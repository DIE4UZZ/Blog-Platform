from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import success_response
from app.db.session import get_db
from app.models.article import Article
from app.models.article_collect import ArticleCollect
from app.models.article_like import ArticleLike
from app.models.user import User
from app.schemas.article import ArticleActionRequest

router = APIRouter()


def _update_like_count(db: Session, article: Article) -> None:
    """Update article like count based on like records.

    Args:
        db (Session): Database session.
        article (Article): Article entity.

    Returns:
        None: No return value.
    """

    article.like_count = (
        db.query(ArticleLike).filter(ArticleLike.article_id == article.id).count()
    )
    db.add(article)
    db.commit()


@router.post("/article/like")
def like_article(
    payload: ArticleActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Like or unlike an article.

    Args:
        payload (ArticleActionRequest): Like action payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with like status.
    """

    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    existing = (
        db.query(ArticleLike)
        .filter(
            ArticleLike.article_id == payload.article_id,
            ArticleLike.user_id == current_user.id,
        )
        .first()
    )
    if payload.action == "like" and existing is None:
        record = ArticleLike(user_id=current_user.id, article_id=payload.article_id)
        db.add(record)
        db.commit()
    if payload.action == "unlike" and existing is not None:
        db.delete(existing)
        db.commit()
    _update_like_count(db, article)
    return success_response(
        {
            "like_count": article.like_count,
            "is_liked": payload.action == "like",
        },
        message="操作成功",
    )


def _update_collect_count(db: Session, article: Article) -> None:
    """Update article collect count based on collect records.

    Args:
        db (Session): Database session.
        article (Article): Article entity.

    Returns:
        None: No return value.
    """

    article.collect_count = (
        db.query(ArticleCollect)
        .filter(ArticleCollect.article_id == article.id)
        .count()
    )
    db.add(article)
    db.commit()


@router.post("/article/collect")
def collect_article(
    payload: ArticleActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Collect or uncollect an article.

    Args:
        payload (ArticleActionRequest): Collect action payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with collect status.
    """

    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    existing = (
        db.query(ArticleCollect)
        .filter(
            ArticleCollect.article_id == payload.article_id,
            ArticleCollect.user_id == current_user.id,
        )
        .first()
    )
    if payload.action == "collect" and existing is None:
        record = ArticleCollect(user_id=current_user.id, article_id=payload.article_id)
        db.add(record)
        db.commit()
    if payload.action == "uncollect" and existing is not None:
        db.delete(existing)
        db.commit()
    _update_collect_count(db, article)
    return success_response(
        {
            "collect_count": article.collect_count,
            "is_collected": payload.action == "collect",
        },
        message="操作成功",
    )
