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


def _parse_start_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _parse_end_date(value: str) -> datetime:
    day = datetime.strptime(value, "%Y-%m-%d").date()
    return datetime.combine(day, time.max)


def _build_conversion_lookup(
    db: Session, user_id: int, start_dt: datetime, end_dt: datetime
) -> dict[int, list[datetime]]:
    rows = (
        db.query(UserBehavior.article_id, UserBehavior.create_time)
        .filter(
            UserBehavior.user_id == user_id,
            UserBehavior.article_id.isnot(None),
            UserBehavior.behavior_type.in_(["collect", "comment"]),
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .order_by(UserBehavior.article_id, UserBehavior.create_time)
        .all()
    )
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
    if article_id is None:
        return False
    timestamps = conversion_lookup.get(int(article_id), [])
    if not timestamps:
        return False
    index = bisect_left(timestamps, start_time)
    return index < len(timestamps) and timestamps[index] <= end_time


def _safe_rate_change_ratio(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return (current - previous) / previous


@router.get("/analysis/read-trend")
def read_trend(
    user_id: int,
    start_date: str,
    end_date: str,
    granularity: str = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    start_dt = _parse_start_date(start_date)
    end_dt = _parse_end_date(end_date)
    if granularity == "month":
        group_key = func.date_format(UserBehavior.create_time, "%Y-%m")
    elif granularity == "week":
        group_key = func.date_format(UserBehavior.create_time, "%Y-%u")
    else:
        group_key = func.date(UserBehavior.create_time)

    query = (
        db.query(
            group_key.label("bucket"),
            func.count(UserBehavior.id).label("read_count"),
            func.count(func.distinct(UserBehavior.user_id)).label("uv_count"),
            func.avg(UserBehavior.read_duration).label("avg_duration"),
            func.avg(UserBehavior.scroll_depth).label("avg_scroll_depth"),
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
            "pv_counts": read_counts,
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
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    start_dt = _parse_start_date(start_date)
    end_dt = _parse_end_date(end_date)
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="开始日期不能大于结束日期")

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
    conversion_lookup = _build_conversion_lookup(db, user_id, start_dt, end_dt)

    impressions = len(recommendations)
    clicked_recommendations = [item for item in recommendations if item.is_clicked]
    clicks = len(clicked_recommendations)

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

    ctr = float(clicks) / float(impressions) if impressions else 0.0
    conversion = float(conversions) / float(clicks) if clicks else 0.0

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
        day_end = min(datetime.combine(recommendation.create_time.date(), time.max), end_dt)
        if _has_conversion_after(
            conversion_lookup,
            recommendation.article_id,
            recommendation.create_time,
            day_end,
        ):
            daily_bucket[day_key]["conversions"] += 1

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

    average_daily_ctr = (
        sum(float(item["ctr"]) for item in daily) / float(len(daily)) if daily else 0.0
    )
    average_daily_conversion = (
        sum(float(item["conversion"]) for item in daily) / float(len(daily)) if daily else 0.0
    )
    best_ctr_day = max(daily, key=lambda item: float(item["ctr"])) if daily else None
    best_conversion_day = max(daily, key=lambda item: float(item["conversion"])) if daily else None

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
            "click_through_rate": ctr,
            "conversion_rate": conversion,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "daily": daily,
            "source_breakdown": source_breakdown,
            "comparison": {
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
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    tag_counter = Counter()
    if user.preference_tags:
        for tag in user.preference_tags.split(","):
            tag = tag.strip()
            if tag:
                tag_counter[tag] += 1

    behaviors = (
        db.query(UserBehavior)
        .filter(UserBehavior.user_id == user_id)
        .order_by(UserBehavior.create_time.desc())
        .limit(1000)
        .all()
    )
    active_hours = Counter()
    behavior_counter = Counter()
    read_durations = []
    scroll_depths = []
    category_counter = Counter()
    keyword_counter = Counter()

    article_ids = list({item.article_id for item in behaviors if item.article_id})
    article_map: dict[int, Article] = {}
    if article_ids:
        for article in db.query(Article).filter(Article.id.in_(article_ids)).all():
            article_map[article.id] = article

    for behavior in behaviors:
        active_hours[behavior.create_time.hour] += 1
        behavior_counter[behavior.behavior_type] += 1
        if behavior.read_duration:
            read_durations.append(int(behavior.read_duration))
        if behavior.scroll_depth is not None:
            depth = max(0.0, min(float(behavior.scroll_depth), 1.0))
            scroll_depths.append(depth)
        if behavior.behavior_type == "search" and behavior.keyword:
            keyword_counter[behavior.keyword] += 1
        if behavior.article_id and article_map.get(behavior.article_id):
            category = article_map[behavior.article_id].category
            if category:
                category_counter[category] += 1

    interest_tags_top10 = [
        {"tag": tag, "weight": weight / 10.0}
        for tag, weight in tag_counter.most_common(10)
    ]
    active_hours_data = [
        {"hour": hour, "count": count}
        for hour, count in sorted(active_hours.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    active_hours_full = [{"hour": hour, "count": int(active_hours.get(hour, 0))} for hour in range(24)]
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
    avg_read_duration = int(sum(read_durations) / len(read_durations)) if read_durations else 0
    avg_scroll_depth = round(float(sum(scroll_depths) / len(scroll_depths)), 4) if scroll_depths else 0.0
    max_scroll_depth = round(max(scroll_depths), 4) if scroll_depths else 0.0
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
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="days must be between 1 and 30")

    end_day = datetime.utcnow().date()
    start_day = end_day - timedelta(days=days - 1)
    start_dt = datetime.combine(start_day, time.min)
    end_dt = datetime.combine(end_day, time.max)

    rows = (
        db.query(UserBehavior.create_time)
        .filter(
            UserBehavior.user_id == user_id,
            UserBehavior.create_time >= start_dt,
            UserBehavior.create_time <= end_dt,
        )
        .all()
    )

    date_keys = [
        (start_day + timedelta(days=offset)).isoformat()
        for offset in range(days)
    ]
    hour_keys = list(range(24))
    matrix = [[0 for _ in hour_keys] for _ in date_keys]
    hour_counter = Counter()

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

    values = []
    for date_index, hours in enumerate(matrix):
        for hour, count in enumerate(hours):
            values.append([date_index, hour, int(count)])

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
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")

    query = db.query(Article).filter(
        Article.is_deleted == False,
        Article.status == "published",
    )
    if current_user.role != "admin":
        query = query.filter(Article.author_id == user_id)
    all_articles = query.all()
    articles = sorted(all_articles, key=lambda item: item.view_count, reverse=True)[:limit]
    data = []
    category_hot = Counter()
    category_views = Counter()
    category_articles = Counter()
    for item in articles:
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
                "engagement_rate": round(engagement, 4),
            }
        )

    for item in all_articles:
        category = (item.category or "uncategorized").strip() or "uncategorized"
        hot_score = (
            float(item.view_count)
            + float(item.like_count) * 3.0
            + float(item.collect_count) * 5.0
            + float(item.comment_count) * 4.0
        )
        category_hot[category] += hot_score
        category_views[category] += int(item.view_count or 0)
        category_articles[category] += 1

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
