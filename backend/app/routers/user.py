"""
routers/user.py —— 用户账号路由模块

提供用户注册、登录、信息查询、偏好更新等接口：
  - POST /user/register   : 用户注册（用户名 + 邮箱/手机号 + 密码）
  - POST /user/login      : 用户登录（支持用户名/邮箱/手机号 + 密码）
  - GET  /user/info       : 获取当前登录用户的详细信息（含粉丝数、收藏数等）
  - PUT  /user/preference : 更新当前用户的偏好标签（用于个性化推荐）
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.response import success_response
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_read_later import ArticleReadLater
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow
from backend.app.models.user_notification import UserNotification
from backend.app.schemas.user import LoginRequest, PreferenceUpdateRequest, RegisterRequest

router = APIRouter()


def _normalize_optional(value: str | None) -> str | None:
    """将字符串去除首尾空格，空字符串转为 None。

    用于处理邮箱、手机号等可选字段：
      - None → None（未填写）
      - "  " → None（只有空格，视为未填写）
      - " abc " → "abc"（去除首尾空格）

    Args:
        value (str | None): 原始字符串，可为 None。

    Returns:
        str | None: 处理后的字符串，空字符串返回 None。
    """
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None  # 空字符串转为 None


@router.post("/user/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册接口。

    注册流程：
      1. 校验密码长度（bcrypt 最多处理 72 字节）
      2. 规范化用户名、邮箱、手机号（去除首尾空格）
      3. 检查用户名/邮箱/手机号是否已被注册（唯一性校验）
      4. 创建用户记录，密码使用 bcrypt 哈希存储
      5. 返回新用户 ID

    Args:
        payload (RegisterRequest): 注册请求体，包含 username/email/phone/password。
        db (Session): 数据库会话（依赖注入）。

    Returns:
        成功响应，data 包含 user_id。

    Raises:
        HTTPException(400): 密码超长、用户名/邮箱/手机号已存在时抛出。
    """
    # bcrypt 最多处理 72 字节，超出部分会被截断，可能导致安全问题
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码超过 bcrypt 72 字节限制")

    # 规范化输入字段
    username = payload.username.strip()
    email = _normalize_optional(payload.email)
    phone = _normalize_optional(payload.phone)

    # 唯一性校验：用户名、邮箱、手机号均不能重复
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="邮箱已注册")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="手机号已注册")

    # 创建用户记录，密码使用 bcrypt 哈希
    user = User(
        username=username,
        email=email,
        phone=phone,
        password_hash=hash_password(payload.password),  # 哈希密码，不存明文
        role="user",                                     # 默认普通用户角色
        create_time=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # 刷新以获取数据库生成的 id
    return success_response({"user_id": user.id}, message="注册成功")


@router.post("/user/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """用户登录接口。

    登录流程：
      1. 校验密码长度
      2. 收集所有非空账号字段（account/username/email/phone）
      3. 用 OR 查询匹配任意字段，找到对应用户
      4. 验证密码哈希
      5. 更新最近登录时间
      6. 生成 JWT Token 并返回

    支持三种登录方式：
      - 用户名 + 密码
      - 邮箱 + 密码
      - 手机号 + 密码

    Args:
        payload (LoginRequest): 登录请求体。
        db (Session): 数据库会话。

    Returns:
        成功响应，data 包含 user_id/username/email/phone/token。

    Raises:
        HTTPException(400): 账号不存在或密码错误时抛出（不区分两种情况，防止枚举攻击）。
    """
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码超过 bcrypt 72 字节限制")

    # 规范化所有账号字段
    account = _normalize_optional(payload.account)
    email = _normalize_optional(payload.email)
    username = _normalize_optional(payload.username)
    phone = _normalize_optional(payload.phone)

    # 收集所有非空账号值，用于 OR 查询
    candidates = [value for value in [account, email, username, phone] if value]
    user = (
        db.query(User)
        .filter(
            or_(
                User.username.in_(candidates),  # 匹配用户名
                User.email.in_(candidates),     # 匹配邮箱
                User.phone.in_(candidates),     # 匹配手机号
            )
        )
        .first()
        if candidates
        else None
    )
    # 用户不存在或密码错误，统一返回相同错误信息（防止枚举攻击）
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名、邮箱、手机号或密码错误")

    # 更新最近登录时间
    user.last_login_time = datetime.utcnow()
    db.add(user)
    db.commit()

    # 生成 JWT Token，subject 为用户 ID 字符串
    token = create_access_token(str(user.id))
    return success_response(
        {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "token": token,         # 前端存储此 Token，后续请求放入 Authorization 头
        },
        message="登录成功",
    )


@router.get("/user/info")
def get_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的详细信息。

    除基本信息外，还聚合以下统计数据：
      - follower_count          : 粉丝数（关注我的人数）
      - following_count         : 关注数（我关注的人数）
      - unread_notification_count: 未读通知数
      - collection_count        : 收藏文章数
      - read_later_count        : 稍后阅读文章数

    Args:
        db (Session): 数据库会话。
        current_user (User): 当前登录用户（由 JWT Token 解析）。

    Returns:
        成功响应，data 包含用户完整信息和统计数据。
    """
    # 统计粉丝数：following_id = 我的 ID 的记录数
    follower_count = db.query(UserFollow).filter(UserFollow.following_id == current_user.id).count()
    # 统计关注数：follower_id = 我的 ID 的记录数
    following_count = db.query(UserFollow).filter(UserFollow.follower_id == current_user.id).count()
    # 统计未读通知数
    unread_notification_count = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.is_read == False)
        .count()
    )
    # 统计收藏文章数
    collection_count = db.query(ArticleCollect).filter(ArticleCollect.user_id == current_user.id).count()
    # 统计稍后阅读文章数
    read_later_count = (
        db.query(ArticleReadLater)
        .filter(ArticleReadLater.user_id == current_user.id)
        .count()
    )

    data = {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "preference_tags": current_user.preference_tags or "",  # None 转为空字符串
        "create_time": current_user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_login_time": current_user.last_login_time.strftime("%Y-%m-%d %H:%M:%S")
        if current_user.last_login_time
        else None,
        "follower_count": follower_count,
        "following_count": following_count,
        "unread_notification_count": unread_notification_count,
        "collection_count": collection_count,
        "read_later_count": read_later_count,
    }
    return success_response(data)


@router.put("/user/preference")
def update_preference(
    payload: PreferenceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新当前用户的偏好标签。

    偏好标签用于个性化推荐算法，格式为逗号分隔的字符串，
    例如 "Python,机器学习,深度学习"。

    Args:
        payload (PreferenceUpdateRequest): 请求体，包含 preference_tags 字段。
        db (Session): 数据库会话。
        current_user (User): 当前登录用户。

    Returns:
        成功响应，data 为空对象。
    """
    # 直接覆盖偏好标签（空字符串表示清空所有偏好）
    current_user.preference_tags = payload.preference_tags
    db.add(current_user)
    db.commit()
    return success_response({}, message="更新成功")
