"""
models/article_collect.py —— 文章收藏数据模型

对应数据库表：article_collect

记录用户对文章的收藏关系（多对多关联表）。
每条记录表示"某用户收藏了某篇文章"，通过 (user_id, article_id) 联合唯一约束
防止重复收藏。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, UniqueConstraint

from backend.app.db.base import Base


class ArticleCollect(Base):
    """文章收藏 ORM 模型，映射到数据库 article_collect 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 收藏用户 ID，关联 user 表。
        article_id (int): 被收藏文章 ID，关联 article 表。
        create_time (datetime): 收藏时间（UTC）。
    """

    __tablename__ = "article_collect"

    # 联合唯一约束：同一用户对同一文章只能收藏一次
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_article_collect_user_article"),
    )

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 收藏用户 ID，建立索引加速"我的收藏"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 被收藏文章 ID，建立索引加速"某文章的收藏数"查询
    article_id = Column(Integer, nullable=False, index=True)

    # 收藏时间，用于按时间排序展示收藏列表
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
