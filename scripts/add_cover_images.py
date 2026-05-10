#!/usr/bin/env python3
"""为热度前十的文章添加封面图片。

使用 picsum.photos 提供的随机图片作为封面，
将 markdown 图片语法插入到文章 content 开头，
同时更新 html_content 字段。
"""

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

# 为每篇文章分配不同主题的封面图（使用 picsum seed 确保稳定）
COVER_IMAGES = {
    115: "https://picsum.photos/seed/recommend/800/400",
    122: "https://picsum.photos/seed/evaluation/800/400",
    119: "https://picsum.photos/seed/collab/800/400",
    118: "https://picsum.photos/seed/portrait/800/400",
    117: "https://picsum.photos/seed/analytics/800/400",
    116: "https://picsum.photos/seed/dashboard/800/400",
    120: "https://picsum.photos/seed/semantic/800/400",
    121: "https://picsum.photos/seed/responsive/800/400",
    51: "https://picsum.photos/seed/aitech/800/400",
    71: "https://picsum.photos/seed/backend/800/400",
}


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for article_id, cover_url in COVER_IMAGES.items():
        # 获取当前 content
        cursor.execute("SELECT content FROM article WHERE id = %s", (article_id,))
        row = cursor.fetchone()
        if not row:
            print(f"[{article_id}] 文章不存在，跳过")
            continue

        old_content = row[0]

        # 如果已经有图片则跳过
        if "![" in old_content[:200]:
            print(f"[{article_id}] 已有封面图，跳过")
            continue

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
        print(f"[{article_id}] 已添加封面图: {cover_url}")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ 完成！热度前十文章已全部添加封面图片。")


if __name__ == "__main__":
    main()
