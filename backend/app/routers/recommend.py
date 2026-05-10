"""
routers/recommend.py —— 推荐系统路由模块

实现基于内容的协同过滤混合推荐算法，提供以下接口：
  - GET /recommend/list   : 个性化推荐文章列表（首页信息流）
  - GET /recommend/similar: 相似文章推荐（文章详情页侧边栏）

推荐算法架构（三路混合）：
  1. 内容语义推荐（content_semantic）：
     - 使用 TF-IDF + 余弦相似度计算文章与用户历史阅读内容的相似度
     - 使用 jieba 分词 + 中文停用词过滤
     - 用户画像向量 = 历史文章 TF-IDF 向量的加权平均（权重=行为分数）
  2. 协同过滤推荐（collaborative_filtering）：
     - 找到与当前用户行为重叠最多的相似用户（Top-50）
     - 推荐相似用户喜欢但当前用户未读的文章
  3. 热度推荐（cold_start）：
     - 对新用户或无历史数据时，按热度分数排序推荐
     - 热度分数 = 阅读量 + 点赞量×3 + 收藏量×5 + 评论量×4

最终得分融合权重：
  - hybrid（内容+协同）: 热度×0.15 + 内容×0.50 + 协同×0.35
  - collaborative_filtering: 热度×0.20 + 协同×0.80
  - content_semantic: 热度×0.20 + 内容×0.80
  - cold_start: 热度×1.00

行为分数映射（用于加权用户画像）：
  - read（阅读）: 按阅读时长分级，1.0~5.0 分
  - like（点赞）: 4.0 分
  - collect（收藏）: 5.0 分
  - comment（评论）: 5.0 分
"""

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

# ── 常量定义 ──────────────────────────────────────────────────────────────────

# 参与推荐计算的行为类型（搜索/页面浏览不参与）
INTERACTION_TYPES = {"read", "like", "collect", "comment"}

# 显式行为的偏好分数（越高表示用户越感兴趣）
EXPLICIT_BEHAVIOR_SCORES = {
    "like": 4.0,      # 点赞：明确表示喜欢
    "collect": 5.0,   # 收藏：最强的喜欢信号
    "comment": 5.0,   # 评论：深度参与
}

# 中文停用词文件路径（与本文件同级的 resources 目录）
STOPWORDS_FILE = Path(__file__).resolve().parent.parent / "resources" / "stopwords_zh.txt"

# 内置停用词（文件不存在时的兜底）
DEFAULT_STOPWORDS = {
    "的", "了", "和", "是", "在", "就", "都", "而", "及", "与", "着", "或",
    "一个", "没有", "我们", "你", "我", "他", "她", "它",
    "this", "that", "with", "for", "from", "into", "onto",
    "are", "was", "were", "be", "been",
    "a", "an", "the", "and", "or", "to", "of", "in", "on", "is", "by", "as",
}


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _resolve_author_name(user: User | None) -> str | None:
    """获取用户展示名称（优先用户名，其次邮箱，最后手机号）。"""
    if not user:
        return None
    return user.username or user.email or user.phone


def _split_tags(tags: str | None) -> list[str]:
    """将逗号分隔的标签字符串拆分为列表，过滤空标签。"""
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def _hot_score(article: Article) -> float:
    """计算文章热度分数。

    热度公式：阅读量×1 + 点赞量×3 + 收藏量×5 + 评论量×4
    权重设计：收藏/评论 > 点赞 > 阅读（越主动的行为权重越高）
    """
    return (
        float(article.view_count)
        + float(article.like_count) * 3.0
        + float(article.collect_count) * 5.0
        + float(article.comment_count) * 4.0
    )


def _normalize(value: float, max_value: float) -> float:
    """将值归一化到 [0, 1] 区间（Min-Max 归一化，min=0）。

    Args:
        value: 待归一化的值。
        max_value: 最大值，为 0 时返回 0.0（避免除零）。
    """
    if max_value <= 0:
        return 0.0
    return float(value) / float(max_value)


def _build_recommend_item(article: Article, recommend_type: str, score: float) -> dict:
    """将文章 ORM 对象转换为推荐列表项字典。

    Args:
        article: 文章 ORM 实例。
        recommend_type: 推荐类型标识（hybrid/content_semantic/collaborative_filtering/cold_start）。
        score: 最终推荐分数（已归一化）。
    """
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
        "recommend_type": recommend_type,       # 推荐来源类型（用于分析）
        "recommend_score": round(score, 4),     # 推荐分数（保留 4 位小数）
    }


def _clean_text(text: str) -> str:
    """清洗文本：去除 HTML 标签、Markdown 符号、多余空格，转小写。

    Args:
        text: 原始文本（可能包含 HTML/Markdown）。

    Returns:
        清洗后的纯文本字符串。
    """
    cleaned = re.sub(r"<[^>]+>", " ", text or "")  # 去除 HTML 标签
    cleaned = re.sub(r"[_*#>`~\-\[\]\(\)!\"'""''·,，.。:：;；/\\|]", " ", cleaned)  # 去除 Markdown 符号
    cleaned = re.sub(r"\s+", " ", cleaned)  # 合并多余空格
    return cleaned.strip().lower()


@lru_cache(maxsize=1)
def _load_stopwords() -> set[str]:
    """加载中文停用词表（使用 lru_cache 缓存，只加载一次）。

    优先从文件加载，文件不存在时使用内置停用词。

    Returns:
        停用词集合。
    """
    words = set(DEFAULT_STOPWORDS)
    if STOPWORDS_FILE.exists():
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token:
                words.add(token)
    return words


def _tokenize_with_jieba(text: str) -> list[str]:
    """使用 jieba 对文本进行中文分词，并过滤停用词和无效 token。

    过滤规则：
      - 停用词过滤
      - 只保留中文字符、英文字母、数字（过滤标点符号等）
      - 纯英文/数字 token 长度必须 > 1（过滤单字母/单数字）

    Args:
        text: 待分词的文本。

    Returns:
        有效 token 列表。
    """
    stopwords = _load_stopwords()
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    tokens: list[str] = []
    for token in jieba.lcut(cleaned, cut_all=False):  # 精确模式分词
        value = token.strip().lower()
        if not value or value in stopwords:
            continue
        # 只保留中文、英文、数字组成的 token
        if not re.fullmatch(r"[a-z0-9\u4e00-\u9fff]+", value):
            continue
        # 纯英文/数字 token 长度必须 > 1
        if re.fullmatch(r"[a-z0-9]+", value) and len(value) <= 1:
            continue
        tokens.append(value)
    return tokens


def _build_tfidf_vectorizer() -> TfidfVectorizer:
    """构建 TF-IDF 向量化器（使用 jieba 分词）。

    配置说明：
      - tokenizer: 使用 jieba 分词（支持中文）
      - max_features: 最多保留 12000 个特征词
      - ngram_range: (1, 2) 同时考虑单词和双词组合
    """
    return TfidfVectorizer(
        tokenizer=_tokenize_with_jieba,
        token_pattern=None,             # 禁用默认正则分词（使用自定义 tokenizer）
        preprocessor=lambda value: value,  # 不做额外预处理
        lowercase=False,                # 已在 tokenizer 中处理大小写
        max_features=12000,             # 词汇表大小上限
        ngram_range=(1, 2),             # 单词 + 双词组合
    )


def _article_to_text(article: Article) -> str:
    """将文章各字段拼接为用于 TF-IDF 的文本字符串。

    拼接顺序：标题 > 摘要 > 正文 > 分类 > 标签
    （标题和摘要在前，权重更高）
    """
    parts = [
        article.title or "",
        article.summary or "",
        article.content or "",
        article.category or "",
        article.tags or "",
    ]
    return " ".join(parts)


def _read_duration_to_score(read_duration: int | None) -> float:
    """将阅读时长（秒）转换为偏好分数（1.0~5.0）。

    分级规则：
      - 0~29 秒：1.0（快速浏览，兴趣较低）
      - 30~89 秒：2.0（简单阅读）
      - 90~179 秒：3.0（正常阅读）
      - 180~299 秒：4.0（深度阅读）
      - 300 秒以上：5.0（非常感兴趣）
    """
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
    """根据行为类型和阅读时长计算偏好分数。

    - read 行为：根据阅读时长分级（1.0~5.0）
    - 其他行为：使用 EXPLICIT_BEHAVIOR_SCORES 中的固定分数
    """
    behavior_type = str(behavior.behavior_type or "").lower()
    if behavior_type == "read":
        return _read_duration_to_score(behavior.read_duration)
    return EXPLICIT_BEHAVIOR_SCORES.get(behavior_type, 1.0)


def _fetch_user_history(
    db: Session, current_user: User
) -> tuple[set[int], Counter[str], Counter[str], dict[int, float], dict[int, str]]:
    """获取用户历史行为数据，构建用户兴趣画像。

    返回值说明：
      - interacted_article_ids: 用户已交互的文章 ID 集合（用于过滤已读文章）
      - tag_weights: 标签权重 Counter（标签 → 权重分数）
      - category_weights: 分类权重 Counter（分类 → 权重分数）
      - history_article_weights: 历史文章权重字典（文章 ID → 累计行为分数）
      - history_article_texts: 历史文章文本字典（文章 ID → 拼接文本）

    权重来源：
      1. 用户偏好标签（preference_tags）：每个标签 +3.0
      2. 历史行为文章的标签：每个标签 += 行为分数 × 0.6
      3. 历史行为文章的分类：分类 += 行为分数 × 0.5
    """
    interacted_article_ids: set[int] = set()
    tag_weights: Counter[str] = Counter()
    category_weights: Counter[str] = Counter()
    history_article_weights: dict[int, float] = defaultdict(float)
    history_article_texts: dict[int, str] = {}

    # 从用户偏好标签初始化标签权重（每个偏好标签 +3.0）
    if current_user.preference_tags:
        for tag in _split_tags(current_user.preference_tags):
            tag_weights[tag] += 3.0

    # 查询最近 1000 条交互行为（按时间降序，避免全表扫描）
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

    # 统计每篇文章的累计行为分数
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

    # 批量查询历史文章，提取标签和分类权重
    articles = (
        db.query(Article)
        .filter(Article.id.in_(interacted_article_ids), Article.is_deleted == False)
        .all()
    )
    for article in articles:
        score_factor = max(1.0, float(history_article_weights.get(article.id, 1.0)))
        for tag in _split_tags(article.tags):
            tag_weights[tag] += score_factor * 0.6      # 标签权重
        if article.category:
            category_weights[article.category] += score_factor * 0.5  # 分类权重
        history_article_texts[article.id] = _article_to_text(article)  # 保存文章文本

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
    """构建协同过滤推荐分数。

    算法步骤：
      1. 找到与当前用户行为重叠最多的 Top-50 相似用户
      2. 查询相似用户的所有交互文章
      3. 对当前用户未读的文章，累加 相似用户权重 × 行为分数

    Args:
        db: 数据库会话。
        current_user: 当前用户。
        interacted_article_ids: 当前用户已交互的文章 ID 集合（用于过滤）。

    Returns:
        dict[int, float]: 文章 ID → 协同过滤分数的字典。
    """
    if not interacted_article_ids:
        return {}

    # 找到与当前用户行为重叠最多的相似用户（按重叠文章数降序，取 Top-50）
    similar_user_rows = (
        db.query(
            UserBehavior.user_id.label("user_id"),
            func.count(UserBehavior.id).label("overlap"),  # 重叠行为数
        )
        .filter(
            UserBehavior.user_id.isnot(None),
            UserBehavior.user_id != current_user.id,       # 排除自己
            UserBehavior.article_id.in_(interacted_article_ids),  # 与当前用户有共同文章
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
        )
        .group_by(UserBehavior.user_id)
        .order_by(desc("overlap"))
        .limit(50)  # 只取最相似的 50 个用户
        .all()
    )
    if not similar_user_rows:
        return {}

    # 相似用户权重 = 重叠行为数（重叠越多，相似度越高）
    similar_user_weight = {int(row.user_id): float(row.overlap or 0) for row in similar_user_rows}

    # 查询相似用户的所有交互行为
    candidate_behaviors = (
        db.query(UserBehavior)
        .filter(
            UserBehavior.user_id.in_(similar_user_weight.keys()),
            UserBehavior.article_id.isnot(None),
            UserBehavior.behavior_type.in_(tuple(INTERACTION_TYPES)),
        )
        .all()
    )

    # 计算协同过滤分数：相似用户权重 × 行为分数
    collaborative_scores: dict[int, float] = defaultdict(float)
    for behavior in candidate_behaviors:
        if behavior.article_id is None or behavior.user_id is None:
            continue
        article_id = int(behavior.article_id)
        if article_id in interacted_article_ids:
            continue  # 跳过当前用户已读的文章
        user_weight = similar_user_weight.get(int(behavior.user_id), 0.0)
        behavior_weight = _behavior_preference_score(behavior)
        collaborative_scores[article_id] += user_weight * behavior_weight

    return collaborative_scores


def _build_profile_tag_text(tag_weights: Counter[str], category_weights: Counter[str]) -> str:
    """将用户兴趣标签和分类权重转换为 TF-IDF 输入文本。

    通过重复 token 来模拟权重（权重越高，重复次数越多）：
      - 标签：重复 1~6 次
      - 分类：重复 1~5 次

    Args:
        tag_weights: 标签权重 Counter。
        category_weights: 分类权重 Counter。

    Returns:
        用于 TF-IDF 的用户画像文本字符串。
    """
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
    """计算候选文章的内容语义推荐分数。

    算法步骤：
      1. 基础分：候选文章标签/分类与用户兴趣的直接匹配分
      2. TF-IDF 语义分：
         a. 构建语料库（候选文章 + 历史文章 + 用户画像文本）
         b. 计算 TF-IDF 矩阵
         c. 构建用户画像向量（历史文章向量的加权平均 + 标签向量×0.35）
         d. 计算候选文章与用户画像向量的余弦相似度
         e. 相似度 × 10.0 加到基础分上

    Args:
        candidate_articles: 候选文章列表。
        history_article_texts: 历史文章文本字典。
        history_article_weights: 历史文章权重字典。
        tag_weights: 标签权重 Counter。
        category_weights: 分类权重 Counter。

    Returns:
        dict[int, float]: 文章 ID → 内容语义分数的字典。
    """
    # 第一步：计算基础分（标签/分类直接匹配）
    base_scores: dict[int, float] = {}
    for article in candidate_articles:
        score = 0.0
        for tag in _split_tags(article.tags):
            score += float(tag_weights.get(tag, 0))
        if article.category:
            score += float(category_weights.get(article.category, 0)) * 1.5  # 分类权重×1.5
        base_scores[article.id] = score

    if not candidate_articles:
        return base_scores

    # 第二步：TF-IDF 语义相似度计算
    candidate_ids = [article.id for article in candidate_articles]
    candidate_texts = [_article_to_text(article) for article in candidate_articles]
    history_ids = [article_id for article_id, text in history_article_texts.items() if text.strip()]
    history_texts = [history_article_texts[article_id] for article_id in history_ids]
    profile_tag_text = _build_profile_tag_text(tag_weights, category_weights)

    if not history_texts and not profile_tag_text:
        return base_scores  # 无历史数据，只返回基础分

    # 构建语料库：候选文章 + 历史文章 + 用户画像文本
    corpus = list(candidate_texts) + history_texts
    if profile_tag_text:
        corpus.append(profile_tag_text)

    try:
        vectorizer = _build_tfidf_vectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return base_scores  # 分词失败时降级为基础分

    candidate_matrix = tfidf_matrix[: len(candidate_ids)]
    profile_vector = None

    # 构建用户画像向量（历史文章向量的加权平均）
    if history_ids:
        history_start = len(candidate_ids)
        history_end = history_start + len(history_ids)
        history_matrix = tfidf_matrix[history_start:history_end]
        # 权重归一化
        weights = np.array(
            [max(float(history_article_weights.get(article_id, 1.0)), 0.1) for article_id in history_ids],
            dtype=float,
        )
        if float(weights.sum()) <= 0:
            weights = np.ones_like(weights)
        weights = weights / float(weights.sum())
        # 加权平均：用户画像向量 = Σ(历史文章向量 × 权重)
        weighted_profile = history_matrix.multiply(weights[:, np.newaxis]).sum(axis=0)
        profile_vector = csr_matrix(weighted_profile)

    # 融合标签画像向量（权重 0.35）
    if profile_tag_text:
        tag_vector = tfidf_matrix[-1]
        profile_vector = tag_vector if profile_vector is None else profile_vector + tag_vector * 0.35

    if profile_vector is None:
        return base_scores

    # 计算余弦相似度，加到基础分上
    similarities = cosine_similarity(candidate_matrix, profile_vector).ravel()
    for index, article_id in enumerate(candidate_ids):
        base_scores[article_id] += float(similarities[index]) * 10.0  # 相似度放大 10 倍

    return base_scores


def _persist_recommendations(
    db: Session,
    user_id: int | None,
    items: Iterable[tuple[Article, str, float]],
) -> None:
    """将推荐结果持久化到 recommendation 表（用于 CTR 统计和推荐效果分析）。

    Args:
        db: 数据库会话。
        user_id: 用户 ID，匿名用户为 None。
        items: 推荐结果迭代器，每项为 (文章, 推荐类型, 分数) 元组。
    """
    for article, recommend_type, score in items:
        db.add(
            Recommendation(
                user_id=user_id,
                article_id=article.id,
                recommend_type=recommend_type,      # 推荐来源类型
                recommend_score=float(score),       # 推荐分数
                is_clicked=False,                   # 初始未点击
            )
        )
    db.commit()


def push_new_article_recommendations(
    db: Session,
    article: Article,
    limit: int = 200,
) -> int:
    """新文章发布时，主动推送给可能感兴趣的用户（冷启动推送）。

    推送策略：
      1. 偏好标签匹配：用户偏好标签与文章标签有重叠，每个重叠标签 +2.0 分
      2. 历史行为匹配：有过相关文章交互行为的用户，按行为次数加分
      3. 分类匹配：有过同分类文章阅读行为的用户，按行为次数加分
      4. 按总分降序，取 Top-limit 用户推送

    Args:
        db: 数据库会话。
        article: 新发布的文章。
        limit: 最多推送给多少用户，默认 200。

    Returns:
        int: 实际创建的推荐记录数。
    """
    article_tags = set(_split_tags(article.tags))
    if not article_tags and not article.category:
        return 0  # 无标签无分类，无法匹配，跳过推送

    tag_user_scores: dict[int, float] = defaultdict(float)

    # 策略1：偏好标签匹配（用户偏好标签与文章标签重叠）
    users = db.query(User).filter(User.id != article.author_id).all()
    for user in users:
        preference_tags = set(_split_tags(user.preference_tags))
        overlap = len(article_tags & preference_tags)
        if overlap > 0:
            tag_user_scores[user.id] += float(overlap) * 2.0

    # 策略2：历史行为匹配（有过相关文章交互的用户）
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

    # 策略3：分类匹配（有过同分类文章阅读行为的用户）
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

    # 取 Top-limit 用户，过滤 7 天内已推送过的用户（避免重复推送）
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

    # 创建推荐记录
    created = 0
    for user_id in candidate_user_ids:
        if user_id in existing_user_ids:
            continue  # 跳过已推送的用户
        score = tag_user_scores.get(user_id, 0.0)
        db.add(
            Recommendation(
                user_id=user_id,
                article_id=article.id,
                recommend_type="new_article_cold_start",  # 新文章冷启动推送
                recommend_score=float(score),
                is_clicked=False,
            )
        )
        created += 1
    db.commit()
    return created


# ── 路由处理函数 ──────────────────────────────────────────────────────────────

@router.get("/recommend/list")
def recommend_list(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """获取个性化推荐文章列表（首页信息流）。

    算法流程：
      1. 获取所有已发布文章
      2. 若已登录：获取用户历史行为，构建兴趣画像
      3. 过滤已读文章（候选集 = 全部文章 - 已读文章）
      4. 计算三路分数：热度分、内容语义分、协同过滤分
      5. 归一化各路分数到 [0, 1]
      6. 按推荐类型融合权重，计算最终分数
      7. 按最终分数降序排列，分页返回
      8. 将本次推荐结果持久化（用于 CTR 统计）

    Args:
        page: 页码，从 1 开始。
        page_size: 每页数量，默认 10。
        db: 数据库会话。
        current_user: 当前用户，未登录时为 None（降级为热度推荐）。
    """
    # 获取所有已发布且未删除的文章
    articles = (
        db.query(Article)
        .filter(Article.is_deleted == False, Article.status == "published")
        .all()
    )
    if not articles:
        return success_response({"list": [], "total": 0, "page": page, "page_size": page_size})

    # 初始化各路分数容器
    interacted_article_ids: set[int] = set()
    tag_weights: Counter[str] = Counter()
    category_weights: Counter[str] = Counter()
    history_article_weights: dict[int, float] = defaultdict(float)
    history_article_texts: dict[int, str] = {}
    collaborative_scores: dict[int, float] = {}

    # 已登录用户：获取历史行为和协同过滤分数
    if current_user:
        (
            interacted_article_ids,
            tag_weights,
            category_weights,
            history_article_weights,
            history_article_texts,
        ) = _fetch_user_history(db, current_user)
        collaborative_scores = _build_collaborative_scores(db, current_user, interacted_article_ids)

    # 候选集：过滤已读文章（若全部已读则不过滤，避免空列表）
    candidate_articles = [article for article in articles if article.id not in interacted_article_ids] or articles

    # 计算各路分数
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

    # 归一化各路分数（Min-Max，min=0）
    max_hot = max(hot_score_map.values(), default=0.0)
    max_content = max(content_score_map.values(), default=0.0)
    max_collab = max(collaborative_score_map.values(), default=0.0)

    # 融合分数，确定推荐类型
    scored_items: list[tuple[Article, str, float]] = []
    for article in candidate_articles:
        hot_component = _normalize(hot_score_map[article.id], max_hot)
        content_component = _normalize(content_score_map[article.id], max_content)
        collab_component = _normalize(collaborative_score_map[article.id], max_collab)

        if content_component > 0 and collab_component > 0:
            # 混合推荐：内容 + 协同 + 热度
            recommend_type = "hybrid"
            final_score = hot_component * 0.15 + content_component * 0.5 + collab_component * 0.35
        elif collab_component > 0:
            # 纯协同过滤推荐
            recommend_type = "collaborative_filtering"
            final_score = hot_component * 0.2 + collab_component * 0.8
        elif content_component > 0:
            # 纯内容语义推荐
            recommend_type = "content_semantic"
            final_score = hot_component * 0.2 + content_component * 0.8
        else:
            # 冷启动：纯热度推荐（新用户或无历史数据）
            recommend_type = "cold_start"
            final_score = hot_component

        scored_items.append((article, recommend_type, final_score))

    # 按最终分数降序排列（分数相同时按创建时间降序）
    scored_items.sort(key=lambda item: (item[2], item[0].create_time), reverse=True)
    total = len(scored_items)
    paged_items = scored_items[(page - 1) * page_size : page * page_size]

    # 持久化推荐记录（用于 CTR 统计和推荐效果分析）
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
    """获取与指定文章相似的文章列表（文章详情页侧边栏）。

    相似度计算方式（加权融合）：
      - TF-IDF 余弦相似度（权重 0.65）：语义内容相似
      - 标签 Jaccard 相似度（权重 0.20）：标签重叠程度
      - 同分类加成（权重 0.10）：同分类文章额外加分
      - 热度分（权重 0.05）：热门文章轻微加分

    Args:
        article_id: 目标文章 ID。
        size: 返回相似文章数量，默认 5。
        db: 数据库会话。
        current_user: 当前用户（用于记录推荐日志）。

    Returns:
        成功响应，data 包含相似文章列表。
    """
    # 获取目标文章
    target = db.query(Article).filter(Article.id == article_id, Article.is_deleted == False).first()
    if not target:
        raise HTTPException(status_code=404, detail="文章不存在")

    target_tags = set(_split_tags(target.tags))

    # 候选文章：排除目标文章本身，只取已发布文章
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

    # 计算 TF-IDF 语义相似度
    target_text = _article_to_text(target)
    candidate_texts = [_article_to_text(article) for article in candidates]
    semantic_score_map = {article.id: 0.0 for article in candidates}
    try:
        vectorizer = _build_tfidf_vectorizer()
        # 语料库：目标文章 + 所有候选文章
        tfidf_matrix = vectorizer.fit_transform([target_text] + candidate_texts)
        target_vector = tfidf_matrix[0]         # 目标文章向量
        candidate_matrix = tfidf_matrix[1:]     # 候选文章矩阵
        # 计算每篇候选文章与目标文章的余弦相似度
        semantic_values = cosine_similarity(candidate_matrix, target_vector).ravel()
        for index, article in enumerate(candidates):
            semantic_score_map[article.id] = float(semantic_values[index])
    except ValueError:
        pass  # 分词失败时语义分为 0，降级为标签/分类匹配

    hot_score_map = {article.id: _hot_score(article) for article in candidates}
    max_hot = max(hot_score_map.values(), default=0.0)
    scored_items: list[tuple[Article, str, float]] = []

    for article in candidates:
        article_tags = set(_split_tags(article.tags))
        # 标签 Jaccard 相似度 = |交集| / |并集|
        tag_jaccard = (
            float(len(target_tags & article_tags)) / float(len(target_tags | article_tags))
            if (target_tags or article_tags)
            else 0.0
        )
        # 同分类加成
        category_bonus = 1.0 if target.category and article.category == target.category else 0.0
        semantic_similarity = semantic_score_map.get(article.id, 0.0)
        hot_component = _normalize(hot_score_map[article.id], max_hot)
        # 加权融合最终分数
        score = semantic_similarity * 0.65 + tag_jaccard * 0.2 + category_bonus * 0.1 + hot_component * 0.05
        scored_items.append((article, "content_semantic", score))

    # 按分数降序排列，取 Top-size
    scored_items.sort(key=lambda item: (item[2], item[0].create_time), reverse=True)
    paged_items = scored_items[:size]

    # 持久化推荐记录
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
