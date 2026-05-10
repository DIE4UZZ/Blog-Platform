"""
routers/comment.py —— 评论路由模块

提供文章评论的创建和查询接口：
  - POST /behavior/comment : 发表评论或回复（需要登录）
  - GET  /comment/list     : 获取文章评论列表（无需登录）

评论联动操作：
  - 发表评论后自动更新文章的 comment_count 计数
  - 同时记录一条 behavior_type="comment" 的行为记录（用于推荐算法）
  - 调用 create_comment_notifications 通知文章作者和被回复的评论作者
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.behavior import UserBehavior
from backend.app.models.comment import Comment
from backend.app.models.user import User
from backend.app.routers.social import create_comment_notifications
from backend.app.schemas.comment import CommentCreateRequest

router = APIRouter()


@router.post("/behavior/comment")
def create_comment(
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发表评论或回复。

    评论流程：
      1. 校验文章是否存在且未删除
      2. 若有 parent_id，校验父评论是否存在且属于同一篇文章
      3. 创建评论记录
      4. 文章 comment_count +1
      5. 记录 behavior_type="comment" 的行为（用于推荐算法）
      6. 触发通知：通知文章作者和被回复的评论作者

    Args:
        payload (CommentCreateRequest): 评论请求体，包含 article_id/content/parent_id。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户（评论者）。

    Returns:
        成功响应，data 包含 comment_id 和 create_time。

    Raises:
        HTTPException(404): 文章不存在或父评论不存在时抛出。
    """
    # 校验文章是否存在且未被软删除
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 若是回复评论，校验父评论是否存在且属于同一篇文章
    parent_comment = None
    if payload.parent_id:
        parent_comment = (
            db.query(Comment)
            .filter(
                Comment.id == payload.parent_id,
                Comment.article_id == payload.article_id,  # 防止跨文章回复
            )
            .first()
        )
        if not parent_comment:
            raise HTTPException(status_code=404, detail="父评论不存在")

    # 创建评论记录
    comment = Comment(
        article_id=payload.article_id,
        user_id=current_user.id,
        content=payload.content,
        parent_id=payload.parent_id,    # None 表示顶级评论，有值表示回复
        create_time=datetime.utcnow(),
    )
    db.add(comment)

    # 文章评论数 +1（冗余字段，避免每次 COUNT 查询）
    article.comment_count += 1
    db.add(article)

    # 记录评论行为（用于推荐算法的转化率统计）
    db.add(
        UserBehavior(
            user_id=current_user.id,
            article_id=payload.article_id,
            behavior_type="comment",    # 行为类型：评论
            create_time=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(comment)  # 刷新以获取数据库生成的 id

    # 触发通知：通知文章作者（新评论通知）和被回复的评论作者（回复通知）
    create_comment_notifications(db, article, comment, parent_comment)

    return success_response(
        {
            "comment_id": comment.id,
            "create_time": comment.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        message="评论成功",
    )


@router.get("/comment/list")
def list_comments(
    article_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """获取文章评论列表（公开接口，无需登录）。

    返回指定文章的评论列表，按创建时间降序排列（最新评论在前）。
    同时返回评论者的用户信息（用户名/邮箱/手机号）。

    树形结构说明：
      - parent_id = None：顶级评论
      - parent_id = 某评论 ID：该评论的回复
      - 前端根据 parent_id 自行组装树形结构

    Args:
        article_id (int): 文章 ID（Query 参数）。
        page (int): 页码，从 1 开始。
        page_size (int): 每页数量，默认 10。
        db (Session): 数据库会话。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 comment_id/user/content/parent_id/create_time。
    """
    # 查询该文章的所有评论（按时间降序）
    query = db.query(Comment).filter(Comment.article_id == article_id)
    total = query.count()
    comments = (
        query.order_by(desc(Comment.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 批量查询评论者信息（避免 N+1 查询问题）
    user_ids = list({item.user_id for item in comments})
    users = (
        db.query(User).filter(User.id.in_(user_ids)).all()
        if user_ids
        else []
    )
    user_map = {user.id: user for user in users}  # 建立 ID → User 的映射

    data = {
        "list": [
            {
                "comment_id": item.id,
                "user": {
                    "user_id": item.user_id,
                    # 展示名称：优先用户名，其次邮箱，最后手机号
                    "username": (
                        user_map.get(item.user_id).username
                        or user_map.get(item.user_id).email
                        or user_map.get(item.user_id).phone
                    )
                    if user_map.get(item.user_id)
                    else None,
                },
                "content": item.content,
                "parent_id": item.parent_id,    # None=顶级评论，有值=回复
                "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for item in comments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)
