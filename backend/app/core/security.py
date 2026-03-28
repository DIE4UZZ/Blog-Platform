from datetime import datetime, timedelta
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash plain-text password with bcrypt.

    Args:
        password (str): Plain-text password.

    Returns:
        str: Hashed password.
    """

    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plain-text password against stored hash.

    Args:
        password (str): Plain-text password.
        password_hash (str): Stored password hash.

    Returns:
        bool: True if matches, False otherwise.
    """

    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    """Create JWT access token for a subject.

    Args:
        subject (str): Token subject (user id).

    Returns:
        str: Encoded JWT token string.
    """

    settings = get_settings()
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    payload: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode JWT access token and return payload.

    Args:
        token (str): JWT token string.

    Returns:
        Dict[str, Any]: Token payload.
    """

    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

