#!/usr/bin/env python3
import json
import os
import random
import string
import time
import urllib.request


def build_headers(token):
    """Build HTTP headers for JSON request.

    Args:
        token (str): Bearer token for authorization.

    Returns:
        dict: Headers dictionary.
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def random_words(word_count):
    """Generate random word list.

    Args:
        word_count (int): Number of words to generate.

    Returns:
        str: Random word string.
    """
    words = []
    for _ in range(word_count):
        word = "".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(4, 10)))
        words.append(word)
    return " ".join(words)


def build_article_payload(index):
    """Build article payload for publish API.

    Args:
        index (int): Article index number.

    Returns:
        dict: Article payload.
    """
    title = f"测试文章 {index}"
    category = random.choice(["技术", "产品", "设计", "随笔"])
    tags = ",".join(random.sample(["AI", "Vue", "推荐系统", "前端", "数据分析"], k=2))
    content = f"# {title}\n\n{random_words(60)}\n\n{random_words(80)}\n"
    return {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags,
        "status": "published",
    }


def post_json(url, payload, headers):
    """Send POST request with JSON payload.

    Args:
        url (str): API endpoint URL.
        payload (dict): JSON payload.
        headers (dict): Request headers.

    Returns:
        dict: Parsed response data.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def main():
    """Generate test articles in batch via API.

    Returns:
        None: Script exit point.
    """
    base_url = os.environ.get("BLOG_BASE_URL", "http://localhost:8000/api")
    token = os.environ.get("BLOG_TOKEN", "")
    count = int(os.environ.get("BLOG_ARTICLE_COUNT", "10"))

    publish_url = f"{base_url}/article/publish"
    headers = build_headers(token)

    for index in range(1, count + 1):
        payload = build_article_payload(index)
        response = post_json(publish_url, payload, headers)
        if response.get("code") != 0:
            print(f"[{index}] failed: {response.get('message')}")
        else:
            print(f"[{index}] ok: article_id={response.get('data', {}).get('article_id')}")
        time.sleep(0.2)


if __name__ == "__main__":
    main()
