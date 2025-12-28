from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user
from app.core.response import success_response
from app.db.session import get_db
from app.models.article import Article
from app.models.recommendation import Recommendation
from app.models.user import User

router = APIRouter()


def _build_recommend_item(article: Article, recommend_type: str, score: float) -> dict:
    """Build recommendation list item.

    Args:
        article (Article): Article entity.
        recommend_type (str): Recommendation type.
        score (float): Recommendation score.

    Returns:
        dict: Recommendation item payload.
    """

    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": [tag.strip() for tag in (article.tags or "").split(",") if tag.strip()],
        "author": {
            "user_id": article.author_id,
            "username": None,
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "recommend_type": recommend_type,
        "recommend_score": score,
    }


def _calculate_score(article: Article, preference_tags: List[str]) -> float:
    """Calculate a simple recommendation score.

    Args:
        article (Article): Article entity.
        preference_tags (List[str]): User preference tags.

    Returns:
        float: Recommendation score.
    """

    base_score = float(article.view_count)
    if preference_tags and article.tags:
        article_tags = [tag.strip() for tag in article.tags.split(",") if tag.strip()]
        overlap = len(set(article_tags) & set(preference_tags))
        base_score += overlap * 10
    return base_score


@router.get("/recommend/list")
def recommend_list(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get recommended article list.

    Args:
        page (int): Page number.
        page_size (int): Page size.
        db (Session): Database session.
        current_user (User | None): Optional current user.

    Returns:
        dict: Standardized response with recommendation list.
    """

    query = db.query(Article).filter(Article.is_deleted == False)
    query = query.order_by(desc(Article.view_count), desc(Article.create_time))
    total = query.count()
    items = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    preference_tags = []
    recommend_type = "cold_start"
    user_id = None
    if current_user:
        user_id = current_user.id
        if current_user.preference_tags:
            preference_tags = [
                tag.strip()
                for tag in current_user.preference_tags.split(",")
                if tag.strip()
            ]
            recommend_type = "content_based"
    data_list = []
    for article in items:
        score = _calculate_score(article, preference_tags)
        data_list.append(_build_recommend_item(article, recommend_type, score))
        record = Recommendation(
            user_id=user_id,
            article_id=article.id,
            recommend_type=recommend_type,
            recommend_score=score,
            is_clicked=False,
        )
        db.add(record)
    db.commit()
    return success_response(
        {
            "list": data_list,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/recommend/similar")
def recommend_similar(
    article_id: int,
    size: int = 5,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get similar article recommendations.

    Args:
        article_id (int): Article id.
        size (int): Number of items to return.
        db (Session): Database session.
        current_user (User | None): Optional current user.

    Returns:
        dict: Standardized response with recommendation list.
    """

    target = (
        db.query(Article)
        .filter(Article.id == article_id, Article.is_deleted == False)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="文章不存在")
    query = db.query(Article).filter(Article.is_deleted == False, Article.id != article_id)
    if target.category:
        query = query.filter(Article.category == target.category)
    items = query.order_by(desc(Article.view_count)).limit(size).all()
    data_list = [
        _build_recommend_item(item, "content_based", float(item.view_count))
        for item in items
    ]
    user_id = current_user.id if current_user else None
    for item in items:
        record = Recommendation(
            user_id=user_id,
            article_id=item.id,
            recommend_type="content_based",
            recommend_score=float(item.view_count),
            is_clicked=False,
        )
        db.add(record)
    db.commit()
    return success_response({"list": data_list, "total": len(data_list), "page": 1, "page_size": size})
