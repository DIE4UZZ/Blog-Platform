#!/usr/bin/env python3
"""
seed_extend_data.py —— 补充数据生成脚本

功能：
1. 生成 2026-05-06 到 2026-05-13 的行为数据（延续 seed_paper_demo_data.ps1 的数据）
2. 为 paper_demo_user 添加关注流（follow）和通知（notification）数据

使用方式：
    cd /Users/mac/Desktop/Blog-Platform
    python3 scripts/seed_extend_data.py

依赖：pymysql（已在 backend/requirements.txt 中）
"""

import pymysql
import random
import json
import urllib.request
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============ 配置 ============
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "blog_platform"
BASE_URL = "http://127.0.0.1:8000/api"
DEMO_PASSWORD = "123456"

# 数据日期范围
START_DATE = datetime(2026, 5, 6)
END_DATE = datetime(2026, 5, 13)

# Demo 用户名
DEMO_USERNAME = "paper_demo_user"
SOCIAL_USERNAMES = [
    "paper_demo_author_ai",
    "paper_demo_author_frontend",
    "paper_demo_author_data",
    "paper_demo_reader_a",
    "paper_demo_reader_b",
]


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_user_id(cursor, username):
    """根据用户名获取用户ID"""
    cursor.execute("SELECT id FROM user WHERE username = %s LIMIT 1", (username,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    return None


def get_demo_article_ids(cursor, user_id):
    """获取 demo 用户的文章ID列表"""
    cursor.execute(
        "SELECT id FROM article WHERE author_id = %s AND title LIKE 'Paper Demo - %%' ORDER BY create_time ASC",
        (user_id,),
    )
    return [row["id"] for row in cursor.fetchall()]


def get_social_article_ids(cursor, author_ids):
    """获取社交用户的文章ID列表"""
    if not author_ids:
        return []
    placeholders = ",".join(["%s"] * len(author_ids))
    cursor.execute(
        f"SELECT id, author_id, title FROM article WHERE author_id IN ({placeholders}) AND title LIKE 'Paper Social - %%' ORDER BY create_time ASC",
        author_ids,
    )
    return cursor.fetchall()


def get_external_article_ids(cursor, demo_user_id, limit=30):
    """获取外部文章ID"""
    cursor.execute(
        "SELECT id FROM article WHERE is_deleted = 0 AND status = 'published' AND author_id <> %s ORDER BY id LIMIT %s",
        (demo_user_id, limit),
    )
    return [row["id"] for row in cursor.fetchall()]


def get_all_reader_ids(cursor, demo_user_id, limit=12):
    """获取其他用户ID作为读者"""
    cursor.execute(
        "SELECT id FROM user WHERE id <> %s ORDER BY id LIMIT %s",
        (demo_user_id, limit),
    )
    return [row["id"] for row in cursor.fetchall()]


def escape_str(value):
    """转义字符串用于SQL"""
    if value is None:
        return "NULL"
    return pymysql.converters.escape_string(str(value))


def api_request(url, method="POST", payload=None, token=None):
    """发送 API 请求"""
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"code": -1, "message": str(e)}


def ensure_user(cursor, conn, username, email, password=DEMO_PASSWORD, preference_tags=""):
    """确保用户存在，不存在则直接插入数据库"""
    uid = get_user_id(cursor, username)
    if uid:
        return uid

    print(f"    创建用户 {username}...")
    password_hash = pwd_context.hash(password)
    now = datetime.utcnow()
    cursor.execute(
        "INSERT INTO user (username, email, password, role, preference_tags, create_time) VALUES (%s, %s, %s, %s, %s, %s)",
        (username, email, password_hash, "user", preference_tags or None, now),
    )
    conn.commit()

    # 重新查询 ID
    cursor.execute("SELECT id FROM user WHERE username = %s LIMIT 1", (username,))
    row = cursor.fetchone()
    return row["id"] if row else None


def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("补充数据生成脚本 (2026-05-06 ~ 2026-05-13)")
    print("=" * 60)

    # ============ 获取/创建用户 ============
    print("\n[1/7] 获取/创建用户...")
    demo_user_id = get_user_id(cursor, DEMO_USERNAME)
    if not demo_user_id:
        print(f"  错误：找不到用户 {DEMO_USERNAME}，请先确保该用户已注册")
        return

    # 社交用户配置
    social_user_specs = {
        "paper_demo_author_ai": {"email": "paper_demo_author_ai@example.com", "pref": "ai,recommendation,semantic"},
        "paper_demo_author_frontend": {"email": "paper_demo_author_frontend@example.com", "pref": "frontend,vue,responsive"},
        "paper_demo_author_data": {"email": "paper_demo_author_data@example.com", "pref": "analytics,visualization,behavior"},
        "paper_demo_reader_a": {"email": "paper_demo_reader_a@example.com", "pref": "ai,analytics,blog"},
        "paper_demo_reader_b": {"email": "paper_demo_reader_b@example.com", "pref": "frontend,design,content"},
    }

    social_user_ids = {}
    for username, spec in social_user_specs.items():
        uid = ensure_user(cursor, conn, username, spec["email"], preference_tags=spec["pref"])
        if uid:
            social_user_ids[username] = uid
        else:
            print(f"  警告：无法创建/获取用户 {username}")

    author_ai_id = social_user_ids.get("paper_demo_author_ai")
    author_frontend_id = social_user_ids.get("paper_demo_author_frontend")
    author_data_id = social_user_ids.get("paper_demo_author_data")
    reader_a_id = social_user_ids.get("paper_demo_reader_a")
    reader_b_id = social_user_ids.get("paper_demo_reader_b")

    all_social_ids = [v for v in social_user_ids.values() if v]
    print(f"  demo_user_id = {demo_user_id}")
    print(f"  social_user_ids = {social_user_ids}")

    # ============ 获取文章ID ============
    print("\n[2/7] 获取文章ID...")
    demo_article_ids = get_demo_article_ids(cursor, demo_user_id)
    social_articles = get_social_article_ids(cursor, all_social_ids)
    external_article_ids = get_external_article_ids(cursor, demo_user_id)
    reader_ids = get_all_reader_ids(cursor, demo_user_id)

    print(f"  demo文章数: {len(demo_article_ids)}")
    print(f"  social文章数: {len(social_articles)}")
    print(f"  外部文章数: {len(external_article_ids)}")
    print(f"  读者数: {len(reader_ids)}")

    if not demo_article_ids:
        print("  错误：没有找到 demo 文章，请先运行 seed_paper_demo_data.ps1")
        return

    # ============ 生成行为数据 (5月6日 ~ 5月13日) ============
    print("\n[3/7] 生成行为数据 (5月6日 ~ 5月13日)...")

    behavior_rows = []
    like_rows = []
    collect_rows = []
    comment_rows = []
    recommendation_rows = []

    # 已有的 like/collect 去重
    like_seen = set()
    collect_seen = set()

    # 查询已有的 like 和 collect 避免唯一约束冲突
    cursor.execute("SELECT user_id, article_id FROM article_like")
    for row in cursor.fetchall():
        like_seen.add(f"{row['user_id']}-{row['article_id']}")
    cursor.execute("SELECT user_id, article_id FROM article_collect")
    for row in cursor.fetchall():
        collect_seen.add(f"{row['user_id']}-{row['article_id']}")

    # 计算天数
    total_days = (END_DATE - START_DATE).days + 1  # 5月6日到5月13日 = 8天

    # 为每篇 demo 文章生成阅读行为
    for article_index, article_id in enumerate(demo_article_ids):
        for day_index in range(total_days):
            current_date = START_DATE + timedelta(days=day_index)
            reads_today = 2 + ((article_index + day_index) % 5)

            for read_index in range(reads_today):
                reader_id = reader_ids[(article_index + day_index + read_index) % len(reader_ids)]
                read_time = current_date + timedelta(
                    hours=9 + ((article_index * 2 + read_index * 3) % 10),
                    minutes=(read_index * 11 + article_index * 7) % 60,
                )
                duration = 70 + ((article_index * 31 + day_index * 17 + read_index * 13) % 320)
                depth = round(0.32 + (((article_index + day_index + read_index) % 11) * 0.06), 2)
                if depth > 0.98:
                    depth = 0.98

                behavior_rows.append(
                    (reader_id, article_id, "read", duration, depth, None, read_time)
                )

                # 点赞
                if (article_index + day_index + read_index) % 5 == 0:
                    like_key = f"{reader_id}-{article_id}"
                    if like_key not in like_seen:
                        like_seen.add(like_key)
                        like_rows.append((reader_id, article_id, read_time + timedelta(minutes=5)))

                # 收藏
                if (article_index + day_index + read_index) % 7 == 0:
                    collect_key = f"{reader_id}-{article_id}"
                    if collect_key not in collect_seen:
                        collect_seen.add(collect_key)
                        collect_rows.append((reader_id, article_id, read_time + timedelta(minutes=8)))

                # 评论
                if (article_index + day_index + read_index) % 6 == 0:
                    comment_time = read_time + timedelta(minutes=12)
                    comment_content = f"Insightful point #{article_index + day_index + read_index + 100}"
                    comment_rows.append((article_id, reader_id, comment_content, 0, comment_time))
                    behavior_rows.append(
                        (reader_id, article_id, "comment", None, None, None, comment_time)
                    )

    # 推荐数据
    recommend_types = ["hybrid", "content_semantic", "collaborative_filtering", "cold_start", "new_article_cold_start"]
    for day_index in range(total_days):
        current_date = START_DATE + timedelta(days=day_index)
        for rec_index, rec_type in enumerate(recommend_types):
            article_id = external_article_ids[(day_index + rec_index) % len(external_article_ids)]
            recommend_time = current_date + timedelta(hours=8 + rec_index * 2, minutes=(day_index * 7) % 45)
            clicked = 1 if ((day_index + rec_index) % 4) != 0 else 0
            score = round(0.48 + (rec_index * 0.09) + ((day_index % 5) * 0.03), 4)

            recommendation_rows.append(
                (demo_user_id, article_id, rec_type, score, clicked, recommend_time)
            )

            if clicked == 1:
                read_duration = 95 + ((day_index * 19 + rec_index * 23) % 280)
                scroll_depth = round(0.42 + ((day_index + rec_index) % 8) * 0.07, 2)
                if scroll_depth > 0.99:
                    scroll_depth = 0.99
                behavior_rows.append(
                    (demo_user_id, article_id, "read", read_duration, scroll_depth, None, recommend_time + timedelta(minutes=6))
                )

            if clicked == 1 and ((day_index + rec_index) % 3) == 0:
                convert_time = recommend_time + timedelta(minutes=18)
                behavior_rows.append(
                    (demo_user_id, article_id, "comment", None, None, None, convert_time)
                )
                comment_rows.append(
                    (article_id, demo_user_id, f"Demo conversion comment ext-{day_index + rec_index + 1}", 0, convert_time)
                )
            elif clicked == 1 and ((day_index + rec_index) % 4) == 0:
                convert_time = recommend_time + timedelta(minutes=20)
                behavior_rows.append(
                    (demo_user_id, article_id, "collect", None, None, None, convert_time)
                )

    # 搜索和页面浏览行为
    keywords = [
        "hybrid ranking", "vue charts", "reading analytics", "user portrait",
        "responsive layout", "content ranking", "ctr analysis", "tfidf recommend",
        "blog behavior", "dashboard design", "semantic recall", "collaborative score",
        "author analytics", "cold start", "engagement rate", "read duration",
        "scroll depth", "article similarity", "heatmap active hour", "category hotness",
        "conversion trend",
    ]
    global_article_ids = external_article_ids + demo_article_ids

    for day_index in range(total_days):
        current_date = START_DATE + timedelta(days=day_index)
        search_keyword = keywords[(day_index + 30) % len(keywords)]  # offset by 30 to avoid repeating original data
        behavior_rows.append(
            (demo_user_id, None, "search", None, None, search_keyword, current_date + timedelta(hours=9))
        )
        behavior_rows.append(
            (demo_user_id, None, "page_view", None, None, "/analysis/read-trend", current_date + timedelta(hours=9, minutes=3))
        )
        behavior_rows.append(
            (demo_user_id, None, "page_leave", None, None, "/analysis/read-trend", current_date + timedelta(hours=9, minutes=17))
        )

        # 额外的页面浏览（关注流和通知页面）
        behavior_rows.append(
            (demo_user_id, None, "page_view", None, None, "/feed/following", current_date + timedelta(hours=10, minutes=15))
        )
        behavior_rows.append(
            (demo_user_id, None, "page_leave", None, None, "/feed/following", current_date + timedelta(hours=10, minutes=28))
        )
        behavior_rows.append(
            (demo_user_id, None, "page_view", None, None, "/notifications", current_date + timedelta(hours=11, minutes=5))
        )
        behavior_rows.append(
            (demo_user_id, None, "page_leave", None, None, "/notifications", current_date + timedelta(hours=11, minutes=12))
        )

        # 点赞和收藏行为
        portrait_article_id = global_article_ids[(day_index + 30) % len(global_article_ids)]
        like_behavior_time = current_date + timedelta(hours=20, minutes=day_index * 3)
        collect_behavior_time = current_date + timedelta(hours=21, minutes=day_index * 2)
        behavior_rows.append(
            (demo_user_id, portrait_article_id, "like", None, None, None, like_behavior_time)
        )
        behavior_rows.append(
            (demo_user_id, portrait_article_id, "collect", None, None, None, collect_behavior_time)
        )

    print(f"  行为记录数: {len(behavior_rows)}")
    print(f"  点赞记录数: {len(like_rows)}")
    print(f"  收藏记录数: {len(collect_rows)}")
    print(f"  评论记录数: {len(comment_rows)}")
    print(f"  推荐记录数: {len(recommendation_rows)}")

    # ============ 生成关注数据 ============
    print("\n[4/7] 生成关注数据...")

    follow_rows = []

    # paper_demo_user 关注 3 个作者
    follow_targets = [author_ai_id, author_frontend_id, author_data_id]
    follow_times = [
        datetime(2026, 4, 8, 10, 30, 0),   # 较早关注
        datetime(2026, 4, 12, 14, 20, 0),
        datetime(2026, 4, 18, 9, 45, 0),
    ]

    # reader_a 和 reader_b 关注 paper_demo_user
    followers_of_demo = [reader_a_id, reader_b_id]
    follower_times = [
        datetime(2026, 4, 15, 16, 10, 0),
        datetime(2026, 5, 2, 11, 30, 0),
    ]

    # 作者之间互相关注（增加社交网络密度）
    cross_follows = [
        (author_ai_id, author_data_id, datetime(2026, 4, 10, 8, 0, 0)),
        (author_frontend_id, author_ai_id, datetime(2026, 4, 11, 9, 30, 0)),
        (reader_a_id, author_ai_id, datetime(2026, 4, 20, 15, 0, 0)),
        (reader_b_id, author_frontend_id, datetime(2026, 4, 22, 12, 0, 0)),
        (author_data_id, demo_user_id, datetime(2026, 5, 7, 14, 20, 0)),
    ]

    # 先清除已有的关注数据（避免唯一约束冲突）
    all_demo_ids = [demo_user_id] + all_social_ids
    placeholders = ",".join(["%s"] * len(all_demo_ids))
    cursor.execute(
        f"DELETE FROM user_follow WHERE follower_id IN ({placeholders}) OR following_id IN ({placeholders})",
        all_demo_ids + all_demo_ids,
    )

    # 插入 paper_demo_user 关注作者
    for target_id, follow_time in zip(follow_targets, follow_times):
        if target_id:
            follow_rows.append((demo_user_id, target_id, follow_time))

    # 插入 reader 关注 paper_demo_user
    for follower_id, follow_time in zip(followers_of_demo, follower_times):
        if follower_id:
            follow_rows.append((follower_id, demo_user_id, follow_time))

    # 插入交叉关注
    for follower_id, following_id, follow_time in cross_follows:
        if follower_id and following_id:
            follow_rows.append((follower_id, following_id, follow_time))

    print(f"  关注记录数: {len(follow_rows)}")

    # ============ 生成通知数据 ============
    print("\n[5/7] 生成通知数据...")

    notification_rows = []

    # 清除已有通知数据
    cursor.execute(
        f"DELETE FROM user_notification WHERE user_id IN ({placeholders}) OR actor_user_id IN ({placeholders})",
        all_demo_ids + all_demo_ids,
    )

    # 1. new_follower 通知：有人关注了 paper_demo_user
    if reader_a_id:
        notification_rows.append((
            demo_user_id, reader_a_id, None, None,
            "new_follower", "你有新的关注者",
            "paper_demo_reader_a 关注了你",
            False, datetime(2026, 4, 15, 16, 10, 0),
        ))
    if reader_b_id:
        notification_rows.append((
            demo_user_id, reader_b_id, None, None,
            "new_follower", "你有新的关注者",
            "paper_demo_reader_b 关注了你",
            False, datetime(2026, 5, 2, 11, 30, 0),
        ))
    if author_data_id:
        notification_rows.append((
            demo_user_id, author_data_id, None, None,
            "new_follower", "你有新的关注者",
            "paper_demo_author_data 关注了你",
            False, datetime(2026, 5, 7, 14, 20, 0),
        ))

    # 2. new_article 通知：关注的作者发布了新文章
    # 从 social_articles 中为 paper_demo_user 生成通知
    for article_info in social_articles:
        article_id = article_info["id"]
        author_id = article_info["author_id"]
        title = article_info["title"]

        # 确定作者名
        author_name = None
        for uname, uid in social_user_ids.items():
            if uid == author_id:
                author_name = uname
                break

        if author_id in follow_targets:
            # paper_demo_user 关注了这个作者，应该收到通知
            notification_rows.append((
                demo_user_id, author_id, article_id, None,
                "new_article", f"{author_name} 发布了新文章",
                title[:120],
                random.choice([True, True, False]),  # 部分已读
                # 通知时间比文章创建时间稍晚
                datetime(2026, 5, 7, 10, 0, 0) + timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59)),
            ))

    # 3. 为5月6日到5月13日期间生成更多 new_article 通知
    # 模拟关注的作者在这段时间发布新文章的通知
    new_article_notifications = [
        (author_ai_id, "paper_demo_author_ai", "Paper Social - Advanced Recall Strategy", datetime(2026, 5, 7, 9, 30, 0)),
        (author_frontend_id, "paper_demo_author_frontend", "Paper Social - Dark Mode Implementation", datetime(2026, 5, 8, 14, 15, 0)),
        (author_data_id, "paper_demo_author_data", "Paper Social - Behavior Funnel Analysis", datetime(2026, 5, 9, 11, 0, 0)),
        (author_ai_id, "paper_demo_author_ai", "Paper Social - Real-time Ranking Update", datetime(2026, 5, 10, 16, 45, 0)),
        (author_frontend_id, "paper_demo_author_frontend", "Paper Social - Component Library Design", datetime(2026, 5, 11, 10, 20, 0)),
        (author_data_id, "paper_demo_author_data", "Paper Social - User Retention Metrics", datetime(2026, 5, 12, 8, 50, 0)),
        (author_ai_id, "paper_demo_author_ai", "Paper Social - Embedding Similarity Search", datetime(2026, 5, 13, 15, 30, 0)),
    ]

    for author_id, author_name, article_title, notify_time in new_article_notifications:
        if author_id:
            notification_rows.append((
                demo_user_id, author_id, None, None,
                "new_article", f"{author_name} 发布了新文章",
                article_title[:120],
                random.choice([True, False]),
                notify_time,
            ))

    # 4. new_comment 通知：paper_demo_user 的文章收到评论
    comment_notification_data = [
        (reader_a_id, "paper_demo_reader_a", demo_article_ids[0] if len(demo_article_ids) > 0 else None, "Great article on hybrid recommendation!", datetime(2026, 5, 7, 12, 30, 0)),
        (reader_b_id, "paper_demo_reader_b", demo_article_ids[1] if len(demo_article_ids) > 1 else None, "Very helpful Vue dashboard tips!", datetime(2026, 5, 8, 15, 45, 0)),
        (author_ai_id, "paper_demo_author_ai", demo_article_ids[0] if len(demo_article_ids) > 0 else None, "Interesting approach to content ranking.", datetime(2026, 5, 9, 9, 20, 0)),
        (reader_a_id, "paper_demo_reader_a", demo_article_ids[2] if len(demo_article_ids) > 2 else None, "The behavior analytics section is insightful.", datetime(2026, 5, 10, 14, 10, 0)),
        (author_frontend_id, "paper_demo_author_frontend", demo_article_ids[1] if len(demo_article_ids) > 1 else None, "Nice responsive design patterns!", datetime(2026, 5, 11, 11, 0, 0)),
        (reader_b_id, "paper_demo_reader_b", demo_article_ids[3] if len(demo_article_ids) > 3 else None, "User portrait modeling is fascinating.", datetime(2026, 5, 12, 16, 30, 0)),
        (author_data_id, "paper_demo_author_data", demo_article_ids[2] if len(demo_article_ids) > 2 else None, "Good analysis on reading behavior.", datetime(2026, 5, 13, 10, 15, 0)),
    ]

    for actor_id, actor_name, article_id, content, notify_time in comment_notification_data:
        if actor_id and article_id:
            notification_rows.append((
                demo_user_id, actor_id, article_id, None,
                "new_comment", "你的文章收到了新评论",
                content[:120],
                random.choice([True, False, False]),  # 大部分未读
                notify_time,
            ))

    # 5. 通知其他用户（作者们收到关注通知）
    # paper_demo_user 关注了作者们 -> 作者们收到 new_follower 通知
    for target_id, follow_time in zip(follow_targets, follow_times):
        if target_id:
            notification_rows.append((
                target_id, demo_user_id, None, None,
                "new_follower", "你有新的关注者",
                "paper_demo_user 关注了你",
                True,  # 已读
                follow_time,
            ))

    print(f"  通知记录数: {len(notification_rows)}")

    # ============ 写入数据库 ============
    print("\n[6/7] 写入数据库...")

    # 插入行为数据
    if behavior_rows:
        sql = "INSERT INTO user_behavior (user_id, article_id, behavior_type, read_duration, scroll_depth, keyword, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, behavior_rows)
        print(f"  已插入 {cursor.rowcount} 条行为记录")

    # 插入点赞数据
    if like_rows:
        sql = "INSERT IGNORE INTO article_like (user_id, article_id, create_time) VALUES (%s, %s, %s)"
        cursor.executemany(sql, like_rows)
        print(f"  已插入 {cursor.rowcount} 条点赞记录")

    # 插入收藏数据
    if collect_rows:
        sql = "INSERT IGNORE INTO article_collect (user_id, article_id, create_time) VALUES (%s, %s, %s)"
        cursor.executemany(sql, collect_rows)
        print(f"  已插入 {cursor.rowcount} 条收藏记录")

    # 插入评论数据
    if comment_rows:
        sql = "INSERT INTO comment (article_id, user_id, content, parent_id, create_time) VALUES (%s, %s, %s, %s, %s)"
        cursor.executemany(sql, comment_rows)
        print(f"  已插入 {cursor.rowcount} 条评论记录")

    # 插入推荐数据
    if recommendation_rows:
        sql = "INSERT INTO recommendation (user_id, article_id, recommend_type, recommend_score, is_clicked, create_time) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, recommendation_rows)
        print(f"  已插入 {cursor.rowcount} 条推荐记录")

    # 插入关注数据
    if follow_rows:
        sql = "INSERT INTO user_follow (follower_id, following_id, create_time) VALUES (%s, %s, %s)"
        cursor.executemany(sql, follow_rows)
        print(f"  已插入 {cursor.rowcount} 条关注记录")

    # 插入通知数据
    if notification_rows:
        sql = "INSERT INTO user_notification (user_id, actor_user_id, article_id, comment_id, notification_type, title, content, is_read, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, notification_rows)
        print(f"  已插入 {cursor.rowcount} 条通知记录")

    # 更新文章的 like_count, collect_count, comment_count
    print("\n[7/7] 更新文章统计计数...")
    cursor.execute("""
        UPDATE article a SET
            like_count = (SELECT COUNT(*) FROM article_like WHERE article_id = a.id),
            collect_count = (SELECT COUNT(*) FROM article_collect WHERE article_id = a.id),
            comment_count = (SELECT COUNT(*) FROM comment WHERE article_id = a.id)
        WHERE a.id IN (
            SELECT DISTINCT article_id FROM article_like WHERE article_id IS NOT NULL
            UNION
            SELECT DISTINCT article_id FROM article_collect WHERE article_id IS NOT NULL
            UNION
            SELECT DISTINCT article_id FROM comment WHERE article_id IS NOT NULL
        )
    """)
    print(f"  已更新 {cursor.rowcount} 篇文章的统计计数")

    conn.commit()
    print("\n" + "=" * 60)
    print("数据生成完成！")
    print(f"  日期范围: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    print(f"  paper_demo_user 关注了: {len(follow_targets)} 个作者")
    print(f"  paper_demo_user 被关注: {len(followers_of_demo) + 1} 人")
    print(f"  通知总数: {len(notification_rows)}")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
