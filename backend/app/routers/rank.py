"""
routers/rank.py —— 排行榜路由模块

提供文章排行榜、热搜词榜、推荐创作者等接口：
  - GET /rank/list       : 文章排行榜（按热度或最新排序）
  - GET /rank/hot-search : 热搜关键词榜（按搜索次数排序）
  - GET /rank/recommend  : 推荐关注的创作者列表

热度分数公式：
  阅读量×1 + 点赞量×3 + 收藏量×5 + 评论量×4
  权重设计：收藏/评论 > 点赞 > 阅读（越主动的行为权重越高）
"""

import re
from typing import List, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.app.core.deps import get_optional_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.behavior import UserBehavior
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow

router = APIRouter()


def _extract_cover_url(content: str | None) -> str | None:
    """从文章 Markdown 或 HTML 内容中提取第一张图片 URL（作为封面）。

    支持两种格式：
      - Markdown 图片语法：![alt](url)
      - HTML img 标签：<img src="url" ...>

    Args:
        content: 文章正文内容（Markdown 或 HTML）。

    Returns:
        第一张图片的 URL，若无图片则返回 None。
    """
    if not content:
        return None
    patterns = [
        r"!\[[^\]]*\]\(([^)]+)\)",          # Markdown 图片语法
        r'<img\s+[^>]*src=["\']([^"\']+)["\']',  # HTML img 标签
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def _calculate_hot_score(article: Article) -> float:
    """计算文章热度分数（用于排行榜排序）。

    热度公式：阅读量×1 + 点赞量×3 + 收藏量×5 + 评论量×4
    """
    return (
        float(article.view_count)
        + float(article.like_count) * 3.0
        + float(article.collect_count) * 5.0
        + float(article.comment_count) * 4.0
    )


def _build_rank_item(article: Article, hot_score: float) -> dict:
    """将文章 ORM 对象转换为排行榜列表项字典。

    Args:
        article: 文章 ORM 实例。
        hot_score: 预计算的热度分数。

    Returns:
        排行榜列表项字典，包含封面图、热度值等信息。
    """
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "cover": _extract_cover_url(article.content),   # 从正文提取封面图
        "hot_value": round(hot_score, 2),               # 热度值（保留 2 位小数）
        "share_count": article.collect_count,           # 用收藏数代表分享数
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "category": article.category,
    }


def _format_user_name(username: str | None, email: str | None, phone: str | None) -> str:
    """格式化用户展示名称（优先用户名，其次邮箱，最后手机号，均无则显示匿名）。"""
    return username or email or phone or "匿名作者"


def _fetch_rank_items(
    query, order: str | None, page: int, page_size: int
) -> Tuple[List[dict], int]:
    """执行排行榜查询并分页返回结果。

    排序策略：
      - order="latest"：按发布时间降序（最新文章优先）
      - 其他（默认 "hottest"）：按热度分数降序，热度相同时按发布时间降序

    注意：热度排序使用 SQL 表达式在数据库层计算，避免全量加载到内存。

    Args:
        query: 已过滤的 SQLAlchemy 查询对象。
        order: 排序方式，"latest" 或 "hottest"（默认）。
        page: 页码，从 1 开始。
        page_size: 每页数量。

    Returns:
        (data, total): 排行榜列表和总数的元组。
    """
    total = query.count()
    if order == "latest":
        # 按发布时间降序
        items = (
            query.order_by(desc(Article.create_time))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        data = [_build_rank_item(item, _calculate_hot_score(item)) for item in items]
        return data, total

    # 按热度分数降序（在 SQL 层计算，避免全量加载）
    score_expr = (
        Article.view_count
        + Article.like_count * 3
        + Article.collect_count * 5
        + Article.comment_count * 4
    ).label("hot_score")
    rows = (
        query.add_columns(score_expr)
        .order_by(desc(score_expr), desc(Article.create_time))  # 热度相同时按时间降序
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
    """获取文章排行榜列表。

    支持按分类筛选、关键词搜索（标题模糊匹配），以及按热度或最新排序。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        category: 分类筛选（精确匹配），为 None 时不过滤。
        keyword: 标题关键词搜索（模糊匹配），为 None 时不过滤。
        order: 排序方式，"hottest"（热度降序，默认）或 "latest"（最新）。
        db: 数据库会话。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
    """
    # 基础查询：只查已发布且未删除的文章
    query = db.query(Article).filter(
        Article.is_deleted == False, Article.status == "published"
    )
    if category:
        query = query.filter(Article.category == category)  # 分类精确匹配
    if keyword:
        query = query.filter(Article.title.like(f"%{keyword}%"))  # 标题模糊搜索
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
    """获取热搜关键词榜（按搜索次数降序）。

    从 user_behavior 表中统计 behavior_type="search" 的关键词频次，
    前 3 名标记为 is_hot=True（用于前端显示"热"标签）。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。

    Returns:
        成功响应，data 包含 list/total/page/page_size。
        list 中每项包含 keyword/count/is_hot（是否为前 3 名）。
    """
    # 统计各关键词的搜索次数（按次数降序）
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
        rank = (page - 1) * page_size + index + 1  # 全局排名（跨页）
        data.append(
            {
                "keyword": row.keyword,
                "count": int(row.count or 0),
                "is_hot": rank <= 3,  # 前 3 名标记为热搜
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
    current_user: User | None = Depends(get_optional_user),
):
    """获取推荐关注的创作者列表（按总阅读量和文章数排序）。

    推荐策略：
      - 统计每位作者的已发布文章数和总阅读量
      - 按总阅读量降序、文章数降序排列
      - 返回 Top-limit 创作者

    Args:
        limit: 返回创作者数量，默认 6。
        db: 数据库会话。
        current_user: 当前用户（用于标记是否已关注），未登录时为 None。

    Returns:
        成功响应，data 包含 list。
        list 中每项包含 user_id/name/desc/article_count/view_count/follower_count/followed。
    """
    # 联表查询：统计每位作者的文章数和总阅读量
    rows = (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.email.label("email"),
            User.phone.label("phone"),
            func.count(Article.id).label("article_count"),       # 文章数
            func.sum(Article.view_count).label("view_count"),    # 总阅读量
        )
        .join(Article, Article.author_id == User.id)
        .filter(Article.is_deleted == False, Article.status == "published")
        .group_by(User.id, User.username, User.email, User.phone)
        .order_by(desc("view_count"), desc("article_count"))     # 按阅读量降序
        .limit(limit)
        .all()
    )

    # 获取当前用户已关注的用户 ID 集合（用于标记 followed 字段）
    followed_user_ids = set()
    if current_user:
        followed_user_ids = {
            int(row.following_id)
            for row in db.query(UserFollow.following_id)
            .filter(UserFollow.follower_id == current_user.id)
            .all()
        }

    data = []
    for row in rows:
        article_count = int(row.article_count or 0)
        view_count = int(row.view_count or 0)
        # 查询该创作者的粉丝数
        follower_count = (
            db.query(UserFollow)
            .filter(UserFollow.following_id == row.user_id)
            .count()
        )
        data.append(
            {
                "user_id": row.user_id,
                "name": _format_user_name(row.username, row.email, row.phone),
                "desc": f"{article_count} 篇文章 · {view_count} 阅读 · {follower_count} 关注者",
                "article_count": article_count,
                "view_count": view_count,
                "follower_count": follower_count,
                "followed": row.user_id in followed_user_ids,  # 当前用户是否已关注
            }
        )
    return success_response({"list": data})
