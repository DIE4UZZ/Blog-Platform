"""
routers/admin.py —— 管理员后台路由模块

提供管理员专用的用户管理、文章审核、异常内容检测接口：
  - GET  /admin/users              : 用户列表（支持关键词/角色筛选）
  - PUT  /admin/user/role          : 修改用户角色（user/admin）
  - GET  /admin/articles           : 文章列表（支持状态/关键词筛选）
  - PUT  /admin/article/review     : 文章审核（发布/驳回/退回草稿）
  - GET  /admin/content/abnormal   : 异常内容检测（关键词命中）

权限控制：
  - 所有接口均通过 require_admin 依赖校验，非管理员返回 403
  - 管理员不能取消自己的管理员权限

异常内容检测说明：
  - 使用关键词黑名单（ABNORMAL_KEYWORDS）对文章和评论进行扫描
  - 命中关键词的内容会被标记，供管理员人工审核
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from backend.app.core.deps import require_admin
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.comment import Comment
from backend.app.models.user import User

router = APIRouter()

# 异常内容关键词黑名单（用于内容安全检测）
ABNORMAL_KEYWORDS = {"诈骗", "赌博", "涉黄", "毒品", "枪支", "暴恐"}


class UserRoleUpdateRequest(BaseModel):
    """修改用户角色的请求体。"""
    user_id: int    # 目标用户 ID
    role: str       # 新角色（"user" 或 "admin"）


class ArticleReviewRequest(BaseModel):
    """文章审核的请求体。"""
    article_id: int  # 目标文章 ID
    status: str      # 审核结果（"published"/"draft"/"rejected"）


def _resolve_user_name(user: User) -> str:
    """获取用户展示名称（优先用户名，其次邮箱，最后手机号，均无则显示 user_ID）。"""
    return user.username or user.email or user.phone or f"user_{user.id}"


@router.get("/admin/users")
def admin_list_users(
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),  # 管理员权限校验（_ 表示不使用返回值）
):
    """获取用户列表（管理员专用）。

    支持按角色筛选和关键词搜索（用户名/邮箱/手机号模糊匹配），
    按注册时间降序排列。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        keyword: 搜索关键词（模糊匹配用户名/邮箱/手机号）。
        role: 角色筛选（"user" 或 "admin"），为 None 时不过滤。
        db: 数据库会话。
        _: 管理员权限校验（通过 require_admin 依赖注入）。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 user_id/username/email/phone/role/create_time/last_login_time。
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)  # 角色精确匹配
    if keyword:
        # 关键词模糊搜索（用户名 OR 邮箱 OR 手机号）
        query = query.filter(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%"),
                User.phone.like(f"%{keyword}%"),
            )
        )
    total = query.count()
    users = (
        query.order_by(desc(User.create_time))  # 按注册时间降序
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = []
    for user in users:
        data.append(
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_login_time": user.last_login_time.strftime("%Y-%m-%d %H:%M:%S")
                if user.last_login_time
                else None,  # 从未登录时为 None
            }
        )
    return success_response(
        {
            "list": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.put("/admin/user/role")
def admin_update_user_role(
    payload: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """修改用户角色（管理员专用）。

    安全限制：
      - 角色只能设置为 "user" 或 "admin"
      - 管理员不能取消自己的管理员权限（防止系统无管理员）

    Args:
        payload: 请求体，包含 user_id 和 role。
        db: 数据库会话。
        current_user: 当前管理员用户（用于防止自降权限）。

    Returns:
        成功响应，message="更新成功"。

    Raises:
        HTTPException(400): 角色值不合法或管理员尝试取消自己权限时抛出。
        HTTPException(404): 目标用户不存在时抛出。
    """
    if payload.role not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="仅支持 user/admin")
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 防止管理员取消自己的权限（避免系统无管理员）
    if target.id == current_user.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="不能取消当前管理员自己的权限")
    target.role = payload.role
    db.add(target)
    db.commit()
    return success_response({}, message="更新成功")


@router.get("/admin/articles")
def admin_list_articles(
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """获取文章列表（管理员专用，包含所有状态的文章）。

    与普通文章列表不同，管理员可以查看所有状态（草稿/已发布/已驳回）的文章，
    支持按状态筛选和关键词搜索（标题/摘要/正文模糊匹配）。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        status: 状态筛选（"draft"/"published"/"rejected"），为 None 时不过滤。
        keyword: 搜索关键词（模糊匹配标题/摘要/正文）。
        db: 数据库会话。
        _: 管理员权限校验。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 article_id/title/summary/status/author/create_time/update_time/view_count。
    """
    # 只过滤已删除的文章（管理员可以看到所有状态）
    query = db.query(Article).filter(Article.is_deleted == False)
    if status:
        query = query.filter(Article.status == status)  # 状态精确匹配
    if keyword:
        # 关键词模糊搜索（标题 OR 摘要 OR 正文）
        query = query.filter(
            or_(
                Article.title.like(f"%{keyword}%"),
                Article.summary.like(f"%{keyword}%"),
                Article.content.like(f"%{keyword}%"),
            )
        )
    total = query.count()
    articles = (
        query.order_by(desc(Article.create_time))  # 按创建时间降序
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 批量查询作者信息（避免 N+1 查询）
    author_ids = list({item.author_id for item in articles})
    authors = (
        db.query(User).filter(User.id.in_(author_ids)).all()
        if author_ids
        else []
    )
    author_map = {author.id: author for author in authors}

    data = []
    for article in articles:
        author = author_map.get(article.author_id)
        data.append(
            {
                "article_id": article.id,
                "title": article.title,
                "summary": article.summary,
                "status": article.status,                           # 文章状态
                "author": _resolve_user_name(author) if author else None,
                "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": article.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "view_count": article.view_count,
            }
        )
    return success_response(
        {
            "list": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.put("/admin/article/review")
def admin_review_article(
    payload: ArticleReviewRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """审核文章（管理员专用）。

    支持三种审核结果：
      - "published"：通过审核，文章公开发布
      - "draft"：退回草稿，作者可继续修改
      - "rejected"：驳回，文章不予发布

    Args:
        payload: 请求体，包含 article_id 和 status。
        db: 数据库会话。
        _: 管理员权限校验。

    Returns:
        成功响应，message="审核状态更新成功"。

    Raises:
        HTTPException(400): status 值不合法时抛出。
        HTTPException(404): 文章不存在时抛出。
    """
    if payload.status not in {"published", "draft", "rejected"}:
        raise HTTPException(status_code=400, detail="状态仅支持 published/draft/rejected")
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.status = payload.status
    article.update_time = datetime.utcnow()  # 更新修改时间
    db.add(article)
    db.commit()
    return success_response({}, message="审核状态更新成功")


@router.get("/admin/content/abnormal")
def admin_abnormal_content(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """检测异常内容（关键词命中检测，管理员专用）。

    检测逻辑：
      1. 查询最近 1000 篇文章（标题+摘要+正文）
      2. 查询最近 1000 条评论
      3. 对每条内容检查是否包含 ABNORMAL_KEYWORDS 中的关键词
      4. 命中的内容按时间降序排列，分页返回

    注意：这是基于关键词的简单检测，仅作为人工审核的辅助工具。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        _: 管理员权限校验。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 type（article/comment）/target_id/snippet/hit_keywords/time。
    """
    # 查询最近 1000 篇文章（按更新时间降序）
    article_rows = (
        db.query(Article)
        .filter(Article.is_deleted == False)
        .order_by(desc(Article.update_time))
        .limit(1000)
        .all()
    )
    # 查询最近 1000 条评论（按创建时间降序）
    comment_rows = (
        db.query(Comment)
        .order_by(desc(Comment.create_time))
        .limit(1000)
        .all()
    )

    rows = []
    # 检测文章内容（标题 + 摘要 + 正文）
    for article in article_rows:
        text = f"{article.title} {article.summary} {article.content}"
        hit_words = [word for word in ABNORMAL_KEYWORDS if word in text]
        if hit_words:
            rows.append(
                {
                    "type": "article",                  # 内容类型
                    "target_id": article.id,            # 文章 ID（用于跳转）
                    "snippet": article.title,           # 摘要片段（显示标题）
                    "hit_keywords": hit_words,          # 命中的关键词列表
                    "time": article.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    # 检测评论内容
    for comment in comment_rows:
        text = comment.content or ""
        hit_words = [word for word in ABNORMAL_KEYWORDS if word in text]
        if hit_words:
            rows.append(
                {
                    "type": "comment",                  # 内容类型
                    "target_id": comment.id,            # 评论 ID
                    "snippet": text[:100],              # 评论内容前 100 字符
                    "hit_keywords": hit_words,          # 命中的关键词列表
                    "time": comment.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    # 按时间降序排列（文章和评论混合排序）
    rows.sort(key=lambda item: item["time"], reverse=True)
    total = len(rows)
    start = (page - 1) * page_size
    end = page * page_size
    return success_response(
        {
            "list": rows[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
