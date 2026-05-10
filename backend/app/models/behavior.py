"""
models/behavior.py —— 用户行为数据模型

对应数据库表：user_behavior

记录用户在平台上的所有行为事件，是数据分析和推荐算法的核心数据源。

行为类型（behavior_type）枚举：
  - "read"      : 阅读文章（携带 read_duration 和 scroll_depth）
  - "like"      : 点赞文章
  - "collect"   : 收藏文章
  - "comment"   : 评论文章
  - "search"    : 搜索（携带 keyword）
  - "page_view" : 页面浏览（携带 keyword=路径）
  - "page_leave": 离开页面（携带 keyword=路径）
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from backend.app.db.base import Base


class UserBehavior(Base):
    """用户行为 ORM 模型，映射到数据库 user_behavior 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 行为发生的用户 ID，关联 user 表。
        article_id (int | None): 相关文章 ID，搜索/页面浏览行为可为空。
        behavior_type (str): 行为类型，见模块文档枚举。
        read_duration (int | None): 阅读时长（秒），仅 read 行为有值。
        scroll_depth (float | None): 滚动深度（0.0~1.0），仅 read 行为有值。
        keyword (str | None): 搜索关键词或页面路径，仅 search/page_view 行为有值。
        create_time (datetime): 行为发生时间（UTC）。
    """

    __tablename__ = "user_behavior"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 用户 ID，建立索引加速"某用户的所有行为"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 相关文章 ID，搜索/页面浏览等行为可为空
    article_id = Column(Integer, nullable=True, index=True)

    # 行为类型：read / like / collect / comment / search / page_view / page_leave
    behavior_type = Column(String(32), nullable=False, index=True)

    # 阅读时长（秒），仅 read 行为记录，用于分析用户阅读深度
    read_duration = Column(Integer, nullable=True)

    # 滚动深度（0.0~1.0），1.0 表示读到文章底部，用于分析内容吸引力
    scroll_depth = Column(Float, nullable=True)

    # 搜索关键词（search 行为）或页面路径（page_view/page_leave 行为）
    keyword = Column(String(255), nullable=True)

    # 行为发生时间，建立索引加速时间范围查询
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
