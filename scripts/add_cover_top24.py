#!/usr/bin/env python3
"""为排行榜热度前24且没有封面图的文章添加封面图片。

热度公式：阅读量×1 + 点赞量×3 + 收藏量×5 + 评论量×4
使用 picsum.photos 提供的随机图片作为封面，
将 markdown 图片语法插入到文章 content 开头，
同时更新 html_content 字段。
"""

import re
import pymysql
from markdown import markdown

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "blog_platform",
    "charset": "utf8mb4",
}

# 用于生成不同主题的封面图 seed 列表
COVER_SEEDS = [
    "tech", "code", "data", "cloud", "network",
    "design", "mobile", "server", "algorithm", "machine",
    "deep", "neural", "graph", "database", "security",
    "devops", "frontend", "api", "microservice", "container",
    "blockchain", "quantum", "robotics", "iot",
]


def has_cover_image(content: str) -> bool:
    """检查文章内容是否已有封面图。"""
    if not content:
        return False
    # 检查前300个字符中是否有图片
    head = content[:300]
    if "![" in head:
        return True
    if re.search(r'<img\s+[^>]*src=', head):
        return True
    return False


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 查询排行榜前24的文章（按热度降序）
    sql = """
        SELECT id, title, content,
               (view_count + like_count * 3 + collect_count * 5 + comment_count * 4) AS hot_score
        FROM article
        WHERE is_deleted = 0 AND status = 'published'
        ORDER BY hot_score DESC, create_time DESC
        LIMIT 24
    """
    cursor.execute(sql)
    rows = cursor.fetchall()

    print(f"排行榜前24文章共 {len(rows)} 篇\n")

    seed_index = 0
    updated_count = 0

    for article_id, title, content, hot_score in rows:
        if has_cover_image(content or ""):
            print(f"  [#{article_id}] 已有封面图，跳过 - {title[:30]}")
            continue

        # 分配一个 seed
        seed = COVER_SEEDS[seed_index % len(COVER_SEEDS)]
        cover_url = f"https://picsum.photos/seed/{seed}{article_id}/800/400"
        seed_index += 1

        old_content = content or ""

        # 在标题行后插入封面图
        lines = old_content.split("\n", 1)
        if len(lines) == 2:
            new_content = f"{lines[0]}\n\n![cover]({cover_url})\n\n{lines[1]}"
        else:
            new_content = f"{lines[0]}\n\n![cover]({cover_url})\n"

        # 重新生成 html_content
        new_html = markdown(new_content)

        cursor.execute(
            "UPDATE article SET content = %s, html_content = %s WHERE id = %s",
            (new_content, new_html, article_id),
        )
        updated_count += 1
        print(f"  [#{article_id}] ✅ 已添加封面图 (热度:{hot_score}) - {title[:30]}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n✅ 完成！共为 {updated_count} 篇文章添加了封面图片。")


if __name__ == "__main__":
    main()
