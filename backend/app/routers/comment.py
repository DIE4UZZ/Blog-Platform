from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import success_response
from app.db.session import get_db
from app.models.article import Article
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreateRequest

router = APIRouter()


@router.post("/behavior/comment")
def create_comment(
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new comment for an article.

    Args:
        payload (CommentCreateRequest): Comment payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with comment id.
    """

    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    comment = Comment(
        article_id=payload.article_id,
        user_id=current_user.id,
        content=payload.content,
        parent_id=payload.parent_id,
        create_time=datetime.utcnow(),
    )
    db.add(comment)
    article.comment_count += 1
    db.add(article)
    db.commit()
    db.refresh(comment)
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
    """Get comment list for an article.

    Args:
        article_id (int): Article id.
        page (int): Page number.
        page_size (int): Page size.
        db (Session): Database session.

    Returns:
        dict: Standardized response with comment list.
    """

    query = db.query(Comment).filter(Comment.article_id == article_id)
    total = query.count()
    comments = (
        query.order_by(desc(Comment.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = {
        "list": [
            {
                "comment_id": item.id,
                "user": {
                    "user_id": item.user_id,
                    "username": None,
                },
                "content": item.content,
                "parent_id": item.parent_id,
                "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for item in comments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)
