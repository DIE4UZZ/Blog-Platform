"""
models/article_like.py —— 文章点赞数据模型

对应数据库表：article_like

记录用户对文章的点赞关系（多对多关联表）。
每条记录表示"某用户点赞了某篇文章"，通过 (user_id, article_id) 联合唯一约束
防止重复点赞。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, UniqueConstraint

from backend.app.db.base import Base


class ArticleLike(Base):
    """文章点赞 ORM 模型，映射到数据库 article_like 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 点赞用户 ID，关联 user 表。
        article_id (int): 被点赞文章 ID，关联 article 表。
        create_time (datetime): 点赞时间（UTC）。
    """

    __tablename__ = "article_like"

    # 联合唯一约束：同一用户对同一文章只能点赞一次
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_article_like_user_article"),
    )

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 点赞用户 ID，建立索引加速"某用户点赞的所有文章"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 被点赞文章 ID，建立索引加速"某文章的点赞数"查询
    article_id = Column(Integer, nullable=False, index=True)

    # 点赞时间
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
