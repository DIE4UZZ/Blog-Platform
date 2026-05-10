"""
routers/library.py —— 用户内容库路由模块

提供用户个人内容库的查询和管理接口：
  - GET  /library/collections : 获取收藏文章列表
  - GET  /library/history     : 获取阅读历史（按文章去重，保留最近阅读时间）
  - GET  /library/read-later  : 获取稍后阅读列表
  - POST /library/read-later  : 添加/移除稍后阅读

阅读历史说明：
  - 从 user_behavior 表中查询 behavior_type="read" 的记录
  - 按文章去重（同一篇文章多次阅读合并为一条）
  - 保留最近阅读时间、阅读次数、最长阅读时长、最大滚动深度
"""

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
    """获取用户展示名称（优先用户名，其次邮箱，最后手机号）。"""
    if not user:
        return None
    return user.username or user.email or user.phone


def _split_tags(tags: str | None) -> list[str]:
    """将逗号分隔的标签字符串拆分为列表，过滤空标签。"""
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _build_article_item(article: Article, author_map: dict[int, User]) -> dict:
    """将文章 ORM 对象转换为内容库列表项字典（不含正文）。

    Args:
        article: 文章 ORM 实例。
        author_map: 作者 ID → User 的映射字典（批量查询结果）。

    Returns:
        文章列表项字典，包含基本信息和统计数据。
    """
    author = author_map.get(article.author_id)
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,         # 摘要（不含完整正文）
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
    """批量查询文章和作者信息，构建 ID → 对象的映射字典。

    使用批量查询避免 N+1 查询问题。

    Args:
        db: 数据库会话。
        article_ids: 文章 ID 列表。

    Returns:
        (article_map, author_map): 文章映射和作者映射的元组。
    """
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
    """获取当前用户的收藏文章列表。

    按收藏时间降序排列，过滤已删除或未发布的文章。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项额外包含 collected_at（收藏时间）。
    """
    query = db.query(ArticleCollect).filter(ArticleCollect.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(desc(ArticleCollect.create_time))  # 按收藏时间降序
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    article_ids = [row.article_id for row in rows]
    article_map, author_map = _build_article_map(db, article_ids)

    data = []
    for row in rows:
        article = article_map.get(row.article_id)
        # 过滤已删除或未发布的文章（文章可能在收藏后被删除或下架）
        if not article or article.is_deleted or article.status != "published":
            continue
        item = _build_article_item(article, author_map)
        item["collected_at"] = row.create_time.strftime("%Y-%m-%d %H:%M:%S")  # 收藏时间
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
    """获取当前用户的阅读历史（按文章去重）。

    处理逻辑：
      1. 查询最近 2000 条 behavior_type="read" 的行为记录
      2. 使用 OrderedDict 按文章去重（保留最近阅读时间的顺序）
      3. 合并同一篇文章的多次阅读数据：
         - read_count: 累计阅读次数
         - last_read_duration: 最近一次阅读时长
         - max_scroll_depth: 历史最大滚动深度
      4. 分页返回，过滤已删除或未发布的文章

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项额外包含 last_read_time/read_count/last_read_duration/max_scroll_depth。
    """
    # 查询最近 2000 条阅读行为（按时间降序，最新的在前）
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

    # 使用 OrderedDict 按文章去重（保留最近阅读时间的顺序）
    history_map: OrderedDict[int, dict] = OrderedDict()
    for row in rows:
        article_id = int(row.article_id or 0)
        if article_id <= 0:
            continue
        bucket = history_map.get(article_id)
        if bucket is None:
            # 第一次出现该文章，创建记录
            history_map[article_id] = {
                "article_id": article_id,
                "last_read_time": row.create_time,          # 最近阅读时间
                "read_count": 1,                            # 阅读次数
                "last_read_duration": int(row.read_duration or 0),  # 最近阅读时长
                "max_scroll_depth": float(row.scroll_depth or 0.0), # 最大滚动深度
            }
            continue
        # 已存在该文章，更新统计数据
        bucket["read_count"] += 1
        bucket["last_read_duration"] = int(row.read_duration or bucket["last_read_duration"] or 0)
        bucket["max_scroll_depth"] = max(
            float(bucket["max_scroll_depth"] or 0.0),
            float(row.scroll_depth or 0.0),
        )

    # 分页处理
    history_items = list(history_map.values())
    total = len(history_items)
    paged_items = history_items[(page - 1) * page_size : page * page_size]
    article_ids = [item["article_id"] for item in paged_items]
    article_map, author_map = _build_article_map(db, article_ids)

    data = []
    for item in paged_items:
        article = article_map.get(item["article_id"])
        # 过滤已删除或未发布的文章
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
    """获取当前用户的稍后阅读列表。

    按添加时间降序排列，过滤已删除或未发布的文章。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项额外包含 saved_at（添加时间）。
    """
    query = db.query(ArticleReadLater).filter(ArticleReadLater.user_id == current_user.id)
    total = query.count()
    rows = (
        query.order_by(desc(ArticleReadLater.create_time))  # 按添加时间降序
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    article_ids = [row.article_id for row in rows]
    article_map, author_map = _build_article_map(db, article_ids)

    data = []
    for row in rows:
        article = article_map.get(row.article_id)
        # 过滤已删除或未发布的文章
        if not article or article.is_deleted or article.status != "published":
            continue
        item = _build_article_item(article, author_map)
        item["saved_at"] = row.create_time.strftime("%Y-%m-%d %H:%M:%S")  # 添加时间
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
    """添加或移除稍后阅读。

    幂等设计：
      - action="save"：若已添加则忽略，未添加则创建记录
      - action="remove"：若未添加则忽略，已添加则删除记录

    Args:
        payload: 请求体，包含 article_id 和 action（"save" 或 "remove"）。
        db: 数据库会话。
        current_user: 当前登录用户。

    Returns:
        成功响应，data 包含：
          - article_id: 操作的文章 ID
          - is_saved_for_later: 操作后的状态
          - read_later_count: 当前用户稍后阅读列表总数

    Raises:
        HTTPException(400): action 不是 "save" 或 "remove" 时抛出。
        HTTPException(404): 文章不存在或未发布时抛出。
    """
    if payload.action not in {"save", "remove"}:
        raise HTTPException(status_code=400, detail="仅支持 save/remove")

    # 校验文章是否存在且已发布
    article = (
        db.query(Article)
        .filter(Article.id == payload.article_id, Article.is_deleted == False)
        .first()
    )
    if not article or article.status != "published":
        raise HTTPException(status_code=404, detail="文章不存在")

    # 查询是否已添加到稍后阅读
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
        # 添加到稍后阅读（幂等）
        db.add(
            ArticleReadLater(
                user_id=current_user.id,
                article_id=payload.article_id,
            )
        )
        db.commit()
        is_saved = True
    elif payload.action == "remove" and existing is not None:
        # 从稍后阅读移除（幂等）
        db.delete(existing)
        db.commit()
        is_saved = False

    # 返回最新的稍后阅读总数
    total = (
        db.query(ArticleReadLater)
        .filter(ArticleReadLater.user_id == current_user.id)
        .count()
    )
    return success_response(
        {
            "article_id": payload.article_id,
            "is_saved_for_later": is_saved,
            "read_later_count": total,  # 当前稍后阅读列表总数
        },
        message="操作成功",
    )
