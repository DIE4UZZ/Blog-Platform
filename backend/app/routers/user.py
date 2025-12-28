from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import success_response
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, PreferenceUpdateRequest, RegisterRequest
from app.core.deps import get_current_user

router = APIRouter()


@router.post("/user/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account.

    Args:
        payload (RegisterRequest): Registration payload.
        db (Session): Database session.

    Returns:
        dict: Standardized response with user_id.
    """

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已注册")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
        create_time=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success_response({"user_id": user.id}, message="注册成功")


@router.post("/user/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login user and issue JWT token.

    Args:
        payload (LoginRequest): Login payload.
        db (Session): Database session.

    Returns:
        dict: Standardized response with token and user info.
    """

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    user.last_login_time = datetime.utcnow()
    db.add(user)
    db.commit()
    token = create_access_token(str(user.id))
    return success_response(
        {
            "user_id": user.id,
            "email": user.email,
            "token": token,
        },
        message="登录成功",
    )


@router.get("/user/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """Get current user profile information.

    Args:
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with user profile.
    """

    data = {
        "user_id": current_user.id,
        "email": current_user.email,
        "phone": None,
        "username": None,
        "preference_tags": current_user.preference_tags or "",
        "create_time": current_user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_login_time": current_user.last_login_time.strftime("%Y-%m-%d %H:%M:%S")
        if current_user.last_login_time
        else None,
    }
    return success_response(data)


@router.put("/user/preference")
def update_preference(
    payload: PreferenceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's preference tags.

    Args:
        payload (PreferenceUpdateRequest): Preference update payload.
        db (Session): Database session.
        current_user (User): Current user from auth dependency.

    Returns:
        dict: Standardized response with empty data.
    """

    current_user.preference_tags = payload.preference_tags
    db.add(current_user)
    db.commit()
    return success_response({}, message="更新成功")
