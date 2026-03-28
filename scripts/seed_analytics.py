#!/usr/bin/env python3
import json
import os
import random
import string
import time
import urllib.parse
import urllib.request


def build_headers(token, has_body):
    """Build HTTP headers for API request.

    Args:
        token (str | None): Bearer token for authorization.
        has_body (bool): Whether request includes JSON body.

    Returns:
        dict: Headers dictionary.
    """
    headers = {}
    if has_body:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url, method="GET", payload=None, token=None, params=None):
    """Send HTTP request and parse JSON response.

    Args:
        url (str): Request URL.
        method (str): HTTP method.
        payload (dict | None): JSON payload.
        token (str | None): Bearer token for authorization.
        params (dict | None): Query params.

    Returns:
        dict: Parsed JSON response.
    """
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = build_headers(token, payload is not None)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def random_words(word_count):
    """Generate random word list for content text.

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
    title = f"seed-article-{index}"
    category = random.choice(["tech", "product", "design", "notes"])
    tags = ",".join(random.sample(["ai", "vue", "recommendation", "frontend", "analytics"], k=2))
    content = f"# {title}\n\n{random_words(60)}\n\n{random_words(80)}\n"
    return {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags,
        "status": "published",
    }


def parse_tokens():
    """Parse token list from environment variables.

    Returns:
        list[str]: Token list.
    """
    token_list = os.environ.get("BLOG_TOKENS", "").strip()
    if token_list:
        return [token.strip() for token in token_list.split(",") if token.strip()]
    single = os.environ.get("BLOG_TOKEN", "").strip()
    return [single] if single else []


def build_base_url():
    """Read base url from environment and normalize.

    Returns:
        str: API base url.
    """
    base_url = os.environ.get("BLOG_BASE_URL", "http://localhost:8000/api").strip()
    return base_url.rstrip("/")


def sleep_with_jitter(base_ms):
    """Sleep for a short time to avoid overwhelming the API.

    Args:
        base_ms (int): Base sleep in milliseconds.

    Returns:
        None: No return value.
    """
    if base_ms <= 0:
        return
    jitter = random.randint(0, max(1, base_ms // 3))
    time.sleep((base_ms + jitter) / 1000.0)


def fetch_article_ids(base_url, token, page_size):
    """Fetch article ids for the current user.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        page_size (int): Page size for list API.

    Returns:
        list[int]: Article ids.
    """
    article_ids = []
    page = 1
    while True:
        response = request_json(
            f"{base_url}/article/my-list",
            params={"page": page, "page_size": page_size, "status": "published"},
            token=token,
        )
        if response.get("code") != 0:
            print(f"[article list] failed: {response.get('message')}")
            break
        data = response.get("data", {})
        items = data.get("list", [])
        if not items:
            break
        article_ids.extend([item["article_id"] for item in items if item.get("article_id")])
        page += 1
    return article_ids


def fetch_global_article_ids(base_url, page_size):
    """Fetch global published article ids.

    Args:
        base_url (str): API base url.
        page_size (int): Page size for list API.

    Returns:
        list[int]: Article ids.
    """
    article_ids = []
    page = 1
    while True:
        response = request_json(
            f"{base_url}/article/list",
            params={"page": page, "page_size": page_size},
        )
        if response.get("code") != 0:
            print(f"[article list] failed: {response.get('message')}")
            break
        data = response.get("data", {})
        items = data.get("list", [])
        if not items:
            break
        article_ids.extend([item["article_id"] for item in items if item.get("article_id")])
        page += 1
    return article_ids


def create_articles(base_url, token, count):
    """Create articles for the current user.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        count (int): Number of articles to create.

    Returns:
        list[int]: Created article ids.
    """
    article_ids = []
    for index in range(1, count + 1):
        payload = build_article_payload(index)
        response = request_json(
            f"{base_url}/article/publish", method="POST", payload=payload, token=token
        )
        if response.get("code") != 0:
            print(f"[publish] failed: {response.get('message')}")
        else:
            article_id = response.get("data", {}).get("article_id")
            if article_id:
                article_ids.append(article_id)
        sleep_with_jitter(120)
    return article_ids


def update_preference_tags(base_url, token, tags):
    """Update user preference tags to enrich portrait data.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        tags (str): Comma-separated tags.

    Returns:
        None: No return value.
    """
    response = request_json(
        f"{base_url}/user/preference",
        method="PUT",
        payload={"preference_tags": tags},
        token=token,
    )
    if response.get("code") != 0:
        print(f"[preference] failed: {response.get('message')}")


def simulate_views(base_url, article_ids, view_events, sleep_ms):
    """Simulate article detail views.

    Args:
        base_url (str): API base url.
        article_ids (list[int]): Article ids.
        view_events (int): Number of view events to generate.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        None: No return value.
    """
    if not article_ids:
        return
    for _ in range(view_events):
        article_id = random.choice(article_ids)
        request_json(f"{base_url}/article/detail", params={"article_id": article_id})
        sleep_with_jitter(sleep_ms)


def simulate_reads(base_url, token, article_ids, read_events, sleep_ms):
    """Simulate read behavior events.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        article_ids (list[int]): Article ids.
        read_events (int): Number of read events.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        None: No return value.
    """
    if not article_ids:
        return
    for _ in range(read_events):
        article_id = random.choice(article_ids)
        payload = {
            "article_id": article_id,
            "behavior_type": "read",
            "read_duration": random.randint(30, 420),
            "scroll_depth": round(random.uniform(0.2, 1.0), 2),
        }
        request_json(f"{base_url}/behavior/report", method="POST", payload=payload, token=token)
        sleep_with_jitter(sleep_ms)


def simulate_likes(base_url, token, article_ids, like_target, sleep_ms):
    """Simulate like actions for unique articles.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        article_ids (list[int]): Article ids.
        like_target (int): Number of likes to attempt.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        None: No return value.
    """
    if not article_ids:
        return
    sample = random.sample(article_ids, k=min(like_target, len(article_ids)))
    for article_id in sample:
        payload = {"article_id": article_id, "action": "like"}
        request_json(f"{base_url}/article/like", method="POST", payload=payload, token=token)
        sleep_with_jitter(sleep_ms)


def simulate_collects(base_url, token, article_ids, collect_target, sleep_ms):
    """Simulate collect actions for unique articles.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        article_ids (list[int]): Article ids.
        collect_target (int): Number of collects to attempt.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        None: No return value.
    """
    if not article_ids:
        return
    sample = random.sample(article_ids, k=min(collect_target, len(article_ids)))
    for article_id in sample:
        payload = {"article_id": article_id, "action": "collect"}
        request_json(f"{base_url}/article/collect", method="POST", payload=payload, token=token)
        sleep_with_jitter(sleep_ms)


def simulate_comments(base_url, token, article_ids, comment_target, sleep_ms):
    """Simulate comment actions.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        article_ids (list[int]): Article ids.
        comment_target (int): Number of comments to post.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        None: No return value.
    """
    if not article_ids:
        return
    for index in range(comment_target):
        article_id = random.choice(article_ids)
        payload = {
            "article_id": article_id,
            "content": f"seed-comment-{index + 1}",
            "parent_id": 0,
        }
        request_json(f"{base_url}/behavior/comment", method="POST", payload=payload, token=token)
        sleep_with_jitter(sleep_ms)


def simulate_recommendations(base_url, token, pages, page_size, sleep_ms):
    """Trigger recommendation list to generate exposure records.

    Args:
        base_url (str): API base url.
        token (str): Auth token.
        pages (int): Page count to request.
        page_size (int): Page size for recommendation list.
        sleep_ms (int): Sleep interval in milliseconds.

    Returns:
        list[int]: Article ids from recommendation list.
    """
    article_ids = []
    for page in range(1, pages + 1):
        response = request_json(
            f"{base_url}/recommend/list",
            params={"page": page, "page_size": page_size},
            token=token,
        )
        if response.get("code") != 0:
            print(f"[recommend list] failed: {response.get('message')}")
            break
        data = response.get("data", {})
        items = data.get("list", [])
        article_ids.extend([item["article_id"] for item in items if item.get("article_id")])
        sleep_with_jitter(sleep_ms)
    return article_ids


def main():
    """Seed analytics-related data via API."""
    base_url = build_base_url()
    tokens = parse_tokens()
    page_size = int(os.environ.get("BLOG_PAGE_SIZE", "10"))
    create_articles_count = int(os.environ.get("BLOG_ARTICLE_COUNT", "20"))
    create_articles_enabled = os.environ.get("BLOG_CREATE_ARTICLES", "0") == "1"
    view_events = int(os.environ.get("BLOG_VIEW_EVENTS", "200"))
    read_events = int(os.environ.get("BLOG_READ_EVENTS", "200"))
    like_target = int(os.environ.get("BLOG_LIKE_TARGET", "20"))
    collect_target = int(os.environ.get("BLOG_COLLECT_TARGET", "10"))
    comment_target = int(os.environ.get("BLOG_COMMENT_TARGET", "20"))
    recommend_pages = int(os.environ.get("BLOG_RECOMMEND_PAGES", "5"))
    sleep_ms = int(os.environ.get("BLOG_SLEEP_MS", "120"))
    preference_tags = os.environ.get("BLOG_PREFERENCE_TAGS", "")

    if not tokens:
        print("No token found. Set BLOG_TOKEN or BLOG_TOKENS for authenticated actions.")
        return

    all_article_ids = fetch_global_article_ids(base_url, page_size)
    if not all_article_ids:
        print("No global articles found. You may need to publish articles first.")

    for token_index, token in enumerate(tokens, start=1):
        print(f"Seeding for token {token_index}/{len(tokens)}")
        if preference_tags:
            update_preference_tags(base_url, token, preference_tags)
        else:
            random_tags = ",".join(random.sample(["ai", "vue", "recommendation", "frontend"], k=2))
            update_preference_tags(base_url, token, random_tags)

        my_article_ids = fetch_article_ids(base_url, token, page_size)
        if not my_article_ids and create_articles_enabled:
            my_article_ids = create_articles(base_url, token, create_articles_count)
        if not my_article_ids:
            my_article_ids = all_article_ids

        recommend_ids = simulate_recommendations(
            base_url, token, recommend_pages, page_size, sleep_ms
        )
        candidate_ids = list({*my_article_ids, *recommend_ids}) or all_article_ids

        simulate_views(base_url, candidate_ids, view_events, sleep_ms)
        simulate_reads(base_url, token, candidate_ids, read_events, sleep_ms)
        simulate_likes(base_url, token, candidate_ids, like_target, sleep_ms)
        simulate_collects(base_url, token, candidate_ids, collect_target, sleep_ms)
        simulate_comments(base_url, token, candidate_ids, comment_target, sleep_ms)

    print("Seeding completed.")


if __name__ == "__main__":
    main()
