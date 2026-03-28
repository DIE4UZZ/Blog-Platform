from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import LoginRequest, PreferenceUpdateRequest, RegisterRequest

router = APIRouter()


def _normalize_optional(value: str | None) -> str | None:
    """规范化可选字符串字段，去掉首尾空白。"""

    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@router.post("/user/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户。"""

    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码超过 bcrypt 72 字节限制")

    username = payload.username.strip()
    email = _normalize_optional(payload.email)
    phone = _normalize_optional(payload.phone)

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="邮箱已注册")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="手机号已注册")

    user = User(
        username=username,
        email=email,
        phone=phone,
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
    """登录并签发 JWT。"""

    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码超过 bcrypt 72 字节限制")

    account = _normalize_optional(payload.account)
    email = _normalize_optional(payload.email)
    username = _normalize_optional(payload.username)
    phone = _normalize_optional(payload.phone)

    candidates = [value for value in [account, email, username, phone] if value]
    user = (
        db.query(User)
        .filter(
            or_(
                User.username.in_(candidates),
                User.email.in_(candidates),
                User.phone.in_(candidates),
            )
        )
        .first()
        if candidates
        else None
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名、邮箱、手机号或密码错误")

    user.last_login_time = datetime.utcnow()
    db.add(user)
    db.commit()
    token = create_access_token(str(user.id))
    return success_response(
        {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "token": token,
        },
        message="登录成功",
    )


@router.get("/user/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户资料。"""

    data = {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
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
    """更新当前用户偏好标签。"""

    current_user.preference_tags = payload.preference_tags
    db.add(current_user)
    db.commit()
    return success_response({}, message="更新成功")
