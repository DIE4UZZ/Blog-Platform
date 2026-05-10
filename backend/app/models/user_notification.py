"""
models/user_notification.py —— 用户通知数据模型

对应数据库表：user_notification

记录系统向用户推送的各类通知消息。

通知类型（notification_type）枚举：
  - "new_follower" : 有新用户关注了我
  - "new_article"  : 我关注的人发布了新文章
  - "new_comment"  : 我的文章收到了新评论
  - "comment_reply": 我的评论收到了回复
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.app.db.base import Base


class UserNotification(Base):
    """用户通知 ORM 模型，映射到数据库 user_notification 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 通知接收者用户 ID，关联 user 表。
        actor_user_id (int | None): 触发通知的用户 ID（如关注者、评论者），可为空。
        article_id (int | None): 相关文章 ID，可为空（new_follower 通知无文章）。
        comment_id (int | None): 相关评论 ID，可为空。
        notification_type (str): 通知类型，见模块文档枚举。
        title (str): 通知标题，简短描述（如"你有新的关注者"）。
        content (str): 通知正文，详细内容（如评论/文章摘要）。
        is_read (bool): 是否已读，默认 False。
        create_time (datetime): 通知创建时间（UTC）。
    """

    __tablename__ = "user_notification"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 通知接收者 ID，建立索引加速"我的通知"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 触发通知的用户 ID（关注者、评论者等），可为空（系统通知无 actor）
    actor_user_id = Column(Integer, nullable=True)

    # 相关文章 ID，用于前端跳转到对应文章页
    article_id = Column(Integer, nullable=True)

    # 相关评论 ID，用于前端定位到具体评论
    comment_id = Column(Integer, nullable=True)

    # 通知类型：new_follower / new_article / new_comment / comment_reply
    notification_type = Column(String(32), nullable=False, index=True)

    # 通知标题，简短描述，直接展示在通知列表
    title = Column(String(255), nullable=False)

    # 通知正文，详细内容（如文章标题、评论内容摘要）
    content = Column(Text, nullable=True)

    # 是否已读：False（未读）/ True（已读），建立索引加速"未读通知数"查询
    is_read = Column(Boolean, nullable=False, default=False, index=True)

    # 通知创建时间，建立索引加速时间排序查询
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
