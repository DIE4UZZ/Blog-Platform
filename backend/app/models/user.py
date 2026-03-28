from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.app.db.base import Base


class User(Base):
    """User account model.

    Attributes:
        id (int): Primary key.
        username (str): Unique username.
        email (str): Unique email address.
        phone (str | None): Unique phone number.
        password_hash (str): Hashed password stored in column "password".
        role (str): User role (user/admin).
        preference_tags (str | None): Comma-separated preference tags.
        create_time (datetime): Account creation time.
        last_login_time (datetime | None): Last login time.
    """

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(32), unique=True, nullable=True, index=True)
    password_hash = Column("password", String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user", index=True)
    preference_tags = Column(String(512), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_time = Column(DateTime, nullable=True)

