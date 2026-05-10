"""
core/security.py —— 安全工具函数

提供密码哈希/验证和 JWT Token 的创建/解码功能。

依赖库：
  - passlib[bcrypt]：用于密码哈希，bcrypt 算法安全性高
  - python-jose[cryptography]：用于 JWT 编解码
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings

# 密码哈希上下文，使用 bcrypt 算法
# deprecated="auto" 表示自动将旧算法哈希标记为需要重新哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """将明文密码哈希为 bcrypt 格式的字符串，用于注册时存储。

    注意：bcrypt 最多处理 72 字节，超出部分会被截断，
    调用方应在传入前校验长度。

    Args:
        password (str): 用户输入的明文密码。

    Returns:
        str: bcrypt 哈希后的密码字符串（含盐值）。
    """
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证明文密码与存储的哈希值是否匹配，用于登录校验。

    Args:
        password (str): 用户输入的明文密码。
        password_hash (str): 数据库中存储的 bcrypt 哈希值。

    Returns:
        bool: 匹配返回 True，否则返回 False。
    """
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    """为指定主体（用户 ID）创建 JWT 访问令牌。

    Payload 结构：
      - sub: 主体标识（用户 ID 字符串）
      - exp: 过期时间（UTC 时间戳）

    Args:
        subject (str): Token 主体，通常为用户 ID 的字符串形式。

    Returns:
        str: 编码后的 JWT 字符串，前端存储后在请求头中携带。
    """
    settings = get_settings()
    # 计算过期时间 = 当前 UTC 时间 + 配置的有效小时数
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    payload: Dict[str, Any] = {
        "sub": subject,   # 主体（用户 ID）
        "exp": expire,    # 过期时间
    }
    # 使用密钥和算法对 payload 进行签名编码
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """解码并验证 JWT 访问令牌，返回 payload 字典。

    若 Token 签名无效或已过期，jose 库会抛出 JWTError，
    调用方应捕获该异常并返回 401 响应。

    Args:
        token (str): 前端传入的 JWT 字符串。

    Returns:
        Dict[str, Any]: 解码后的 payload，包含 sub（用户 ID）等字段。

    Raises:
        jose.JWTError: Token 无效或已过期时抛出。
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
