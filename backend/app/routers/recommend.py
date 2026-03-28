import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import jieba
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.app.core.deps import get_optional_user
from backend.app.core.response import success_response
from backend.app.db.session import get_db
from backend.app.models.article import Article
from backend.app.models.behavior import UserBehavior
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User

router = APIRouter()

INTERACTION_TYPES = {"read", "like", "collect", "comment"}
EXPLICIT_BEHAVIOR_SCORES = {
    "like": 4.0,
    "collect": 5.0,
    "comment": 5.0,
}
STOPWORDS_FILE = Path(__file__).resolve().parent.parent / "resources" / "stopwords_zh.txt"
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
    "没有",
    "我们",
    "你",
    "我",
    "他",
    "她",
    "它",
    "this",
    "that",
    "with",
    "for",
    "from",
    "into",
    "onto",
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


def _resolve_author_name(user: User | None) -> str | None:
    if not user:
        return None
    return user.username or user.email or user.phone


def _split_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _hot_score(article: Article) -> float:
    return (
        float(article.view_count)
        + float(article.like_count) * 3.0
        + float(article.collect_count) * 5.0
        + float(article.comment_count) * 4.0
    )


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return float(value) / float(max_value)


def _build_recommend_item(article: Article, recommend_type: str, score: float) -> dict:
    return {
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": _split_tags(article.tags),
        "author": {
            "user_id": article.author_id,
            "username": _resolve_author_name(article.author),
        },
        "view_count": article.view_count,
        "like_count": article.like_count,
        "collect_count": article.collect_count,
        "create_time": article.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "recommend_type": recommend_type,
        "recommend_score": round(score, 4),
    }


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = re.sub(r"[_*#>`~\-\[\]\(\)!\"'“”‘’·,，.。:：;；/\\|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


@lru_cache(maxsize=1)
def _load_stopwords() -> set[str]:
    words = set(DEFAULT_STOPWORDS)
    if STOPWORDS_FILE.exists():
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token:
                words.add(token)
    return words


def _tokenize_with_jieba(text: str) -> list[str]:
    stopwords = _load_stopwords()
    cleaned = _clean_text(text)
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


def _build_tfidf_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        tokenizer=_tokenize_with_jieba,
        token_pattern=None,
        preprocessor=lambda value: value,
        lowercase=False,
        max_features=12000,
        ngram_range=(1, 2),
    )


def _article_to_text(article: Article) -> str:
    parts = [
        article.title or "",
        article.summary or "",
        article.content or "",
        article.category or "",
        article.tags or "",
    ]
    return " ".join(parts)


def _read_duration_to_score(read_duration: int | None) -> float:
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


def _behavior_preference_score(behavior: UserBehavior) -> float:
    behavior_type = str(behavior.behavior_type or "").lower()
    if behavior_type == "read":
        return _read_duration_to_score(behavior.read_duration)
    return EXPLICIT_BEHAVIOR_SCORES.get(behavior_type, 1.0)


def _fetch_user_history(
    db: Session, current_user: User
) -> tuple[set[int], Counter[str], Counter[str], dict[int, float], dict[int, str]]:
    interacted_article_ids: set[int] = set()
    tag_weights: Counter[str] = Counter()
    category_weights: Counter[str] = Counter()
    history_article_weights: dict[int, float] = defaultdict(float)
    history_article_texts: dict[int, str] = {}

    if current_user.preference_tags:
        for tag in _split_tags(current_user.preference_tags):
            tag_weights[tag] += 3.0

    behaviors = (
        db.query(UserBehavior)
        .filter(
            UserBehavior.user_id == current_user.id,
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
            UserBehavior.article_id.isnot(None),
        )
        .order_by(desc(UserBehavior.create_time))
        .limit(1000)
        .all()
    )
    for behavior in behaviors:
        if behavior.article_id is None:
            continue
        article_id = int(behavior.article_id)
        interacted_article_ids.add(article_id)
        history_article_weights[article_id] += _behavior_preference_score(behavior)

    if not interacted_article_ids:
        return (
            interacted_article_ids,
            tag_weights,
            category_weights,
            history_article_weights,
            history_article_texts,
        )

    articles = (
        db.query(Article)
        .filter(Article.id.in_(interacted_article_ids), Article.is_deleted == False)
        .all()
    )
    for article in articles:
        score_factor = max(1.0, float(history_article_weights.get(article.id, 1.0)))
        for tag in _split_tags(article.tags):
            tag_weights[tag] += score_factor * 0.6
        if article.category:
            category_weights[article.category] += score_factor * 0.5
        history_article_texts[article.id] = _article_to_text(article)

    return (
        interacted_article_ids,
        tag_weights,
        category_weights,
        history_article_weights,
        history_article_texts,
    )


def _build_collaborative_scores(
    db: Session, current_user: User, interacted_article_ids: set[int]
) -> dict[int, float]:
    if not interacted_article_ids:
        return {}

    similar_user_rows = (
        db.query(
            UserBehavior.user_id.label("user_id"),
            func.count(UserBehavior.id).label("overlap"),
        )
        .filter(
            UserBehavior.user_id.isnot(None),
            UserBehavior.user_id != current_user.id,
            UserBehavior.article_id.in_(interacted_article_ids),
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
        )
        .group_by(UserBehavior.user_id)
        .order_by(desc("overlap"))
        .limit(50)
        .all()
    )
    if not similar_user_rows:
        return {}

    similar_user_weight = {int(row.user_id): float(row.overlap or 0) for row in similar_user_rows}
    candidate_behaviors = (
        db.query(UserBehavior)
        .filter(
            UserBehavior.user_id.in_(similar_user_weight.keys()),
            UserBehavior.article_id.isnot(None),
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
        )
        .all()
    )

    collaborative_scores: dict[int, float] = defaultdict(float)
    for behavior in candidate_behaviors:
        if behavior.article_id is None or behavior.user_id is None:
            continue
        article_id = int(behavior.article_id)
        if article_id in interacted_article_ids:
            continue
        user_weight = similar_user_weight.get(int(behavior.user_id), 0.0)
        behavior_weight = _behavior_preference_score(behavior)
        collaborative_scores[article_id] += user_weight * behavior_weight
    return collaborative_scores


def _build_profile_tag_text(tag_weights: Counter[str], category_weights: Counter[str]) -> str:
    tokens: list[str] = []
    for tag, weight in tag_weights.items():
        repeat = max(1, min(6, int(round(float(weight)))))
        tokens.extend([tag] * repeat)
    for category, weight in category_weights.items():
        repeat = max(1, min(5, int(round(float(weight)))))
        tokens.extend([category] * repeat)
    return " ".join(tokens)


def _compute_content_scores(
    candidate_articles: list[Article],
    history_article_texts: dict[int, str],
    history_article_weights: dict[int, float],
    tag_weights: Counter[str],
    category_weights: Counter[str],
) -> dict[int, float]:
    base_scores: dict[int, float] = {}
    for article in candidate_articles:
        score = 0.0
        for tag in _split_tags(article.tags):
            score += float(tag_weights.get(tag, 0))
        if article.category:
            score += float(category_weights.get(article.category, 0)) * 1.5
        base_scores[article.id] = score

    if not candidate_articles:
        return base_scores

    candidate_ids = [article.id for article in candidate_articles]
    candidate_texts = [_article_to_text(article) for article in candidate_articles]
    history_ids = [article_id for article_id, text in history_article_texts.items() if text.strip()]
    history_texts = [history_article_texts[article_id] for article_id in history_ids]
    profile_tag_text = _build_profile_tag_text(tag_weights, category_weights)

    if not history_texts and not profile_tag_text:
        return base_scores

    corpus = list(candidate_texts) + history_texts
    if profile_tag_text:
        corpus.append(profile_tag_text)

    try:
        vectorizer = _build_tfidf_vectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return base_scores

    candidate_matrix = tfidf_matrix[: len(candidate_ids)]
    profile_vector = None

    if history_ids:
        history_start = len(candidate_ids)
        history_end = history_start + len(history_ids)
        history_matrix = tfidf_matrix[history_start:history_end]
        weights = np.array(
            [max(float(history_article_weights.get(article_id, 1.0)), 0.1) for article_id in history_ids],
            dtype=float,
        )
        if float(weights.sum()) <= 0:
            weights = np.ones_like(weights)
        weights = weights / float(weights.sum())
        weighted_profile = history_matrix.multiply(weights[:, np.newaxis]).sum(axis=0)
        profile_vector = csr_matrix(weighted_profile)

    if profile_tag_text:
        tag_vector = tfidf_matrix[-1]
        profile_vector = tag_vector if profile_vector is None else profile_vector + tag_vector * 0.35

    if profile_vector is None:
        return base_scores

    similarities = cosine_similarity(candidate_matrix, profile_vector).ravel()
    for index, article_id in enumerate(candidate_ids):
        base_scores[article_id] += float(similarities[index]) * 10.0
    return base_scores


def _persist_recommendations(
    db: Session,
    user_id: int | None,
    items: Iterable[tuple[Article, str, float]],
) -> None:
    for article, recommend_type, score in items:
        db.add(
            Recommendation(
                user_id=user_id,
                article_id=article.id,
                recommend_type=recommend_type,
                recommend_score=float(score),
                is_clicked=False,
            )
        )
    db.commit()


def push_new_article_recommendations(
    db: Session,
    article: Article,
    limit: int = 200,
) -> int:
    """Push a newly published article to likely interested users."""

    article_tags = set(_split_tags(article.tags))
    if not article_tags and not article.category:
        return 0

    tag_user_scores: dict[int, float] = defaultdict(float)
    users = db.query(User).filter(User.id != article.author_id).all()
    for user in users:
        preference_tags = set(_split_tags(user.preference_tags))
        overlap = len(article_tags & preference_tags)
        if overlap > 0:
            tag_user_scores[user.id] += float(overlap) * 2.0

    if article_tags:
        behavior_rows = (
            db.query(UserBehavior.user_id, func.count(UserBehavior.id).label("cnt"))
            .join(Article, Article.id == UserBehavior.article_id)
            .filter(
                UserBehavior.user_id.isnot(None),
                UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
                Article.is_deleted == False,
            )
            .group_by(UserBehavior.user_id)
            .all()
        )
        for row in behavior_rows:
            if row.user_id and row.user_id != article.author_id:
                tag_user_scores[int(row.user_id)] += min(float(row.cnt or 0), 5.0) * 0.1

    if article.category:
        category_rows = (
            db.query(UserBehavior.user_id, func.count(UserBehavior.id).label("cnt"))
            .join(Article, Article.id == UserBehavior.article_id)
            .filter(
                UserBehavior.user_id.isnot(None),
                UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
                Article.category == article.category,
                Article.is_deleted == False,
            )
            .group_by(UserBehavior.user_id)
            .all()
        )
        for row in category_rows:
            if row.user_id and row.user_id != article.author_id:
                tag_user_scores[int(row.user_id)] += float(row.cnt or 0) * 0.3

    if not tag_user_scores:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=7)
    candidate_user_ids = [
        user_id
        for user_id, _ in sorted(tag_user_scores.items(), key=lambda item: item[1], reverse=True)[
            :limit
        ]
    ]
    existing_rows = (
        db.query(Recommendation.user_id)
        .filter(
            Recommendation.user_id.in_(candidate_user_ids),
            Recommendation.article_id == article.id,
            Recommendation.create_time >= cutoff,
        )
        .all()
    )
    existing_user_ids = {int(row.user_id) for row in existing_rows if row.user_id is not None}

    created = 0
    for user_id in candidate_user_ids:
        if user_id in existing_user_ids:
            continue
        score = tag_user_scores.get(user_id, 0.0)
        db.add(
            Recommendation(
                user_id=user_id,
                article_id=article.id,
                recommend_type="new_article_cold_start",
                recommend_score=float(score),
                is_clicked=False,
            )
        )
        created += 1
    db.commit()
    return created


@router.get("/recommend/list")
def recommend_list(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    articles = (
        db.query(Article)
        .filter(Article.is_deleted == False, Article.status == "published")
        .all()
    )
    if not articles:
        return success_response({"list": [], "total": 0, "page": page, "page_size": page_size})

    interacted_article_ids: set[int] = set()
    tag_weights: Counter[str] = Counter()
    category_weights: Counter[str] = Counter()
    history_article_weights: dict[int, float] = defaultdict(float)
    history_article_texts: dict[int, str] = {}
    collaborative_scores: dict[int, float] = {}

    if current_user:
        (
            interacted_article_ids,
            tag_weights,
            category_weights,
            history_article_weights,
            history_article_texts,
        ) = _fetch_user_history(db, current_user)
        collaborative_scores = _build_collaborative_scores(db, current_user, interacted_article_ids)

    candidate_articles = [article for article in articles if article.id not in interacted_article_ids] or articles
    hot_score_map = {article.id: _hot_score(article) for article in candidate_articles}
    content_score_map = _compute_content_scores(
        candidate_articles,
        history_article_texts,
        history_article_weights,
        tag_weights,
        category_weights,
    )
    collaborative_score_map = {
        article.id: float(collaborative_scores.get(article.id, 0.0)) for article in candidate_articles
    }

    max_hot = max(hot_score_map.values(), default=0.0)
    max_content = max(content_score_map.values(), default=0.0)
    max_collab = max(collaborative_score_map.values(), default=0.0)

    scored_items: list[tuple[Article, str, float]] = []
    for article in candidate_articles:
        hot_component = _normalize(hot_score_map[article.id], max_hot)
        content_component = _normalize(content_score_map[article.id], max_content)
        collab_component = _normalize(collaborative_score_map[article.id], max_collab)

        if content_component > 0 and collab_component > 0:
            recommend_type = "hybrid"
            final_score = hot_component * 0.15 + content_component * 0.5 + collab_component * 0.35
        elif collab_component > 0:
            recommend_type = "collaborative_filtering"
            final_score = hot_component * 0.2 + collab_component * 0.8
        elif content_component > 0:
            recommend_type = "content_semantic"
            final_score = hot_component * 0.2 + content_component * 0.8
        else:
            recommend_type = "cold_start"
            final_score = hot_component

        scored_items.append((article, recommend_type, final_score))

    scored_items.sort(key=lambda item: (item[2], item[0].create_time), reverse=True)
    total = len(scored_items)
    paged_items = scored_items[(page - 1) * page_size : page * page_size]

    _persist_recommendations(db, current_user.id if current_user else None, paged_items)

    return success_response(
        {
            "list": [
                _build_recommend_item(article, recommend_type, score)
                for article, recommend_type, score in paged_items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/recommend/similar")
def recommend_similar(
    article_id: int,
    size: int = 5,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    target = db.query(Article).filter(Article.id == article_id, Article.is_deleted == False).first()
    if not target:
        raise HTTPException(status_code=404, detail="文章不存在")

    target_tags = set(_split_tags(target.tags))
    candidates = (
        db.query(Article)
        .filter(
            Article.is_deleted == False,
            Article.status == "published",
            Article.id != article_id,
        )
        .all()
    )
    if not candidates:
        return success_response({"list": [], "total": 0, "page": 1, "page_size": size})

    target_text = _article_to_text(target)
    candidate_texts = [_article_to_text(article) for article in candidates]
    semantic_score_map = {article.id: 0.0 for article in candidates}
    try:
        vectorizer = _build_tfidf_vectorizer()
        tfidf_matrix = vectorizer.fit_transform([target_text] + candidate_texts)
        target_vector = tfidf_matrix[0]
        candidate_matrix = tfidf_matrix[1:]
        semantic_values = cosine_similarity(candidate_matrix, target_vector).ravel()
        for index, article in enumerate(candidates):
            semantic_score_map[article.id] = float(semantic_values[index])
    except ValueError:
        pass

    hot_score_map = {article.id: _hot_score(article) for article in candidates}
    max_hot = max(hot_score_map.values(), default=0.0)
    scored_items: list[tuple[Article, str, float]] = []

    for article in candidates:
        article_tags = set(_split_tags(article.tags))
        tag_jaccard = (
            float(len(target_tags & article_tags)) / float(len(target_tags | article_tags))
            if (target_tags or article_tags)
            else 0.0
        )
        category_bonus = 1.0 if target.category and article.category == target.category else 0.0
        semantic_similarity = semantic_score_map.get(article.id, 0.0)
        hot_component = _normalize(hot_score_map[article.id], max_hot)
        score = semantic_similarity * 0.65 + tag_jaccard * 0.2 + category_bonus * 0.1 + hot_component * 0.05
        scored_items.append((article, "content_semantic", score))

    scored_items.sort(key=lambda item: (item[2], item[0].create_time), reverse=True)
    paged_items = scored_items[:size]

    _persist_recommendations(db, current_user.id if current_user else None, paged_items)

    return success_response(
        {
            "list": [
                _build_recommend_item(article, recommend_type, score)
                for article, recommend_type, score in paged_items
            ],
            "total": len(paged_items),
            "page": 1,
            "page_size": size,
        }
    )
