from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from markdown import markdown
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_optional_user, require_admin
from app.core.response import success_response
from app.db.session import get_db
from app.models.article import Article
from app.models.article_collect import ArticleCollect
from app.models.article_like import ArticleLike
from app.models.user import User
from app.schemas.article import ArticleEditRequest, ArticlePublishRequest

router = APIRouter()


def build_summary(content: str, limit: int = 120) -> str:
    """Build a short summary from content.

    Args:
        content (str): Article content.
        limit (int): Maximum length for summary.

    Returns:
        str: Summary string.
    """

    plain = content.replace("\n", " ").strip()
    return plain[:limit]


def split_tags(tags: str | None) -> List[str]:
    """Split comma-separated tags into a list.

    Args:
        tags (str | None): Comma-separated tags.

    Returns:
        List[str]: List of tag strings.
    """

    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


@router.post("/article/publish")
def publish_article(
    payload: ArticlePublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a new article.

    Args:
        payload (ArticlePublishRequest): Article payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with article_id.
    """

    html_content = markdown(payload.content)
    article = Article(
        author_id=current_user.id,
        title=payload.title,
        content=payload.content,
        html_content=html_content,
        summary=build_summary(payload.content),
        category=payload.category,
        tags=payload.tags,
        status=payload.status,
        create_time=datetime.utcnow(),
        update_time=datetime.utcnow(),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return success_response({"article_id": article.id}, message="发布成功")


@router.put("/article/edit")
def edit_article(
    payload: ArticleEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit an existing article.

    Args:
        payload (ArticleEditRequest): Article edit payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with empty data.
    """

    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    article.title = payload.title
    article.content = payload.content
    article.html_content = markdown(payload.content)
    article.summary = build_summary(payload.content)
    article.category = payload.category
    article.tags = payload.tags
    article.status = payload.status
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()
    return success_response({}, message="编辑成功")


@router.delete("/article/delete")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete an article.

    Args:
        article_id (int): Article id.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with empty data.
    """

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article or article.is_deleted:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    article.is_deleted = True
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()
    return success_response({}, message="删除成功")


@router.get("/article/detail")
def get_article_detail(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get article detail by id.

    Args:
        article_id (int): Article id.
        db (Session): Database session.
        current_user (User | None): Optional current user.

    Returns:
        dict: Standardized response with article detail.
    """

    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.view_count += 1
    article.update_time = datetime.utcnow()
    db.add(article)
    db.commit()
    is_liked = False
    is_collected = False
    if current_user:
        is_liked = (
            db.query(ArticleLike)
            .filter(
                ArticleLike.article_id == article.id,
                ArticleLike.user_id == current_user.id,
            )
            .first()
            is not None
        )
        is_collected = (
            db.query(ArticleCollect)
            .filter(
                ArticleCollect.article_id == article.id,
                ArticleCollect.user_id == current_user.id,
            )
            .first()
            is not None
        )
    data = {
        "article_id": article.id,
        "title": article.title,
        "content": article.content,
        "html_content": article.html_content,
        "category": article.category,
        "tags": split_tags(article.tags),
        "author": {
            "user_id": article.author_id,
            "username": None,
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "update_time": article.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_liked": is_liked,
        "is_collected": is_collected,
    }
    return success_response(data)


def _build_article_list_item(article: Article) -> dict:
    """Build list item representation for article.

    Args:
        article (Article): Article entity.

    Returns:
        dict: Article list item.
    """

    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": split_tags(article.tags),
        "author": {
            "user_id": article.author_id,
            "username": None,
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/article/list")
def list_articles(
    page: int = 1,
    page_size: int = 10,
    category: str | None = None,
    tags: str | None = None,
    keyword: str | None = None,
    order: str | None = "latest",
    db: Session = Depends(get_db),
):
    """Get paginated article list with filters.

    Args:
        page (int): Page number.
        page_size (int): Page size.
        category (str | None): Category filter.
        tags (str | None): Tags filter.
        keyword (str | None): Keyword filter.
        order (str | None): Order by latest/hottest.
        db (Session): Database session.

    Returns:
        dict: Standardized response with article list.
    """

    query = db.query(Article).filter(Article.is_deleted == False)
    if category:
        query = query.filter(Article.category == category)
    if tags:
        tag_list = split_tags(tags)
        for tag in tag_list:
            query = query.filter(Article.tags.like(f"%{tag}%"))
    if keyword:
        query = query.filter(Article.title.like(f"%{keyword}%"))
    if order == "hottest":
        query = query.order_by(desc(Article.view_count))
    else:
        query = query.order_by(desc(Article.create_time))
    total = query.count()
    items = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = {
        "list": [_build_article_list_item(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)


@router.get("/article/my-list")
def list_my_articles(
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's article list.

    Args:
        page (int): Page number.
        page_size (int): Page size.
        status (str | None): Status filter.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with article list.
    """

    query = db.query(Article).filter(
        Article.author_id == current_user.id, Article.is_deleted == False
    )
    if status:
        query = query.filter(Article.status == status)
    total = query.count()
    items = (
        query.order_by(desc(Article.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = {
        "list": [_build_article_list_item(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)
