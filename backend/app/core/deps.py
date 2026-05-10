"""
core/deps.py —— FastAPI 依赖注入函数

本模块提供三个可复用的 Depends 依赖：
  - get_current_user   : 强制要求登录，未登录抛 401
  - get_optional_user  : 可选登录，未登录返回 None（用于公开接口）
  - require_admin      : 在 get_current_user 基础上进一步要求管理员角色

使用方式（在路由函数参数中声明）：
    current_user: User = Depends(get_current_user)
    current_user: User | None = Depends(get_optional_user)
    _: User = Depends(require_admin)
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token  # JWT 解码
from backend.app.db.session import get_db                  # 数据库会话
from backend.app.models.user import User                   # 用户 ORM 模型

# HTTPBearer 从请求头 Authorization: Bearer <token> 中提取凭证
# auto_error=False 表示未提供 Token 时不自动抛出异常，由依赖函数自行处理
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从请求头中解析 JWT Token，返回当前登录用户。

    流程：
      1. 检查 credentials 是否存在（即请求头是否携带 Bearer Token）
      2. 解码 Token，提取 sub 字段（用户 ID）
      3. 查询数据库确认用户存在
      4. 任一步骤失败均抛出 401 异常

    Args:
        credentials: FastAPI 自动从 Authorization 请求头提取的 Bearer 凭证。
        db: 数据库会话（由 get_db 依赖注入）。

    Returns:
        User: 当前已认证的用户 ORM 实例。

    Raises:
        HTTPException(401): Token 缺失、无效、过期或用户不存在时抛出。
    """
    if credentials is None:
        # 请求头中没有 Authorization 字段
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")
    try:
        # 解码 JWT，获取 payload
        payload = decode_access_token(credentials.credentials)
        # sub 字段存储的是用户 ID（字符串形式）
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        # Token 签名错误、过期或 sub 字段格式异常
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")

    # 根据用户 ID 查询数据库
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Token 有效但用户已被删除
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或 Token 失效")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """尝试从请求头解析 JWT Token，成功则返回用户，失败则返回 None。

    适用于既支持匿名访问又支持登录增强功能的接口，
    例如文章详情页（未登录可查看，登录后可显示点赞/收藏状态）。

    Args:
        credentials: Bearer 凭证，可为 None。
        db: 数据库会话。

    Returns:
        Optional[User]: 已认证的用户实例，或 None（未登录/Token 无效）。
    """
    if credentials is None:
        return None  # 未携带 Token，视为匿名用户
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None  # Token 无效，静默处理，不抛异常
    return db.query(User).filter(User.id == user_id).first()


def require_admin(user: User = Depends(get_current_user)) -> User:
    """在已登录的基础上，进一步要求当前用户具有管理员角色。

    依赖链：require_admin → get_current_user → HTTPBearer + get_db

    Args:
        user: 由 get_current_user 注入的当前登录用户。

    Returns:
        User: 当前管理员用户实例。

    Raises:
        HTTPException(403): 用户角色不是 "admin" 时抛出。
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    return user
