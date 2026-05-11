"""
models/article.py —— 文章数据模型

对应数据库表：article

字段说明：
  - id           : 主键，自增整数
  - author_id    : 作者用户 ID（外键关联 user.id）
  - title        : 文章标题
  - summary      : 文章摘要（可为空，用于列表页展示）
  - content      : 文章正文（Markdown 格式）
  - category     : 文章分类（如 "技术"、"生活"）
  - tags         : 标签，逗号分隔字符串（如 "Python,FastAPI"）
  - status       : 发布状态："draft"（草稿）/"published"（已发布）/"rejected"（已拒绝）
  - view_count   : 阅读次数（冗余字段，避免频繁 JOIN behavior 表）
  - like_count   : 点赞次数
  - collect_count: 收藏次数
  - comment_count: 评论次数
  - is_deleted   : 软删除标志，True 表示已删除（不物理删除）
  - create_time  : 创建时间（UTC）
  - update_time  : 最后更新时间（UTC）
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Article(Base):
    """文章 ORM 模型，映射到数据库 article 表。"""

    __tablename__ = "article"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 作者 ID，关联 user 表，建立索引加速"我的文章"查询
    author_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)

    # 关联作者用户对象（lazy 加载，访问时自动查询）
    author = relationship("User", foreign_keys=[author_id], lazy="select")

    # 文章标题，最长 255 字符
    title = Column(String(255), nullable=False)

    # 文章摘要，用于列表页展示，可为空（前端可截取正文前 N 字）
    summary = Column(String(512), nullable=True)

    # 文章正文，使用 Text 类型存储 Markdown 内容，无长度限制
    content = Column(Text, nullable=True)

    # 文章 HTML 内容（由 Markdown 转换而来，供前端直接渲染）
    html_content = Column(Text, nullable=True)

    # 文章分类，用于筛选和统计
    category = Column(String(64), nullable=True, index=True)

    # 标签，逗号分隔，例如 "Python,FastAPI,后端"
    tags = Column(String(512), nullable=True)

    # 发布状态：draft（草稿）/ published（已发布）/ rejected（已拒绝）
    # 建立索引加速按状态筛选
    status = Column(String(32), nullable=False, default="draft", index=True)

    # 阅读次数，每次用户阅读时 +1（冗余计数，避免实时聚合 behavior 表）
    view_count = Column(Integer, nullable=False, default=0)

    # 点赞次数，用户点赞/取消点赞时同步更新
    like_count = Column(Integer, nullable=False, default=0)

    # 收藏次数，用户收藏/取消收藏时同步更新
    collect_count = Column(Integer, nullable=False, default=0)

    # 评论次数，新增/删除评论时同步更新
    comment_count = Column(Integer, nullable=False, default=0)

    # 软删除标志：True 表示已删除，查询时过滤 is_deleted == False
    is_deleted = Column(Boolean, nullable=False, default=False)

    # 创建时间，默认当前 UTC 时间
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 最后更新时间，编辑文章时更新
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
