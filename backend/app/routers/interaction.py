from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_like import ArticleLike
from backend.app.models.behavior import UserBehavior
from backend.app.models.user import User
from backend.app.schemas.article import ArticleActionRequest

router = APIRouter()


def _record_behavior(db: Session, user_id: int, article_id: int, behavior_type: str) -> None:
    """记录互动行为，供分析模块使用。"""

    db.add(
        UserBehavior(
            user_id=user_id,
            article_id=article_id,
            behavior_type=behavior_type,
            create_time=datetime.utcnow(),
        )
    )
    db.commit()


def _update_like_count(db: Session, article: Article) -> None:
    """根据点赞记录刷新文章点赞数。"""

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
    """点赞或取消点赞。"""

    if payload.action not in {"like", "unlike"}:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
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
        db.add(ArticleLike(user_id=current_user.id, article_id=payload.article_id))
        db.commit()
        _record_behavior(db, current_user.id, payload.article_id, "like")
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
    """根据收藏记录刷新文章收藏数。"""

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
    """收藏或取消收藏。"""

    if payload.action not in {"collect", "uncollect"}:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
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
        db.add(ArticleCollect(user_id=current_user.id, article_id=payload.article_id))
        db.commit()
        _record_behavior(db, current_user.id, payload.article_id, "collect")
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
