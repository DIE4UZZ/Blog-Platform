from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Return the current authenticated user.

    Args:
        credentials (HTTPAuthorizationCredentials): Bearer credentials.
        db (Session): Database session.

    Returns:
        User: Authenticated user instance.

    Raises:
        HTTPException: When authentication fails.
    """

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the current user if token exists, otherwise None.

    Args:
        credentials (HTTPAuthorizationCredentials): Bearer credentials.
        db (Session): Database session.

    Returns:
        Optional[User]: User instance or None.
    """

    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require current user to be admin.

    Args:
        user (User): Current user.

    Returns:
        User: Current user if admin.

    Raises:
        HTTPException: When user is not admin.
    """

    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    return user

