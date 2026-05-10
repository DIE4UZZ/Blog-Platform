"""
core/config.py —— 应用配置管理

使用 pydantic-settings 从环境变量或 .env 文件中读取配置项。
所有配置项均以 BLOG_ 为前缀（例如 BLOG_DATABASE_URL）。

配置加载优先级（由高到低）：
  1. 操作系统环境变量
  2. backend/.env 文件
  3. 字段默认值
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置类，字段值从环境变量自动注入。

    Attributes:
        database_url (str): SQLAlchemy 数据库连接 URL，默认连接本地 MySQL。
            格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
        jwt_secret (str): JWT 签名密钥，生产环境必须替换为随机强密钥。
        jwt_algorithm (str): JWT 签名算法，默认 HS256（HMAC-SHA256）。
        jwt_expire_hours (int): JWT Token 有效期（小时），默认 24 小时。
        cors_origins (List[str]): 允许跨域的来源列表，默认 ["*"] 表示允许所有来源。
    """

    # 数据库连接字符串，默认指向本地 MySQL 的 blog_platform 数据库
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/blog_platform?charset=utf8mb4"

    # JWT 相关配置
    jwt_secret: str = "change_me"       # 签名密钥，生产环境务必修改
    jwt_algorithm: str = "HS256"        # 签名算法
    jwt_expire_hours: int = 24          # Token 有效期（小时）

    # CORS 允许的前端来源，["*"] 表示不限制
    cors_origins: List[str] = ["*"]

    # pydantic-settings 元配置
    model_config = SettingsConfigDict(
        env_prefix="BLOG_",             # 环境变量前缀，例如 BLOG_JWT_SECRET
        env_file="backend/.env",        # 从该路径读取 .env 文件
        env_file_encoding="utf-8",
        case_sensitive=False,           # 环境变量名不区分大小写
        extra="ignore",                 # 忽略 .env 中多余的字段
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局唯一的配置实例（单例，使用 lru_cache 缓存）。

    使用 lru_cache 确保整个进程生命周期内只解析一次配置，
    避免重复读取文件或环境变量带来的性能开销。

    Returns:
        Settings: 已加载的配置实例。
    """
    return Settings()
