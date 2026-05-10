"""
models/recommendation.py —— 推荐记录数据模型

对应数据库表：recommendation

记录系统向用户推荐文章的每一次曝光事件，用于：
  1. 推荐效果分析（点击率 CTR、转化率）
  2. 避免重复推荐同一篇文章

推荐类型（recommend_type）枚举：
  - "collaborative" : 协同过滤推荐（基于相似用户行为）
  - "content"       : 内容相似推荐（基于文章标签/分类）
  - "hot"           : 热门推荐（基于热度分数）
  - "new"           : 最新文章推荐
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from backend.app.db.base import Base


class Recommendation(Base):
    """推荐记录 ORM 模型，映射到数据库 recommendation 表。

    Attributes:
        id (int): 主键，自增。
        user_id (int): 被推荐的用户 ID，关联 user 表。
        article_id (int): 被推荐的文章 ID，关联 article 表。
        recommend_type (str): 推荐算法类型，见模块文档枚举。
        score (float | None): 推荐分数，分数越高表示越相关。
        is_clicked (bool): 用户是否点击了该推荐，默认 False。
        create_time (datetime): 推荐曝光时间（UTC）。
    """

    __tablename__ = "recommendation"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 被推荐用户 ID，建立索引加速"某用户的推荐记录"查询
    user_id = Column(Integer, nullable=False, index=True)

    # 被推荐文章 ID
    article_id = Column(Integer, nullable=True, index=True)

    # 推荐算法类型：collaborative / content / hot / new
    recommend_type = Column(String(32), nullable=True)

    # 推荐分数，由推荐算法计算，用于排序和效果分析
    score = Column(Float, nullable=True)

    # 用户是否点击了该推荐项，初始为 False，用户点击后更新为 True
    is_clicked = Column(Boolean, nullable=False, default=False)

    # 推荐曝光时间，建立索引加速时间范围查询
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
