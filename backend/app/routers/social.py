"""
routers/social.py —— 社交功能路由模块

提供用户关注、通知、关注动态等社交功能接口：
  - POST /follow/action       : 关注 / 取消关注用户
  - GET  /follow/list         : 获取关注列表或粉丝列表
  - GET  /follow/status       : 查询对某用户的关注状态
  - GET  /feed/following      : 获取关注用户的最新文章动态
  - GET  /notification/list   : 获取通知列表
  - PUT  /notification/read   : 标记通知为已读

通知类型说明：
  - new_article  : 关注的作者发布了新文章
  - new_comment  : 自己的文章收到了新评论
  - comment_reply: 自己的评论收到了回复
  - new_follower : 有新用户关注了自己
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user, get_optional_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.comment import Comment
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow
from backend.app.models.user_notification import UserNotification
from backend.app.schemas.social import FollowActionRequest, NotificationReadRequest

router = APIRouter()


def _resolve_user_name(user: User | None) -> str | None:
    """获取用户展示名称（优先用户名，其次邮箱，最后手机号）。"""
    if not user:
        return None
    return user.username or user.email or user.phone


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    content: str,
    actor_user_id: int | None = None,
    article_id: int | None = None,
    comment_id: int | None = None,
) -> None:
    """创建一条系统通知记录（不自动 commit，由调用方统一提交）。

    Args:
        db: 数据库会话。
        user_id: 接收通知的用户 ID。
        notification_type: 通知类型（new_article/new_comment/comment_reply/new_follower）。
        title: 通知标题（简短描述）。
        content: 通知内容（详细信息，最多 120 字符）。
        actor_user_id: 触发通知的用户 ID（可选）。
        article_id: 关联文章 ID（可选，用于前端跳转）。
        comment_id: 关联评论 ID（可选）。
    """
    db.add(
        UserNotification(
            user_id=user_id,
            actor_user_id=actor_user_id,    # 触发者（如评论者、关注者）
            article_id=article_id,          # 关联文章（用于前端跳转）
            comment_id=comment_id,          # 关联评论
            notification_type=notification_type,
            title=title,
            content=content,
            is_read=False,                  # 初始未读
            create_time=datetime.utcnow(),
        )
    )


def create_new_article_notifications(
    db: Session,
    author: User,
    article: Article,
) -> int:
    """文章发布时，通知所有关注该作者的粉丝。

    Args:
        db: 数据库会话。
        author: 文章作者。
        article: 新发布的文章。

    Returns:
        int: 通知的粉丝数量。
    """
    # 查询所有关注该作者的粉丝 ID
    follower_rows = (
        db.query(UserFollow.follower_id)
        .filter(UserFollow.following_id == author.id)
        .all()
    )
    follower_ids = [int(row.follower_id) for row in follower_rows]
    if not follower_ids:
        return 0

    author_name = _resolve_user_name(author) or f"user_{author.id}"
    title = f"{author_name} 发布了新文章"
    content = article.title[:120]  # 通知内容为文章标题（截取前 120 字符）

    # 为每个粉丝创建通知
    for follower_id in follower_ids:
        create_notification(
            db=db,
            user_id=follower_id,
            notification_type="new_article",
            title=title,
            content=content,
            actor_user_id=author.id,
            article_id=article.id,
        )
    db.commit()
    return len(follower_ids)


def create_comment_notifications(
    db: Session,
    article: Article,
    comment: Comment,
    parent_comment: Comment | None = None,
) -> None:
    """评论发布时，通知文章作者和被回复的评论作者。

    通知规则：
      1. 若评论者不是文章作者，通知文章作者（新评论通知）
      2. 若是回复评论，且被回复者不是文章作者也不是评论者，通知被回复者（回复通知）
         （避免重复通知：文章作者已收到新评论通知，不再收到回复通知）

    Args:
        db: 数据库会话。
        article: 被评论的文章。
        comment: 新创建的评论。
        parent_comment: 父评论（回复时有值，顶级评论时为 None）。
    """
    # 通知文章作者（评论者不是作者本人时才通知）
    if comment.user_id != article.author_id:
        create_notification(
            db=db,
            user_id=article.author_id,
            notification_type="new_comment",
            title="你的文章收到了新评论",
            content=(comment.content or "")[:120],
            actor_user_id=comment.user_id,
            article_id=article.id,
            comment_id=comment.id,
        )

    # 通知被回复的评论作者（避免重复通知文章作者和评论者自己）
    if (
        parent_comment
        and parent_comment.user_id not in {article.author_id, comment.user_id}
    ):
        create_notification(
            db=db,
            user_id=parent_comment.user_id,
            notification_type="comment_reply",
            title="你的评论收到了新回复",
            content=(comment.content or "")[:120],
            actor_user_id=comment.user_id,
            article_id=article.id,
            comment_id=comment.id,
        )
    db.commit()


def _build_article_list_item(article: Article, author_map: dict[int, User]) -> dict:
    """将文章 ORM 对象转换为动态列表项字典（用于关注动态接口）。"""
    author = author_map.get(article.author_id)
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": [tag.strip() for tag in (article.tags or "").split(",") if tag.strip()],
        "author": {
            "user_id": article.author_id,
            "username": _resolve_user_name(author),
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "comment_count": article.comment_count,
        "status": article.status,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/follow/action")
def follow_action(
    payload: FollowActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关注或取消关注用户。

    幂等设计：
      - action="follow"：若已关注则忽略，未关注则添加记录并通知对方
      - action="unfollow"：若未关注则忽略，已关注则删除记录

    Args:
        payload: 请求体，包含 target_user_id 和 action。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 target_user_id/is_followed/follower_count/following_count。

    Raises:
        HTTPException(400): 尝试关注自己或 action 不合法时抛出。
        HTTPException(404): 目标用户不存在时抛出。
    """
    if payload.target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    if payload.action not in {"follow", "unfollow"}:
        raise HTTPException(status_code=400, detail="仅支持 follow/unfollow")

    target_user = db.query(User).filter(User.id == payload.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")

    # 查询是否已关注
    existing = (
        db.query(UserFollow)
        .filter(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == payload.target_user_id,
        )
        .first()
    )
    is_followed = existing is not None

    if payload.action == "follow" and existing is None:
        # 添加关注记录
        db.add(
            UserFollow(
                follower_id=current_user.id,
                following_id=payload.target_user_id,
                create_time=datetime.utcnow(),
            )
        )
        # 通知被关注者
        create_notification(
            db=db,
            user_id=payload.target_user_id,
            notification_type="new_follower",
            title="你有新的关注者",
            content=f"{_resolve_user_name(current_user) or '有用户'} 关注了你",
            actor_user_id=current_user.id,
        )
        db.commit()
        is_followed = True
    elif payload.action == "unfollow" and existing is not None:
        db.delete(existing)
        db.commit()
        is_followed = False

    # 返回最新的粉丝数和关注数
    follower_count = (
        db.query(UserFollow)
        .filter(UserFollow.following_id == payload.target_user_id)
        .count()
    )
    following_count = (
        db.query(UserFollow)
        .filter(UserFollow.follower_id == current_user.id)
        .count()
    )
    return success_response(
        {
            "target_user_id": payload.target_user_id,
            "is_followed": is_followed,
            "follower_count": follower_count,   # 目标用户的粉丝数
            "following_count": following_count, # 当前用户的关注数
        },
        message="操作成功",
    )


@router.get("/follow/list")
def follow_list(
    list_type: str = "following",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的关注列表或粉丝列表。

    Args:
        list_type: "following"（我关注的人）或 "followers"（关注我的人）。
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 user_id/username/role/create_time（关注时间）。
    """
    if list_type not in {"following", "followers"}:
        raise HTTPException(status_code=400, detail="list_type 仅支持 following/followers")

    if list_type == "following":
        # 我关注的人：follower_id = 我的 ID
        query = db.query(UserFollow).filter(UserFollow.follower_id == current_user.id)
        total = query.count()
        rows = (
            query.order_by(desc(UserFollow.create_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        user_ids = [row.following_id for row in rows]
    else:
        # 关注我的人：following_id = 我的 ID
        query = db.query(UserFollow).filter(UserFollow.following_id == current_user.id)
        total = query.count()
        rows = (
            query.order_by(desc(UserFollow.create_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        user_ids = [row.follower_id for row in rows]

    # 批量查询用户信息（避免 N+1 查询）
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {user.id: user for user in users}
    data = []
    for row in rows:
        target_id = row.following_id if list_type == "following" else row.follower_id
        user = user_map.get(target_id)
        data.append(
            {
                "user_id": target_id,
                "username": _resolve_user_name(user),
                "role": user.role if user else "user",
                "create_time": row.create_time.strftime("%Y-%m-%d %H:%M:%S"),  # 关注时间
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


@router.get("/feed/following")
def following_feed(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取关注用户的最新文章动态（关注动态流）。

    只返回当前用户关注的作者发布的已发布文章，按发布时间降序排列。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        若未关注任何人，返回空列表。
    """
    # 获取当前用户关注的所有用户 ID
    followed_ids = [
        int(row.following_id)
        for row in db.query(UserFollow.following_id)
        .filter(UserFollow.follower_id == current_user.id)
        .all()
    ]
    if not followed_ids:
        return success_response({"list": [], "total": 0, "page": page, "page_size": page_size})

    # 查询关注用户发布的文章（已发布且未删除）
    query = (
        db.query(Article)
        .filter(
            Article.author_id.in_(followed_ids),
            Article.is_deleted == False,
            Article.status == "published",
        )
    )
    total = query.count()
    articles = (
        query.order_by(desc(Article.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 批量查询作者信息（避免 N+1 查询）
    author_ids = list({article.author_id for article in articles})
    authors = db.query(User).filter(User.id.in_(author_ids)).all() if author_ids else []
    author_map = {author.id: author for author in authors}

    return success_response(
        {
            "list": [_build_article_list_item(article, author_map) for article in articles],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/notification/list")
def notification_list(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的通知列表。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 20。
        unread_only: 是否只返回未读通知，默认 False。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含：
          - list: 通知列表（含触发者信息、关联文章/评论 ID、跳转路径）
          - total: 总数
          - unread_count: 当前未读通知总数（用于角标显示）
    """
    query = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if unread_only:
        query = query.filter(UserNotification.is_read == False)
    total = query.count()
    rows = (
        query.order_by(desc(UserNotification.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 批量查询触发者信息（避免 N+1 查询）
    actor_ids = list({row.actor_user_id for row in rows if row.actor_user_id})
    actors = db.query(User).filter(User.id.in_(actor_ids)).all() if actor_ids else []
    actor_map = {actor.id: actor for actor in actors}

    # 统计未读通知总数（用于前端角标）
    unread_count = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.is_read == False)
        .count()
    )
    data = []
    for row in rows:
        actor = actor_map.get(row.actor_user_id) if row.actor_user_id else None
        data.append(
            {
                "notification_id": row.id,
                "notification_type": row.notification_type,
                "title": row.title,
                "content": row.content,
                "is_read": row.is_read,
                "actor": {
                    "user_id": actor.id,
                    "username": _resolve_user_name(actor),
                }
                if actor
                else None,
                "article_id": row.article_id,
                "comment_id": row.comment_id,
                "target_path": f"/articles/{row.article_id}" if row.article_id else None,  # 前端跳转路径
                "create_time": row.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return success_response(
        {
            "list": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "unread_count": unread_count,   # 未读通知总数（用于角标）
        }
    )


@router.put("/notification/read")
def mark_notifications_read(
    payload: NotificationReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记通知为已读。

    支持两种模式：
      - read_all=True：标记当前用户所有未读通知为已读
      - read_all=False：标记指定 ID 列表的通知为已读

    Args:
        payload: 请求体，包含 read_all 和 notification_ids。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 updated_count（更新数量）和 unread_count（剩余未读数）。

    Raises:
        HTTPException(400): read_all=False 且未提供 notification_ids 时抛出。
    """
    query = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if payload.read_all:
        # 全部标记已读
        rows = query.filter(UserNotification.is_read == False).all()
    else:
        if not payload.notification_ids:
            raise HTTPException(status_code=400, detail="请提供通知 ID")
        # 按 ID 列表标记已读
        rows = query.filter(UserNotification.id.in_(payload.notification_ids)).all()

    for row in rows:
        row.is_read = True
        db.add(row)
    db.commit()

    # 返回剩余未读数（用于更新前端角标）
    unread_count = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.is_read == False)
        .count()
    )
    return success_response(
        {"updated_count": len(rows), "unread_count": unread_count},
        message="更新成功",
    )


@router.get("/follow/status")
def follow_status(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """查询当前用户对目标用户的关注状态（支持匿名访问）。

    Args:
        target_user_id: 目标用户 ID（Query 参数）。
        db: 数据库会话。
        current_user: 当前用户，未登录时为 None。

    Returns:
        成功响应，data 包含：
          - target_user_id: 目标用户 ID
          - is_followed: 当前用户是否已关注（未登录时为 False）
          - follower_count: 目标用户的粉丝数
    """
    # 统计目标用户的粉丝数
    follower_count = (
        db.query(UserFollow)
        .filter(UserFollow.following_id == target_user_id)
        .count()
    )
    is_followed = False
    if current_user:
        # 查询当前用户是否已关注目标用户
        is_followed = (
            db.query(UserFollow)
            .filter(
                UserFollow.follower_id == current_user.id,
                UserFollow.following_id == target_user_id,
            )
            .first()
            is not None
        )
    return success_response(
        {
            "target_user_id": target_user_id,
            "is_followed": is_followed,
            "follower_count": follower_count,
        }
    )
