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
    db.add(
        UserNotification(
            user_id=user_id,
            actor_user_id=actor_user_id,
            article_id=article_id,
            comment_id=comment_id,
            notification_type=notification_type,
            title=title,
            content=content,
            is_read=False,
            create_time=datetime.utcnow(),
        )
    )


def create_new_article_notifications(
    db: Session,
    author: User,
    article: Article,
) -> int:
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
    content = article.title[:120]
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
    if payload.target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    if payload.action not in {"follow", "unfollow"}:
        raise HTTPException(status_code=400, detail="仅支持 follow/unfollow")

    target_user = db.query(User).filter(User.id == payload.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")

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
        db.add(
            UserFollow(
                follower_id=current_user.id,
                following_id=payload.target_user_id,
                create_time=datetime.utcnow(),
            )
        )
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
            "follower_count": follower_count,
            "following_count": following_count,
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
    if list_type not in {"following", "followers"}:
        raise HTTPException(status_code=400, detail="list_type 仅支持 following/followers")

    if list_type == "following":
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
        query = db.query(UserFollow).filter(UserFollow.following_id == current_user.id)
        total = query.count()
        rows = (
            query.order_by(desc(UserFollow.create_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        user_ids = [row.follower_id for row in rows]

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
                "create_time": row.create_time.strftime("%Y-%m-%d %H:%M:%S"),
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
    followed_ids = [
        int(row.following_id)
        for row in db.query(UserFollow.following_id)
        .filter(UserFollow.follower_id == current_user.id)
        .all()
    ]
    if not followed_ids:
        return success_response({"list": [], "total": 0, "page": page, "page_size": page_size})

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
    actor_ids = list({row.actor_user_id for row in rows if row.actor_user_id})
    actors = db.query(User).filter(User.id.in_(actor_ids)).all() if actor_ids else []
    actor_map = {actor.id: actor for actor in actors}
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
                "target_path": f"/articles/{row.article_id}" if row.article_id else None,
                "create_time": row.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return success_response(
        {
            "list": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "unread_count": unread_count,
        }
    )


@router.put("/notification/read")
def mark_notifications_read(
    payload: NotificationReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if payload.read_all:
        rows = query.filter(UserNotification.is_read == False).all()
    else:
        if not payload.notification_ids:
            raise HTTPException(status_code=400, detail="请提供通知 ID")
        rows = query.filter(UserNotification.id.in_(payload.notification_ids)).all()

    for row in rows:
        row.is_read = True
        db.add(row)
    db.commit()
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
    follower_count = (
        db.query(UserFollow)
        .filter(UserFollow.following_id == target_user_id)
        .count()
    )
    is_followed = False
    if current_user:
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
