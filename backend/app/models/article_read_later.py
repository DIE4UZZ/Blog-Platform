"""
models/article_read_later.py —— 稍后阅读数据模型

对应数据库表：article_read_later

记录用户标记为"稍后阅读"的文章（类似书签功能）。
通过 (user_id, article_id) 联合唯一约束防止重复添加。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, UniqueConstraint

from backend.app.db.base import Base


class ArticleReadLater(Base):
    """稍后阅读 ORM 模型，映射到数据库 article_read_later 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 用户 ID，关联 user 表。
        article_id (int): 文章 ID，关联 article 表。
        create_time (datetime): 添加时间（UTC）。
    """

    __tablename__ = "article_read_later"

    # 联合唯一约束：同一用户对同一文章只能添加一次稍后阅读
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_read_later_user_article"),
    )

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 用户 ID，建立索引加速"我的稍后阅读"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 文章 ID
    article_id = Column(Integer, nullable=False, index=True)

    # 添加时间，用于按时间排序展示稍后阅读列表
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
