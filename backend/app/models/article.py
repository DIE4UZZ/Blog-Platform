from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Article(Base):
    """Article model for blog content.

    Attributes:
        id (int): Primary key.
        author_id (int): Author user id.
        title (str): Article title.
        content (str): Markdown content.
        html_content (str): Rendered HTML content.
        summary (str): Short summary of content.
        category (str): Article category.
        tags (str | None): Comma-separated tags.
        status (str): draft/published.
        view_count (int): View counter.
        like_count (int): Like counter.
        collect_count (int): Collect counter.
        comment_count (int): Comment counter.
        is_deleted (bool): Soft delete flag.
        create_time (datetime): Creation time.
        update_time (datetime): Update time.
    """

    __tablename__ = "article"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    html_content = Column(Text, nullable=False)
    summary = Column(String(512), nullable=False)
    category = Column(String(64), nullable=False)
    tags = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, default="published", index=True)
    view_count = Column(Integer, nullable=False, default=0)
    like_count = Column(Integer, nullable=False, default=0)
    collect_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    is_deleted = Column(Boolean, nullable=False, default=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    author = relationship("User")
