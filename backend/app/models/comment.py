"""
models/comment.py —— 评论数据模型

对应数据库表：comment

支持两级评论结构：
  - 顶级评论：parent_id 为 None
  - 回复评论：parent_id 指向被回复的顶级评论 ID

注意：本系统只支持两级嵌套（评论 + 回复），不支持无限层级。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.app.db.base import Base


class Comment(Base):
    """评论 ORM 模型，映射到数据库 comment 表。

    Attributes:
        id (int): 主键，自增。
        article_id (int): 所属文章 ID，关联 article 表。
        user_id (int): 评论者用户 ID，关联 user 表。
        parent_id (int | None): 父评论 ID，顶级评论为 None，回复评论指向父评论。
        content (str): 评论正文内容。
        create_time (datetime): 评论创建时间（UTC）。
    """

    __tablename__ = "comment"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 所属文章 ID，建立索引加速"某文章的所有评论"查询
    article_id = Column(Integer, nullable=False, index=True)

    # 评论者用户 ID，建立索引加速"某用户的所有评论"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 父评论 ID：
    #   - None：顶级评论（直接评论文章）
    #   - 非 None：回复某条顶级评论
    parent_id = Column(Integer, nullable=True, index=True)

    # 评论正文，使用 Text 类型支持较长内容
    content = Column(Text, nullable=False)

    # 评论创建时间，建立索引加速时间排序查询
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
