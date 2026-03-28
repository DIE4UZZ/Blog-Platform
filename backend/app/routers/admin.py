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

ABNORMAL_KEYWORDS = {"诈骗", "赌博", "涉黄", "毒品", "枪支", "暴恐"}


class UserRoleUpdateRequest(BaseModel):
    user_id: int
    role: str


class ArticleReviewRequest(BaseModel):
    article_id: int
    status: str


def _resolve_user_name(user: User) -> str:
    return user.username or user.email or user.phone or f"user_{user.id}"


@router.get("/admin/users")
def admin_list_users(
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if keyword:
        query = query.filter(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%"),
                User.phone.like(f"%{keyword}%"),
            )
        )
    total = query.count()
    users = (
        query.order_by(desc(User.create_time))
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
                else None,
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
    if payload.role not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="仅支持 user/admin")
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
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
    query = db.query(Article).filter(Article.is_deleted == False)
    if status:
        query = query.filter(Article.status == status)
    if keyword:
        query = query.filter(
            or_(
                Article.title.like(f"%{keyword}%"),
                Article.summary.like(f"%{keyword}%"),
                Article.content.like(f"%{keyword}%"),
            )
        )
    total = query.count()
    articles = (
        query.order_by(desc(Article.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
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
                "status": article.status,
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
    article.update_time = datetime.utcnow()
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
    article_rows = (
        db.query(Article)
        .filter(Article.is_deleted == False)
        .order_by(desc(Article.update_time))
        .limit(1000)
        .all()
    )
    comment_rows = (
        db.query(Comment)
        .order_by(desc(Comment.create_time))
        .limit(1000)
        .all()
    )
    rows = []
    for article in article_rows:
        text = f"{article.title} {article.summary} {article.content}"
        hit_words = [word for word in ABNORMAL_KEYWORDS if word in text]
        if hit_words:
            rows.append(
                {
                    "type": "article",
                    "target_id": article.id,
                    "snippet": article.title,
                    "hit_keywords": hit_words,
                    "time": article.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    for comment in comment_rows:
        text = comment.content or ""
        hit_words = [word for word in ABNORMAL_KEYWORDS if word in text]
        if hit_words:
            rows.append(
                {
                    "type": "comment",
                    "target_id": comment.id,
                    "snippet": text[:100],
                    "hit_keywords": hit_words,
                    "time": comment.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
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
