"""
models/user_follow.py —— 用户关注关系数据模型

对应数据库表：user_follow

记录用户之间的关注关系（有向图）：
  - follower_id  : 关注者（"我"）
  - following_id : 被关注者（"TA"）

例如：A 关注了 B，则存储一条 (follower_id=A, following_id=B) 的记录。

查询场景：
  - "我关注的人"：WHERE follower_id = 我的 ID
  - "关注我的人"：WHERE following_id = 我的 ID
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, UniqueConstraint

from backend.app.db.base import Base


class UserFollow(Base):
    """用户关注关系 ORM 模型，映射到数据库 user_follow 表。

    Attributes:
        id (int): 主键，自增。
        follower_id (int): 关注者用户 ID（"我"），关联 user 表。
        following_id (int): 被关注者用户 ID（"TA"），关联 user 表。
        create_time (datetime): 关注时间（UTC）。
    """

    __tablename__ = "user_follow"

    # 联合唯一约束：同一用户对同一人只能关注一次
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follow"),
    )

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 关注者 ID（"我"），建立索引加速"我关注的人"查询
    follower_id = Column(Integer, nullable=False, index=True)

    # 被关注者 ID（"TA"），建立索引加速"关注我的人"查询
    following_id = Column(Integer, nullable=False, index=True)

    # 关注时间，用于按时间排序展示关注列表
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
