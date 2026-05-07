from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_read_later import ArticleReadLater
from backend.app.models.behavior import UserBehavior
from backend.app.models.user import User
from backend.app.schemas.library import ReadLaterActionRequest

router = APIRouter()


def _resolve_author_name(user: User | None) -> str | None:
    if not user:
        return None
    return user.username or user.email or user.phone


def _split_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _build_article_item(article: Article, author_map: dict[int, User]) -> dict:
    author = author_map.get(article.author_id)
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": _split_tags(article.tags),
        "author": {
            "user_id": article.author_id,
            "username": _resolve_author_name(author),
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "comment_count": article.comment_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _build_article_map(
    db: Session, article_ids: list[int]
) -> tuple[dict[int, Article], dict[int, User]]:
    articles = db.query(Article).filter(Article.id.in_(article_ids)).all() if article_ids else []
    article_map = {article.id: article for article in articles}
    author_ids = list({article.author_id for article in articles})
    authors = db.query(User).filter(User.id.in_(author_ids)).all() if author_ids else []
    author_map = {author.id: author for author in authors}
    return article_map, author_map


@router.get("/library/collections")
def library_collections(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ArticleCollect).filter(ArticleCollect.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(desc(ArticleCollect.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    article_ids = [row.article_id for row in rows]
    article_map, author_map = _build_article_map(db, article_ids)
    data = []
    for row in rows:
        article = article_map.get(row.article_id)
        if not article or article.is_deleted or article.status != "published":
            continue
        item = _build_article_item(article, author_map)
        item["collected_at"] = row.create_time.strftime("%Y-%m-%d %H:%M:%S")
        data.append(item)
    return success_response(
        {"list": data, "total": total, "page": page, "page_size": page_size}
    )


@router.get("/library/history")
def library_history(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(UserBehavior)
        .filter(
            UserBehavior.user_id == current_user.id,
            UserBehavior.behavior_type == "read",
            UserBehavior.article_id.isnot(None),
        )
        .order_by(desc(UserBehavior.create_time))
        .limit(2000)
        .all()
    )

    history_map: OrderedDict[int, dict] = OrderedDict()
    for row in rows:
        article_id = int(row.article_id or 0)
        if article_id <= 0:
            continue
        bucket = history_map.get(article_id)
        if bucket is None:
            history_map[article_id] = {
                "article_id": article_id,
                "last_read_time": row.create_time,
                "read_count": 1,
                "last_read_duration": int(row.read_duration or 0),
                "max_scroll_depth": float(row.scroll_depth or 0.0),
            }
            continue
        bucket["read_count"] += 1
        bucket["last_read_duration"] = int(row.read_duration or bucket["last_read_duration"] or 0)
        bucket["max_scroll_depth"] = max(
            float(bucket["max_scroll_depth"] or 0.0),
            float(row.scroll_depth or 0.0),
        )

    history_items = list(history_map.values())
    total = len(history_items)
    paged_items = history_items[(page - 1) * page_size : page * page_size]
    article_ids = [item["article_id"] for item in paged_items]
    article_map, author_map = _build_article_map(db, article_ids)

    data = []
    for item in paged_items:
        article = article_map.get(item["article_id"])
        if not article or article.is_deleted or article.status != "published":
            continue
        payload = _build_article_item(article, author_map)
        payload["last_read_time"] = item["last_read_time"].strftime("%Y-%m-%d %H:%M:%S")
        payload["read_count"] = int(item["read_count"])
        payload["last_read_duration"] = int(item["last_read_duration"])
        payload["max_scroll_depth"] = round(float(item["max_scroll_depth"]), 4)
        data.append(payload)

    return success_response(
        {"list": data, "total": total, "page": page, "page_size": page_size}
    )


@router.get("/library/read-later")
def library_read_later(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ArticleReadLater).filter(ArticleReadLater.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(desc(ArticleReadLater.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    article_ids = [row.article_id for row in rows]
    article_map, author_map = _build_article_map(db, article_ids)
    data = []
    for row in rows:
        article = article_map.get(row.article_id)
        if not article or article.is_deleted or article.status != "published":
            continue
        item = _build_article_item(article, author_map)
        item["saved_at"] = row.create_time.strftime("%Y-%m-%d %H:%M:%S")
        data.append(item)
    return success_response(
        {"list": data, "total": total, "page": page, "page_size": page_size}
    )


@router.post("/library/read-later")
def toggle_read_later(
    payload: ReadLaterActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.action not in {"save", "remove"}:
        raise HTTPException(status_code=400, detail="仅支持 save/remove")

    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article or article.status != "published":
        raise HTTPException(status_code=404, detail="文章不存在")

    existing = (
        db.query(ArticleReadLater)
        .filter(
            ArticleReadLater.user_id == current_user.id,
            ArticleReadLater.article_id == payload.article_id,
        )
        .first()
    )
    is_saved = existing is not None

    if payload.action == "save" and existing is None:
        db.add(
            ArticleReadLater(
                user_id=current_user.id,
                article_id=payload.article_id,
            )
        )
        db.commit()
        is_saved = True
    elif payload.action == "remove" and existing is not None:
        db.delete(existing)
        db.commit()
        is_saved = False

    total = (
        db.query(ArticleReadLater)
        .filter(ArticleReadLater.user_id == current_user.id)
        .count()
    )
    return success_response(
        {
            "article_id": payload.article_id,
            "is_saved_for_later": is_saved,
            "read_later_count": total,
        },
        message="操作成功",
    )
