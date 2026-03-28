from __future__ import annotations

import argparse
import math
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import jieba
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.db.init_db import init_db  # noqa: E402
from backend.app.db.session import SessionLocal  # noqa: E402
from backend.app.models.article import Article  # noqa: E402
from backend.app.models.behavior import UserBehavior  # noqa: E402
from backend.app.models.user import User  # noqa: E402,F401

INTERACTION_TYPES = {"read", "like", "collect", "comment"}
STOPWORDS_FILE = ROOT / "backend" / "app" / "resources" / "stopwords_zh.txt"
DEFAULT_STOPWORDS = {
    "的",
    "了",
    "和",
    "是",
    "在",
    "就",
    "都",
    "而",
    "及",
    "与",
    "着",
    "或",
    "一个",
    "一种",
    "没有",
    "我们",
    "你们",
    "他们",
    "它们",
    "我",
    "你",
    "他",
    "她",
    "它",
    "this",
    "that",
    "with",
    "for",
    "from",
    "into",
    "are",
    "was",
    "were",
    "be",
    "been",
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "is",
    "by",
    "as",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline evaluation for blog recommendation with 8:2 split."
    )
    parser.add_argument("--top-k", type=int, default=10, help="Top-K recommendations.")
    parser.add_argument(
        "--min-interactions",
        type=int,
        default=5,
        help="Minimum interactions required per user to participate in evaluation.",
    )
    parser.add_argument(
        "--neighbors",
        type=int,
        default=20,
        help="Number of nearest users used for collaborative scoring.",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=0,
        help="Maximum users to evaluate, 0 means no limit.",
    )
    return parser.parse_args()


def load_stopwords() -> set[str]:
    words = set(DEFAULT_STOPWORDS)
    if STOPWORDS_FILE.exists():
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token:
                words.add(token)
    return words


def clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = re.sub(r"[_*#>`~\-\[\]\(\)!\"'“”‘’·,，.。:：;；/\\|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


def tokenize(text: str, stopwords: set[str]) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    tokens: list[str] = []
    for token in jieba.lcut(cleaned, cut_all=False):
        value = token.strip().lower()
        if not value or value in stopwords:
            continue
        if not re.fullmatch(r"[a-z0-9\u4e00-\u9fff]+", value):
            continue
        if re.fullmatch(r"[a-z0-9]+", value) and len(value) <= 1:
            continue
        tokens.append(value)
    return tokens


def article_to_text(article: Article) -> str:
    return " ".join(
        [
            article.title or "",
            article.summary or "",
            article.content or "",
            article.category or "",
            article.tags or "",
        ]
    )


def read_duration_score(read_duration: int | None) -> float:
    duration = int(read_duration or 0)
    if duration <= 0:
        return 1.0
    if duration < 30:
        return 1.0
    if duration < 90:
        return 2.0
    if duration < 180:
        return 3.0
    if duration < 300:
        return 4.0
    return 5.0


def behavior_score(behavior: UserBehavior) -> float:
    behavior_type = str(behavior.behavior_type or "").lower()
    if behavior_type == "read":
        return read_duration_score(behavior.read_duration)
    if behavior_type == "like":
        return 4.0
    if behavior_type == "collect":
        return 5.0
    if behavior_type == "comment":
        return 5.0
    return 1.0


def normalize_scores(score_map: dict[int, float]) -> dict[int, float]:
    if not score_map:
        return {}
    max_value = max(score_map.values())
    if max_value <= 0:
        return {key: 0.0 for key in score_map}
    return {key: value / max_value for key, value in score_map.items()}


def dict_cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(value * b.get(key, 0.0) for key, value in a.items())
    if dot <= 0:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _random_words(rng: random.Random, count: int) -> str:
    """Generate deterministic pseudo content for synthetic data."""

    vocab = [
        "recommendation",
        "system",
        "ranking",
        "recall",
        "precision",
        "embedding",
        "tfidf",
        "cosine",
        "similarity",
        "python",
        "fastapi",
        "mysql",
        "frontend",
        "vue",
        "react",
        "analytics",
        "abtest",
        "nlp",
        "vector",
        "user",
        "profile",
        "article",
        "content",
        "feature",
        "model",
        "training",
        "dataset",
        "evaluation",
        "metric",
        "experiment",
    ]
    return " ".join(rng.choices(vocab, k=count))


def seed_synthetic_data(
    db,
    min_articles: int = 80,
    min_behaviors: int = 600,
    random_seed: int = 20240328,
) -> tuple[int, int, int]:
    """Populate minimal demo data so the evaluation script can run independently.

    Returns:
        tuple[int, int, int]: Added (users, articles, behaviors).
    """

    existing_articles = db.query(Article).count()
    existing_behaviors = (
        db.query(UserBehavior)
        .filter(
            UserBehavior.user_id.isnot(None),
            UserBehavior.article_id.isnot(None),
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
        )
        .count()
    )

    if existing_articles >= min_articles and existing_behaviors >= min_behaviors:
        print(
            "Synthetic seeding skipped: existing dataset already meets "
            f"{min_articles} articles and {min_behaviors} interactions."
        )
        return (0, 0, 0)

    rng = random.Random(random_seed)
    categories = [
        ("ai", ["nlp", "cv", "embedding", "recommendation"]),
        ("frontend", ["vue", "react", "css", "typescript"]),
        ("backend", ["fastapi", "mysql", "redis", "celery"]),
        ("product", ["analytics", "growth", "abtest", "ux"]),
    ]

    # Users
    existing_users = db.query(User).count()
    target_users = max(12, min_articles // 6)
    users: list[User] = []
    for index in range(target_users):
        name = f"demo_user_{existing_users + index + 1}"
        preferred = rng.sample(categories, k=2)
        preference_tags = ",".join({pref[0] for pref in preferred})
        user = User(
            username=name,
            email=f"{name}@example.com",
            password_hash="demo-hash",
            role="user",
            preference_tags=preference_tags,
        )
        db.add(user)
        users.append(user)
    db.flush()  # obtain user ids

    # Articles
    target_articles = max(min_articles - existing_articles, 0)
    articles: list[Article] = []
    for index in range(target_articles):
        category, tag_candidates = rng.choice(categories)
        tags = ",".join(rng.sample(tag_candidates, k=min(2, len(tag_candidates))))
        title = f"Demo Article {existing_articles + index + 1} - {category}"
        paragraph_a = _random_words(rng, 80)
        paragraph_b = _random_words(rng, 60)
        content = f"# {title}\n\n{paragraph_a}\n\n{paragraph_b}"
        summary = " ".join(paragraph_a.split()[:32])
        author = rng.choice(users)
        article = Article(
            author_id=author.id,
            title=title,
            content=content,
            html_content=f"<h1>{title}</h1><p>{paragraph_a}</p><p>{paragraph_b}</p>",
            summary=summary,
            category=category,
            tags=tags,
            status="published",
            view_count=rng.randint(50, 200),
        )
        db.add(article)
        articles.append(article)
    db.flush()  # obtain article ids

    # Behaviors
    target_behaviors = max(min_behaviors - existing_behaviors, 0)
    behavior_types = ["read", "like", "collect", "comment"]
    behaviors_added = 0
    for user in users:
        preferred_categories = user.preference_tags.split(",") if user.preference_tags else []
        user_articles = [a for a in articles if a.category in preferred_categories] or articles
        per_user = rng.randint(30, 80)
        for _ in range(per_user):
            if behaviors_added >= target_behaviors and target_behaviors > 0:
                break
            article = rng.choice(user_articles if rng.random() < 0.7 else articles)
            btype = rng.choices(behavior_types, weights=[0.55, 0.2, 0.15, 0.1], k=1)[0]
            created_at = datetime.utcnow() - timedelta(days=rng.randint(0, 28), minutes=rng.randint(0, 1440))
            behavior = UserBehavior(
                user_id=user.id,
                article_id=article.id,
                behavior_type=btype,
                read_duration=rng.randint(30, 420) if btype == "read" else None,
                scroll_depth=round(rng.uniform(0.2, 1.0), 2) if btype == "read" else None,
                create_time=created_at,
            )
            db.add(behavior)
            behaviors_added += 1
        if behaviors_added >= target_behaviors and target_behaviors > 0:
            break

    try:
        db.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        db.rollback()
        print(f"Synthetic data seeding failed: {exc}")
        return (0, 0, 0)

    print(
        f"Synthetic data ready: users={len(users)}, "
        f"articles={len(articles)}, behaviors={behaviors_added}"
    )
    return (len(users), len(articles), behaviors_added)


def main() -> None:
    args = parse_args()
    stopwords = load_stopwords()

    # Ensure tables exist before accessing data.
    init_db()

    db = SessionLocal()
    try:
        seed_synthetic_data(db)

        articles = (
            db.query(Article)
            .filter(Article.is_deleted == False, Article.status == "published")
            .all()
        )
        if not articles:
            print("No published articles found, evaluation aborted.")
            return

        article_ids = [article.id for article in articles]
        article_id_set = set(article_ids)
        article_index = {article_id: index for index, article_id in enumerate(article_ids)}
        article_texts = [article_to_text(article) for article in articles]

        vectorizer = TfidfVectorizer(
            tokenizer=lambda value: tokenize(value, stopwords),
            token_pattern=None,
            preprocessor=lambda value: value,
            lowercase=False,
            max_features=12000,
            ngram_range=(1, 2),
        )
        tfidf_matrix = vectorizer.fit_transform(article_texts)

        behaviors = (
            db.query(UserBehavior)
            .filter(
                UserBehavior.user_id.isnot(None),
                UserBehavior.article_id.isnot(None),
                UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
            )
            .order_by(UserBehavior.create_time.asc())
            .all()
        )

        user_records: dict[int, list[UserBehavior]] = defaultdict(list)
        for behavior in behaviors:
            if behavior.article_id not in article_id_set:
                continue
            user_records[int(behavior.user_id)].append(behavior)

        train_user_item: dict[int, dict[int, float]] = {}
        test_user_items: dict[int, set[int]] = {}
        for user_id, records in user_records.items():
            if len(records) < max(2, args.min_interactions):
                continue
            split_index = int(len(records) * 0.8)
            split_index = min(max(split_index, 1), len(records) - 1)
            train_records = records[:split_index]
            test_records = records[split_index:]

            train_map: dict[int, float] = defaultdict(float)
            for item in train_records:
                train_map[int(item.article_id)] += behavior_score(item)
            test_set = {int(item.article_id) for item in test_records}
            if not train_map or not test_set:
                continue
            train_user_item[user_id] = dict(train_map)
            test_user_items[user_id] = test_set

        user_ids = list(train_user_item.keys())
        if args.max_users > 0:
            user_ids = user_ids[: args.max_users]
        if not user_ids:
            print("No eligible users for evaluation after 8:2 split.")
            return

        precision_scores: list[float] = []
        recall_scores: list[float] = []
        hit_users = 0

        for user_id in user_ids:
            train_map = train_user_item[user_id]
            test_set = test_user_items.get(user_id, set())
            if not test_set:
                continue

            train_article_ids = [aid for aid in train_map.keys() if aid in article_index]
            candidate_ids = [aid for aid in article_ids if aid not in train_map]
            if not train_article_ids or not candidate_ids:
                continue

            # Content score with TF-IDF weighted profile.
            train_indices = [article_index[aid] for aid in train_article_ids]
            candidate_indices = [article_index[aid] for aid in candidate_ids]
            train_weights = np.array([max(train_map[aid], 0.1) for aid in train_article_ids], dtype=float)
            train_weights = train_weights / float(train_weights.sum())
            profile_vector = tfidf_matrix[train_indices].multiply(train_weights[:, np.newaxis]).sum(axis=0)
            profile_vector = csr_matrix(profile_vector)
            content_sim = cosine_similarity(tfidf_matrix[candidate_indices], profile_vector).ravel()
            content_scores = {aid: float(content_sim[idx]) for idx, aid in enumerate(candidate_ids)}

            # Collaborative score with user-based cosine on train interactions.
            user_similarities: list[tuple[int, float]] = []
            for other_user_id in user_ids:
                if other_user_id == user_id:
                    continue
                similarity = dict_cosine(train_map, train_user_item[other_user_id])
                if similarity > 0:
                    user_similarities.append((other_user_id, similarity))
            user_similarities.sort(key=lambda item: item[1], reverse=True)
            neighbors = user_similarities[: args.neighbors]

            collab_scores: dict[int, float] = defaultdict(float)
            for neighbor_user_id, similarity in neighbors:
                neighbor_train_map = train_user_item[neighbor_user_id]
                for article_id, score in neighbor_train_map.items():
                    if article_id in train_map:
                        continue
                    collab_scores[article_id] += similarity * score

            content_norm = normalize_scores(content_scores)
            collab_norm = normalize_scores(dict(collab_scores))
            final_scores = {
                article_id: content_norm.get(article_id, 0.0) * 0.6
                + collab_norm.get(article_id, 0.0) * 0.4
                for article_id in candidate_ids
            }
            ranked_article_ids = [
                article_id
                for article_id, _ in sorted(final_scores.items(), key=lambda item: item[1], reverse=True)
            ]
            top_k_ids = ranked_article_ids[: args.top_k]
            if not top_k_ids:
                continue

            hits = len(set(top_k_ids) & test_set)
            precision = hits / float(args.top_k)
            recall = hits / float(len(test_set))
            precision_scores.append(precision)
            recall_scores.append(recall)
            if hits > 0:
                hit_users += 1

        if not precision_scores:
            print("No evaluable user after recommendation generation.")
            return

        avg_precision = sum(precision_scores) / float(len(precision_scores))
        avg_recall = sum(recall_scores) / float(len(recall_scores))
        hit_rate = hit_users / float(len(precision_scores))

        print("=== Offline Recommendation Evaluation (8:2 split) ===")
        print(f"Evaluated users: {len(precision_scores)}")
        print(f"Top-K: {args.top_k}")
        print(f"Precision@{args.top_k}: {avg_precision:.4f}")
        print(f"Recall@{args.top_k}: {avg_recall:.4f}")
        print(f"HitRate@{args.top_k}: {hit_rate:.4f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
