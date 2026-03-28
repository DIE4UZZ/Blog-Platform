import re
from typing import List, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.behavior import UserBehavior
from backend.app.models.user import User

router = APIRouter()


def _extract_cover_url(content: str | None) -> str | None:
    """Extract the first image URL from markdown or HTML content."""

    if not content:
        return None
    patterns = [
        r"!\[[^\]]*\]\(([^)]+)\)",
        r'<img\s+[^>]*src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def _calculate_hot_score(article: Article) -> float:
    """Calculate hot score for ranking."""

    return (
        float(article.view_count)
        + float(article.like_count) * 3.0
        + float(article.collect_count) * 5.0
        + float(article.comment_count) * 4.0
    )


def _build_rank_item(article: Article, hot_score: float) -> dict:
    """Build leaderboard item response."""

    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "cover": _extract_cover_url(article.content),
        "hot_value": round(hot_score, 2),
        "share_count": article.collect_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "category": article.category,
    }


def _format_user_name(username: str | None, email: str | None, phone: str | None) -> str:
    """Format user display name from profile fields."""

    return username or email or phone or "匿名作者"


def _fetch_rank_items(
    query, order: str | None, page: int, page_size: int
) -> Tuple[List[dict], int]:
    """Fetch leaderboard items with pagination."""

    total = query.count()
    if order == "latest":
        items = (
            query.order_by(desc(Article.create_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        data = [_build_rank_item(item, _calculate_hot_score(item)) for item in items]
        return data, total
    score_expr = (
        Article.view_count
        + Article.like_count * 3
        + Article.collect_count * 5
        + Article.comment_count * 4
    ).label("hot_score")
    rows = (
        query.add_columns(score_expr)
        .order_by(desc(score_expr), desc(Article.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = []
    for article, hot_score in rows:
        data.append(_build_rank_item(article, hot_score))
    return data, total


@router.get("/rank/list")
def rank_list(
    page: int = 1,
    page_size: int = 10,
    category: str | None = None,
    keyword: str | None = None,
    order: str | None = "hottest",
    db: Session = Depends(get_db),
):
    """Get leaderboard list sorted by hot score or latest."""

    query = db.query(Article).filter(
        Article.is_deleted == False, Article.status == "published"
    )
    if category:
        query = query.filter(Article.category == category)
    if keyword:
        query = query.filter(Article.title.like(f"%{keyword}%"))
    data, total = _fetch_rank_items(query, order, page, page_size)
    return success_response(
        {
            "list": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/rank/hot-search")
def hot_search(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """Get hot search keywords ranked by count."""

    base_query = (
        db.query(
            UserBehavior.keyword.label("keyword"),
            func.count(UserBehavior.id).label("count"),
        )
        .filter(
            UserBehavior.behavior_type == "search",
            UserBehavior.keyword.isnot(None),
            UserBehavior.keyword != "",
        )
        .group_by(UserBehavior.keyword)
        .order_by(desc("count"))
    )
    total = base_query.count()
    rows = (
        base_query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = []
    for index, row in enumerate(rows):
        rank = (page - 1) * page_size + index + 1
        data.append(
            {
                "keyword": row.keyword,
                "count": int(row.count or 0),
                "is_hot": rank <= 3,
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


@router.get("/rank/recommend")
def recommend_follow(
    limit: int = 6,
    db: Session = Depends(get_db),
):
    """Get recommended creators list based on article performance."""

    rows = (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.email.label("email"),
            User.phone.label("phone"),
            func.count(Article.id).label("article_count"),
            func.sum(Article.view_count).label("view_count"),
        )
        .join(Article, Article.author_id == User.id)
        .filter(Article.is_deleted == False, Article.status == "published")
        .group_by(User.id, User.username, User.email, User.phone)
        .order_by(desc("view_count"), desc("article_count"))
        .limit(limit)
        .all()
    )
    data = []
    for row in rows:
        article_count = int(row.article_count or 0)
        view_count = int(row.view_count or 0)
        data.append(
            {
                "user_id": row.user_id,
                "name": _format_user_name(row.username, row.email, row.phone),
                "desc": f"{article_count} 篇文章 · {view_count} 阅读",
                "article_count": article_count,
                "view_count": view_count,
                "followed": False,
            }
        )
    return success_response({"list": data})
