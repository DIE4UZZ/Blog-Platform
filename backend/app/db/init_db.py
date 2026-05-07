from sqlalchemy import inspect, text

from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.models.article import Article
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_read_later import ArticleReadLater
from backend.app.models.article_like import ArticleLike
from backend.app.models.behavior import UserBehavior
from backend.app.models.comment import Comment
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow
from backend.app.models.user_notification import UserNotification


def _ensure_user_columns() -> None:
    """Backfill newly added user columns for existing databases."""

    inspector = inspect(engine)
    if "user" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("user")}
    statements: list[str] = []
    if "username" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN username VARCHAR(64)")
    if "phone" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN phone VARCHAR(32)")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        if "username" not in columns:
            username_fill_sql = (
                "UPDATE user SET username = COALESCE(NULLIF(email, ''), 'user_' || id) "
                "WHERE username IS NULL OR username = ''"
                if engine.dialect.name == "sqlite"
                else "UPDATE user SET username = COALESCE(NULLIF(email, ''), CONCAT('user_', id)) "
                "WHERE username IS NULL OR username = ''"
            )
            connection.execute(
                text(username_fill_sql)
            )
        if "phone" not in columns:
            connection.execute(text("UPDATE user SET phone = NULL WHERE phone = ''"))

        if engine.dialect.name != "sqlite":
            if "username" not in columns:
                connection.execute(text("ALTER TABLE user MODIFY username VARCHAR(64) NOT NULL"))
            index_names = {index["name"] for index in inspector.get_indexes("user")}
            if "ix_user_username" not in index_names:
                connection.execute(text("CREATE UNIQUE INDEX ix_user_username ON user (username)"))
            if "ix_user_phone" not in index_names:
                connection.execute(text("CREATE UNIQUE INDEX ix_user_phone ON user (phone)"))


def init_db():
    """Create database tables based on ORM models."""

    Base.metadata.create_all(bind=engine)
    _ensure_user_columns()
