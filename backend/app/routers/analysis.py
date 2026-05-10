"""
routers/analysis.py —— 数据分析路由模块

提供作者/管理员查看数据分析报表的 API 接口：
  - GET /analysis/read-trend        : 阅读趋势（PV/UV/时长/滚动深度，按日/周/月聚合）
  - GET /analysis/recommend-effect  : 推荐效果（CTR 点击率、转化率、来源分布）
  - GET /analysis/user-portrait     : 用户画像（兴趣标签、活跃时段、行为分布）
  - GET /analysis/active-heatmap    : 活跃热力图（日期×小时的行为频次矩阵）
  - GET /analysis/content-performance: 内容表现（文章阅读/点赞/收藏/评论排行）

权限控制：
  - 普通用户只能查看自己的数据（user_id 必须等于当前登录用户 ID）
  - 管理员可以查看任意用户的数据
"""

from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.behavior import UserBehavior
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User

router = APIRouter()


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _parse_start_date(value: str) -> datetime:
    """将 'YYYY-MM-DD' 格式的日期字符串解析为当天 00:00:00 的 datetime 对象。

    Args:
        value (str): 日期字符串，格式 "YYYY-MM-DD"。

    Returns:
        datetime: 当天 00:00:00 的 datetime 对象。
    """
    return datetime.strptime(value, "%Y-%m-%d")


def _parse_end_date(value: str) -> datetime:
    """将 'YYYY-MM-DD' 格式的日期字符串解析为当天 23:59:59.999999 的 datetime 对象。

    用于时间范围查询的结束边界，确保包含当天最后一刻的数据。

    Args:
        value (str): 日期字符串，格式 "YYYY-MM-DD"。

    Returns:
        datetime: 当天 23:59:59.999999 的 datetime 对象。
    """
    day = datetime.strptime(value, "%Y-%m-%d").date()
    return datetime.combine(day, time.max)


def _build_conversion_lookup(
    db: Session, user_id: int, start_dt: datetime, end_dt: datetime
) -> dict[int, list[datetime]]:
    """构建"转化行为"查找表，用于快速判断某次推荐点击后是否发生了转化。

    转化行为定义：用户在点击推荐后，对该文章执行了收藏（collect）或评论（comment）操作。

    Args:
        db: 数据库会话。
        user_id: 用户 ID。
        start_dt: 查询开始时间。
        end_dt: 查询结束时间。

    Returns:
        dict[int, list[datetime]]: 以文章 ID 为键，转化行为时间列表（升序）为值的字典。
            用于 bisect_left 二分查找，快速判断某时间点之后是否有转化。
    """
    rows = (
        db.query(UserBehavior.article_id, UserBehavior.create_time)
        .filter(
            UserBehavior.user_id == user_id,
            UserBehavior.article_id.isnot(None),
            UserBehavior.behavior_type.in_(["collect", "comment"]),  # 转化行为类型
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .order_by(UserBehavior.article_id, UserBehavior.create_time)
        .all()
    )
    # 按文章 ID 分组，每组内时间列表已升序排列（ORDER BY 保证）
    conversion_lookup: dict[int, list[datetime]] = defaultdict(list)
    for article_id, create_time in rows:
        conversion_lookup[int(article_id)].append(create_time)
    return conversion_lookup


def _has_conversion_after(
    conversion_lookup: dict[int, list[datetime]],
    article_id: int | None,
    start_time: datetime,
    end_time: datetime,
) -> bool:
    """判断某篇文章在指定时间窗口内是否发生了转化行为。

    使用二分查找（bisect_left）在已排序的时间列表中快速定位，
    时间复杂度 O(log n)，避免线性扫描。

    Args:
        conversion_lookup: 由 _build_conversion_lookup 构建的查找表。
        article_id: 文章 ID，为 None 时直接返回 False。
        start_time: 时间窗口开始（推荐点击时间）。
        end_time: 时间窗口结束（通常为查询结束时间）。

    Returns:
        bool: 在 [start_time, end_time] 内有转化行为返回 True，否则 False。
    """
    if article_id is None:
        return False
    timestamps = conversion_lookup.get(int(article_id), [])
    if not timestamps:
        return False
    # 二分查找：找到第一个 >= start_time 的位置
    index = bisect_left(timestamps, start_time)
    # 检查该位置的时间是否在 end_time 之内
    return index < len(timestamps) and timestamps[index] <= end_time


def _safe_rate_change_ratio(current: float, previous: float) -> float | None:
    """安全计算环比变化率：(current - previous) / previous。

    当 previous <= 0 时返回 None，避免除零错误。

    Args:
        current: 当前周期的指标值。
        previous: 上一周期的指标值。

    Returns:
        float | None: 变化率（正数表示增长，负数表示下降），previous <= 0 时返回 None。
    """
    if previous <= 0:
        return None
    return (current - previous) / previous


# ── 路由处理函数 ──────────────────────────────────────────────────────────────

@router.get("/analysis/read-trend")
def read_trend(
    user_id: int,
    start_date: str,
    end_date: str,
    granularity: str = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文章阅读趋势数据。

    按指定时间粒度（日/周/月）聚合该作者文章的阅读数据，
    返回 PV（页面浏览量）、UV（独立访客数）、平均阅读时长、平均滚动深度。

    Args:
        user_id: 要查询的作者用户 ID。
        start_date: 查询开始日期，格式 "YYYY-MM-DD"。
        end_date: 查询结束日期，格式 "YYYY-MM-DD"。
        granularity: 时间粒度，"day"（日）/ "week"（周）/ "month"（月），默认 "day"。
        db: 数据库会话。
        current_user: 当前登录用户（权限校验用）。

    Returns:
        成功响应，data 包含：
          - dates: 时间桶列表
          - read_counts / pv_counts: 各时间桶 PV 数
          - uv_counts: 各时间桶 UV 数
          - total_pv / total_uv: 总 PV/UV
          - avg_read_duration: 各时间桶平均阅读时长（秒）
          - avg_scroll_depth: 各时间桶平均滚动深度（0.0~1.0）
    """
    # 权限校验：普通用户只能查自己的数据
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    start_dt = _parse_start_date(start_date)
    end_dt = _parse_end_date(end_date)

    # 根据粒度选择 MySQL 日期格式化函数
    if granularity == "month":
        group_key = func.date_format(UserBehavior.create_time, "%Y-%m")   # 按月聚合
    elif granularity == "week":
        group_key = func.date_format(UserBehavior.create_time, "%Y-%u")   # 按周聚合（%u=周数）
    else:
        group_key = func.date(UserBehavior.create_time)                    # 按日聚合（默认）

    # 聚合查询：JOIN article 表过滤出该作者的文章阅读行为
    query = (
        db.query(
            group_key.label("bucket"),
            func.count(UserBehavior.id).label("read_count"),                          # PV
            func.count(func.distinct(UserBehavior.user_id)).label("uv_count"),        # UV（去重）
            func.avg(UserBehavior.read_duration).label("avg_duration"),               # 平均阅读时长
            func.avg(UserBehavior.scroll_depth).label("avg_scroll_depth"),            # 平均滚动深度
        )
        .join(Article, Article.id == UserBehavior.article_id)
        .filter(
            UserBehavior.behavior_type == "read",
            Article.author_id == user_id,
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .group_by(group_key)
        .order_by(group_key)
    )

    # 将查询结果转换为列表格式
    dates: List[str] = []
    read_counts: List[int] = []
    uv_counts: List[int] = []
    avg_read_duration: List[int] = []
    avg_scroll_depth: List[float] = []
    for row in query:
        dates.append(str(row.bucket))
        read_counts.append(int(row.read_count or 0))
        uv_counts.append(int(row.uv_count or 0))
        avg_read_duration.append(int(row.avg_duration or 0))
        avg_scroll_depth.append(round(float(row.avg_scroll_depth or 0.0), 4))

    # 汇总查询：计算整个时间段的总 PV 和总 UV
    summary_row = (
        db.query(
            func.count(UserBehavior.id).label("total_pv"),
            func.count(func.distinct(UserBehavior.user_id)).label("total_uv"),
        )
        .join(Article, Article.id == UserBehavior.article_id)
        .filter(
            UserBehavior.behavior_type == "read",
            Article.author_id == user_id,
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .first()
    )
    total_pv = int(summary_row.total_pv or 0) if summary_row else 0
    total_uv = int(summary_row.total_uv or 0) if summary_row else 0

    return success_response(
        {
            "dates": dates,
            "read_counts": read_counts,
            "pv_counts": read_counts,       # pv_counts 与 read_counts 相同，兼容前端字段名
            "uv_counts": uv_counts,
            "total_pv": total_pv,
            "total_uv": total_uv,
            "avg_read_duration": avg_read_duration,
            "avg_scroll_depth": avg_scroll_depth,
        }
    )


@router.get("/analysis/recommend-effect")
def recommend_effect(
    user_id: int,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取推荐效果分析数据。

    统计指定时间段内推荐系统的效果指标：
      - 曝光量（impressions）：推荐记录总数
      - 点击量（clicks）：用户点击了推荐的次数
      - 转化量（conversions）：点击后发生收藏/评论的次数
      - CTR（点击率）= clicks / impressions
      - 转化率 = conversions / clicks
      - 按推荐来源（recommend_type）分组的效果明细
      - 按日期分组的每日效果趋势
      - 与上一个等长周期的环比对比数据

    Args:
        user_id: 要查询的用户 ID。
        start_date: 查询开始日期，格式 "YYYY-MM-DD"。
        end_date: 查询结束日期，格式 "YYYY-MM-DD"。
        db: 数据库会话。
        current_user: 当前登录用户（权限校验用）。
    """
    # 权限校验
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    start_dt = _parse_start_date(start_date)
    end_dt = _parse_end_date(end_date)
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")

    # 查询当前周期内该用户的所有推荐记录（按时间升序）
    recommendations = (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.create_time >= start_dt,
            Recommendation.create_time <= end_dt,
        )
        .order_by(Recommendation.create_time.asc())
        .all()
    )
    # 构建转化查找表，用于快速判断每次点击是否发生了转化
    conversion_lookup = _build_conversion_lookup(db, user_id, start_dt, end_dt)

    # 计算总体指标
    impressions = len(recommendations)                                          # 总曝光量
    clicked_recommendations = [item for item in recommendations if item.is_clicked]
    clicks = len(clicked_recommendations)                                       # 总点击量

    # 统计转化量：遍历所有点击记录，判断是否在点击后发生了转化
    conversions = sum(
        1
        for recommendation in clicked_recommendations
        if _has_conversion_after(
            conversion_lookup,
            recommendation.article_id,
            recommendation.create_time,
            end_dt,
        )
    )

    # 计算总体 CTR 和转化率
    ctr = float(clicks) / float(impressions) if impressions else 0.0
    conversion = float(conversions) / float(clicks) if clicks else 0.0

    # 按推荐来源（recommend_type）分组统计
    source_bucket: dict[str, dict[str, int]] = defaultdict(
        lambda: {"impressions": 0, "clicks": 0, "conversions": 0}
    )
    for recommendation in recommendations:
        source_key = str(recommendation.recommend_type or "unknown")
        source_bucket[source_key]["impressions"] += 1
        if recommendation.is_clicked:
            source_bucket[source_key]["clicks"] += 1

    for recommendation in clicked_recommendations:
        source_key = str(recommendation.recommend_type or "unknown")
        if _has_conversion_after(
            conversion_lookup,
            recommendation.article_id,
            recommendation.create_time,
            end_dt,
        ):
            source_bucket[source_key]["conversions"] += 1

    # 按日期分组统计每日效果趋势
    daily_bucket: dict[str, dict[str, int]] = defaultdict(
        lambda: {"impressions": 0, "clicks": 0, "conversions": 0}
    )
    for recommendation in recommendations:
        day_key = recommendation.create_time.date().isoformat()
        daily_bucket[day_key]["impressions"] += 1
        if recommendation.is_clicked:
            daily_bucket[day_key]["clicks"] += 1

    for recommendation in clicked_recommendations:
        day_key = recommendation.create_time.date().isoformat()
        # 转化时间窗口：从点击时刻到当天结束（或查询结束时间，取较小值）
        day_end = min(datetime.combine(recommendation.create_time.date(), time.max), end_dt)
        if _has_conversion_after(
            conversion_lookup,
            recommendation.article_id,
            recommendation.create_time,
            day_end,
        ):
            daily_bucket[day_key]["conversions"] += 1

    # 构建每日趋势列表（按日期升序排列）
    daily = []
    for day_key in sorted(daily_bucket.keys()):
        row = daily_bucket[day_key]
        day_impressions = int(row["impressions"])
        day_clicks = int(row["clicks"])
        day_conversions = int(row["conversions"])
        daily.append(
            {
                "date": day_key,
                "impressions": day_impressions,
                "clicks": day_clicks,
                "conversions": day_conversions,
                "ctr": float(day_clicks) / float(day_impressions) if day_impressions else 0.0,
                "conversion": float(day_conversions) / float(day_clicks) if day_clicks else 0.0,
            }
        )

    # 计算平均每日 CTR 和转化率，以及最佳表现日期
    average_daily_ctr = (
        sum(float(item["ctr"]) for item in daily) / float(len(daily)) if daily else 0.0
    )
    average_daily_conversion = (
        sum(float(item["conversion"]) for item in daily) / float(len(daily)) if daily else 0.0
    )
    best_ctr_day = max(daily, key=lambda item: float(item["ctr"])) if daily else None
    best_conversion_day = max(daily, key=lambda item: float(item["conversion"])) if daily else None

    # 计算上一个等长周期的数据（用于环比对比）
    period_days = max(1, (end_dt.date() - start_dt.date()).days + 1)
    previous_end_dt = start_dt - timedelta(microseconds=1)
    previous_start_dt = previous_end_dt - timedelta(days=period_days) + timedelta(microseconds=1)
    previous_recommendations = (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.create_time >= previous_start_dt,
            Recommendation.create_time <= previous_end_dt,
        )
        .all()
    )
    previous_conversion_lookup = _build_conversion_lookup(
        db, user_id, previous_start_dt, previous_end_dt
    )
    previous_impressions = len(previous_recommendations)
    previous_clicked_recommendations = [
        item for item in previous_recommendations if item.is_clicked
    ]
    previous_clicks = len(previous_clicked_recommendations)
    previous_conversions = sum(
        1
        for recommendation in previous_clicked_recommendations
        if _has_conversion_after(
            previous_conversion_lookup,
            recommendation.article_id,
            recommendation.create_time,
            previous_end_dt,
        )
    )
    previous_ctr = (
        float(previous_clicks) / float(previous_impressions) if previous_impressions else 0.0
    )
    previous_conversion = (
        float(previous_conversions) / float(previous_clicks) if previous_clicks else 0.0
    )

    # 构建推荐来源分布列表（按曝光量降序排列）
    source_breakdown = []
    for source_key, row in sorted(
        source_bucket.items(),
        key=lambda item: (-int(item[1]["impressions"]), item[0]),
    ):
        source_impressions = int(row["impressions"])
        source_clicks = int(row["clicks"])
        source_conversions = int(row["conversions"])
        source_breakdown.append(
            {
                "recommend_type": source_key,
                "impressions": source_impressions,
                "clicks": source_clicks,
                "conversions": source_conversions,
                "ctr": float(source_clicks) / float(source_impressions)
                if source_impressions
                else 0.0,
                "conversion": float(source_conversions) / float(source_clicks)
                if source_clicks
                else 0.0,
            }
        )

    return success_response(
        {
            "click_through_rate": ctr,          # 总点击率
            "conversion_rate": conversion,       # 总转化率
            "impressions": impressions,          # 总曝光量
            "clicks": clicks,                    # 总点击量
            "conversions": conversions,          # 总转化量
            "daily": daily,                      # 每日趋势
            "source_breakdown": source_breakdown, # 来源分布
            "comparison": {                      # 环比对比数据
                "average_daily_ctr": average_daily_ctr,
                "average_daily_conversion": average_daily_conversion,
                "best_ctr_date": best_ctr_day["date"] if best_ctr_day else None,
                "best_ctr": float(best_ctr_day["ctr"]) if best_ctr_day else 0.0,
                "best_conversion_date": best_conversion_day["date"]
                if best_conversion_day
                else None,
                "best_conversion": float(best_conversion_day["conversion"])
                if best_conversion_day
                else 0.0,
                "previous_click_through_rate": previous_ctr,
                "previous_conversion_rate": previous_conversion,
                "click_through_rate_change": ctr - previous_ctr,
                "conversion_rate_change": conversion - previous_conversion,
                "click_through_rate_change_ratio": _safe_rate_change_ratio(ctr, previous_ctr),
                "conversion_rate_change_ratio": _safe_rate_change_ratio(
                    conversion, previous_conversion
                ),
            },
        }
    )


@router.get("/analysis/user-portrait")
def user_portrait(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户画像数据。

    分析用户的行为数据，生成多维度的用户画像：
      - 兴趣标签 TOP10（来自 preference_tags 字段）
      - 活跃时段分布（24 小时热力图）
      - 行为类型分布（阅读/点赞/收藏/评论/搜索占比）
      - 偏好分类 TOP10（基于阅读行为统计）
      - 近期搜索关键词 TOP10
      - 平均阅读时长和滚动深度统计

    Args:
        user_id: 要查询的用户 ID。
        db: 数据库会话。
        current_user: 当前登录用户（权限校验用）。
    """
    # 权限校验
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 解析用户偏好标签（逗号分隔字符串 → Counter）
    tag_counter = Counter()
    if user.preference_tags:
        for tag in user.preference_tags.split(","):
            tag = tag.strip()
            if tag:
                tag_counter[tag] += 1

    # 查询最近 1000 条行为记录（按时间降序，避免全表扫描）
    behaviors = (
        db.query(UserBehavior)
        .filter(UserBehavior.user_id == user_id)
        .order_by(UserBehavior.create_time.desc())
        .limit(1000)
        .all()
    )

    # 初始化统计容器
    active_hours = Counter()        # 各小时活跃次数
    behavior_counter = Counter()    # 各行为类型次数
    read_durations = []             # 阅读时长列表
    scroll_depths = []              # 滚动深度列表
    category_counter = Counter()    # 各分类阅读次数
    keyword_counter = Counter()     # 各搜索词次数

    # 批量查询行为涉及的文章（避免 N+1 查询问题）
    article_ids = list({item.article_id for item in behaviors if item.article_id})
    article_map: dict[int, Article] = {}
    if article_ids:
        for article in db.query(Article).filter(Article.id.in_(article_ids)).all():
            article_map[article.id] = article

    # 遍历行为记录，统计各维度数据
    for behavior in behaviors:
        active_hours[behavior.create_time.hour] += 1           # 统计活跃小时
        behavior_counter[behavior.behavior_type] += 1          # 统计行为类型
        if behavior.read_duration:
            read_durations.append(int(behavior.read_duration))
        if behavior.scroll_depth is not None:
            # 将滚动深度限制在 [0.0, 1.0] 范围内（防止异常数据）
            depth = max(0.0, min(float(behavior.scroll_depth), 1.0))
            scroll_depths.append(depth)
        if behavior.behavior_type == "search" and behavior.keyword:
            keyword_counter[behavior.keyword] += 1             # 统计搜索词
        if behavior.article_id and article_map.get(behavior.article_id):
            category = article_map[behavior.article_id].category
            if category:
                category_counter[category] += 1                # 统计偏好分类

    # 构建各维度分析结果
    interest_tags_top10 = [
        {"tag": tag, "weight": weight / 10.0}
        for tag, weight in tag_counter.most_common(10)
    ]
    active_hours_data = [
        {"hour": hour, "count": count}
        for hour, count in sorted(active_hours.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    # 完整 24 小时数据（用于热力图展示）
    active_hours_full = [{"hour": hour, "count": int(active_hours.get(hour, 0))} for hour in range(24)]
    # 活跃峰值时段（取前 3 个有数据的小时）
    active_peak_hours = [
        item
        for item in sorted(active_hours_full, key=lambda item: (-item["count"], item["hour"]))
        if item["count"] > 0
    ][:3]
    behavior_distribution = [
        {"behavior_type": behavior_type, "count": count}
        for behavior_type, count in behavior_counter.most_common(10)
    ]
    preferred_categories = [
        {"category": category, "count": count}
        for category, count in category_counter.most_common(10)
    ]
    recent_search_keywords = [
        {"keyword": keyword, "count": count}
        for keyword, count in keyword_counter.most_common(10)
    ]
    # 计算平均阅读时长和滚动深度
    avg_read_duration = int(sum(read_durations) / len(read_durations)) if read_durations else 0
    avg_scroll_depth = round(float(sum(scroll_depths) / len(scroll_depths)), 4) if scroll_depths else 0.0
    max_scroll_depth = round(max(scroll_depths), 4) if scroll_depths else 0.0

    # 滚动深度分布（分为 4 个区间）
    scroll_depth_distribution = [
        {"range": "0-25%", "count": 0},
        {"range": "25-50%", "count": 0},
        {"range": "50-75%", "count": 0},
        {"range": "75-100%", "count": 0},
    ]
    for depth in scroll_depths:
        if depth < 0.25:
            scroll_depth_distribution[0]["count"] += 1
        elif depth < 0.5:
            scroll_depth_distribution[1]["count"] += 1
        elif depth < 0.75:
            scroll_depth_distribution[2]["count"] += 1
        else:
            scroll_depth_distribution[3]["count"] += 1

    return success_response(
        {
            "interest_tags_top10": interest_tags_top10,
            "active_hours": active_hours_data,
            "active_hours_full": active_hours_full,
            "active_peak_hours": active_peak_hours,
            "behavior_distribution": behavior_distribution,
            "preferred_categories": preferred_categories,
            "recent_search_keywords": recent_search_keywords,
            "avg_read_duration": avg_read_duration,
            "avg_scroll_depth": avg_scroll_depth,
            "max_scroll_depth": max_scroll_depth,
            "scroll_depth_distribution": scroll_depth_distribution,
        }
    )


@router.get("/analysis/active-heatmap")
def active_heatmap(
    user_id: int,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户活跃热力图数据。

    返回最近 N 天内，用户每天每小时的行为频次矩阵，
    用于前端渲染日期×小时的热力图（ECharts heatmap）。

    Args:
        user_id: 要查询的用户 ID。
        days: 查询天数，范围 1-30，默认 7 天。
        db: 数据库会话。
        current_user: 当前登录用户（权限校验用）。

    Returns:
        成功响应，data 包含：
          - dates: 日期列表（YYYY-MM-DD 格式）
          - hours: 小时列表（0-23）
          - values: 热力图数据，格式 [[日期索引, 小时, 频次], ...]
          - total_events: 总行为次数
          - peak_hours: 活跃峰值时段（前 3 个）
    """
    # 权限校验
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="days must be between 1 and 30")

    # 计算查询时间范围（最近 N 天）
    end_day = datetime.utcnow().date()
    start_day = end_day - timedelta(days=days - 1)
    start_dt = datetime.combine(start_day, time.min)
    end_dt = datetime.combine(end_day, time.max)

    # 查询时间范围内的所有行为记录（只需要时间字段）
    rows = (
        db.query(UserBehavior.create_time)
        .filter(
            UserBehavior.user_id == user_id,
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .all()
    )

    # 构建日期列表和初始化矩阵
    date_keys = [
        (start_day + timedelta(days=offset)).isoformat()
        for offset in range(days)
    ]
    hour_keys = list(range(24))
    # matrix[日期索引][小时] = 行为次数
    matrix = [[0 for _ in hour_keys] for _ in date_keys]
    hour_counter = Counter()

    # 建立日期→索引的映射，加速查找
    date_index_map = {date_key: index for index, date_key in enumerate(date_keys)}
    for row in rows:
        create_time = row.create_time
        date_key = create_time.date().isoformat()
        hour = int(create_time.hour)
        date_index = date_index_map.get(date_key)
        if date_index is None:
            continue
        matrix[date_index][hour] += 1
        hour_counter[hour] += 1

    # 将矩阵转换为 ECharts heatmap 所需的 [x, y, value] 格式
    values = []
    for date_index, hours in enumerate(matrix):
        for hour, count in enumerate(hours):
            values.append([date_index, hour, int(count)])

    # 计算活跃峰值时段（前 3 个）
    peak_hours = [
        {"hour": int(hour), "count": int(count)}
        for hour, count in sorted(hour_counter.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]

    return success_response(
        {
            "dates": date_keys,
            "hours": hour_keys,
            "values": values,
            "total_events": int(len(rows)),
            "peak_hours": peak_hours,
        }
    )


@router.get("/analysis/content-performance")
def content_performance(
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取内容表现分析数据。

    返回该作者文章的阅读/点赞/收藏/评论排行，以及各分类的热度统计。

    热度分数计算公式：
      hot_score = view_count + like_count × 3 + collect_count × 5 + comment_count × 4

    Args:
        user_id: 要查询的作者用户 ID。
        limit: 返回文章数量上限，默认 10。
        db: 数据库会话。
        current_user: 当前登录用户（权限校验用）。

    Returns:
        成功响应，data 包含：
          - articles: 文章表现列表（按阅读量降序）
          - category_stats: 分类热度统计（按热度分数降序，最多 8 个分类）
    """
    # 权限校验
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    # 查询已发布且未删除的文章
    query = db.query(Article).filter(
        Article.is_deleted == False,
        Article.status == "published",
    )
    # 普通用户只能查自己的文章，管理员可查所有文章
    if current_user.role != "admin":
        query = query.filter(Article.author_id == user_id)
    all_articles = query.all()

    # 按阅读量降序排列，取前 limit 篇
    articles = sorted(all_articles, key=lambda item: item.view_count, reverse=True)[:limit]
    data = []
    category_hot = Counter()    # 各分类热度分数
    category_views = Counter()  # 各分类总阅读量
    category_articles = Counter()  # 各分类文章数

    for item in articles:
        # 互动率 = (点赞 + 收藏 + 评论) / 阅读量
        engagement = (item.like_count + item.collect_count + item.comment_count) / max(
            item.view_count, 1
        )
        data.append(
            {
                "article_id": item.id,
                "title": item.title,
                "view_count": item.view_count,
                "like_count": item.like_count,
                "collect_count": item.collect_count,
                "comment_count": item.comment_count,
                "engagement_rate": round(engagement, 4),  # 互动率，保留 4 位小数
            }
        )

    # 统计所有文章的分类热度（不限于 top limit）
    for item in all_articles:
        category = (item.category or "uncategorized").strip() or "uncategorized"
        # 热度分数：阅读 ×1 + 点赞 ×3 + 收藏 ×5 + 评论 ×4
        hot_score = (
            float(item.view_count)
            + float(item.like_count) * 3.0
            + float(item.collect_count) * 5.0
            + float(item.comment_count) * 4.0
        )
        category_hot[category] += hot_score
        category_views[category] += int(item.view_count or 0)
        category_articles[category] += 1

    # 构建分类统计列表（取热度最高的 8 个分类）
    category_stats = [
        {
            "category": category,
            "hot_score": round(float(score), 4),
            "view_count": int(category_views.get(category, 0)),
            "article_count": int(category_articles.get(category, 0)),
        }
        for category, score in category_hot.most_common(8)
    ]

    return success_response({"articles": data, "category_stats": category_stats})
