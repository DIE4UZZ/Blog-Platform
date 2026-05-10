"""
routers/interaction.py —— 文章互动路由模块

提供文章点赞和收藏的切换接口：
  - POST /article/like    : 点赞 / 取消点赞
  - POST /article/collect : 收藏 / 取消收藏

设计说明：
  - 使用幂等设计：重复点赞不会报错，重复取消也不会报错
  - 每次操作后重新 COUNT 刷新文章的 like_count / collect_count（保证准确性）
  - 点赞/收藏时同步记录行为数据（用于推荐算法和数据分析）
"""

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
    """记录用户互动行为到行为表（供推荐算法和数据分析使用）。

    Args:
        db (Session): 数据库会话。
        user_id (int): 操作用户 ID。
        article_id (int): 被操作文章 ID。
        behavior_type (str): 行为类型，"like" 或 "collect"。
    """
    db.add(
        UserBehavior(
            user_id=user_id,
            article_id=article_id,
            behavior_type=behavior_type,    # 行为类型标记
            create_time=datetime.utcnow(),
        )
    )
    db.commit()


def _update_like_count(db: Session, article: Article) -> None:
    """重新统计并更新文章的点赞数（从 article_like 表 COUNT）。

    使用 COUNT 而非 +1/-1 的原因：
      - 避免并发操作导致计数不准确
      - 防止重复点赞导致计数异常

    Args:
        db (Session): 数据库会话。
        article (Article): 要更新的文章 ORM 对象。
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
    """点赞或取消点赞文章。

    幂等设计：
      - action="like"：若已点赞则忽略，未点赞则添加记录并记录行为
      - action="unlike"：若未点赞则忽略，已点赞则删除记录

    Args:
        payload (ArticleActionRequest): 请求体，包含 article_id 和 action。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 包含：
          - like_count: 最新点赞数
          - is_liked: 操作后的点赞状态

    Raises:
        HTTPException(400): action 不是 "like" 或 "unlike" 时抛出。
        HTTPException(404): 文章不存在时抛出。
    """
    if payload.action not in {"like", "unlike"}:
        raise HTTPException(status_code=400, detail="不支持的操作类型")

    # 校验文章是否存在
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 查询当前用户是否已点赞该文章
    existing = (
        db.query(ArticleLike)
        .filter(
            ArticleLike.article_id == payload.article_id,
            ArticleLike.user_id == current_user.id,
        )
        .first()
    )

    # 点赞：仅在未点赞时添加记录（幂等）
    if payload.action == "like" and existing is None:
        db.add(ArticleLike(user_id=current_user.id, article_id=payload.article_id))
        db.commit()
        _record_behavior(db, current_user.id, payload.article_id, "like")  # 记录行为

    # 取消点赞：仅在已点赞时删除记录（幂等）
    if payload.action == "unlike" and existing is not None:
        db.delete(existing)
        db.commit()

    # 重新统计点赞数（保证准确性）
    _update_like_count(db, article)
    return success_response(
        {
            "like_count": article.like_count,
            "is_liked": payload.action == "like",   # 返回操作后的状态
        },
        message="操作成功",
    )


def _update_collect_count(db: Session, article: Article) -> None:
    """重新统计并更新文章的收藏数（从 article_collect 表 COUNT）。

    Args:
        db (Session): 数据库会话。
        article (Article): 要更新的文章 ORM 对象。
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
    """收藏或取消收藏文章。

    幂等设计：
      - action="collect"：若已收藏则忽略，未收藏则添加记录并记录行为
      - action="uncollect"：若未收藏则忽略，已收藏则删除记录

    Args:
        payload (ArticleActionRequest): 请求体，包含 article_id 和 action。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 包含：
          - collect_count: 最新收藏数
          - is_collected: 操作后的收藏状态

    Raises:
        HTTPException(400): action 不是 "collect" 或 "uncollect" 时抛出。
        HTTPException(404): 文章不存在时抛出。
    """
    if payload.action not in {"collect", "uncollect"}:
        raise HTTPException(status_code=400, detail="不支持的操作类型")

    # 校验文章是否存在
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 查询当前用户是否已收藏该文章
    existing = (
        db.query(ArticleCollect)
        .filter(
            ArticleCollect.article_id == payload.article_id,
            ArticleCollect.user_id == current_user.id,
        )
        .first()
    )

    # 收藏：仅在未收藏时添加记录（幂等）
    if payload.action == "collect" and existing is None:
        db.add(ArticleCollect(user_id=current_user.id, article_id=payload.article_id))
        db.commit()
        _record_behavior(db, current_user.id, payload.article_id, "collect")  # 记录行为

    # 取消收藏：仅在已收藏时删除记录（幂等）
    if payload.action == "uncollect" and existing is not None:
        db.delete(existing)
        db.commit()

    # 重新统计收藏数（保证准确性）
    _update_collect_count(db, article)
    return success_response(
        {
            "collect_count": article.collect_count,
            "is_collected": payload.action == "collect",    # 返回操作后的状态
        },
        message="操作成功",
    )
