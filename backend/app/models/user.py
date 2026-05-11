"""
models/user.py —— 用户数据模型

对应数据库表：user

字段说明：
  - id            : 主键，自增整数
  - username      : 用户名，唯一，不可为空，用于登录和展示
  - email         : 邮箱，唯一，可为空（注册时邮箱/手机号至少填一项）
  - phone         : 手机号，唯一，可为空
  - password_hash : bcrypt 哈希后的密码，数据库列名为 "password"
  - role          : 角色，"user"（普通用户）或 "admin"（管理员）
  - preference_tags: 用户偏好标签，逗号分隔的字符串，用于个性化推荐
  - create_time   : 账号创建时间（UTC）
  - last_login_time: 最近一次登录时间（UTC），可为空
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.app.db.base import Base


class User(Base):
    """用户账号 ORM 模型，映射到数据库 user 表。

    Attributes:
        id (int): 主键，自增。
        username (str): 唯一用户名，长度 2-64，用于登录和页面展示。
        email (str | None): 邮箱地址，唯一，可为空。
        phone (str | None): 手机号，唯一，可为空。
        password_hash (str): bcrypt 哈希密码，数据库列名为 "password"。
        role (str): 用户角色，"user" 或 "admin"，默认 "user"。
        preference_tags (str | None): 偏好标签，逗号分隔，例如 "Python,机器学习"。
        create_time (datetime): 账号注册时间（UTC）。
        last_login_time (datetime | None): 最近登录时间（UTC），首次登录前为 None。
    """

    __tablename__ = "user"  # 数据库表名

    # 主键，自增整数，建立索引加速查询
    id = Column(Integer, primary_key=True, index=True)

    # 用户名：唯一约束 + 索引，用于登录和展示
    username = Column(String(64), unique=True, nullable=False, index=True)

    # 邮箱：唯一约束 + 索引，可为空（支持仅手机号注册）
    email = Column(String(255), unique=True, nullable=True, index=True)

    # 手机号：唯一约束 + 索引，可为空（支持仅邮箱注册）
    phone = Column(String(32), unique=True, nullable=True, index=True)

    # 密码哈希：数据库列名为 "password"，Python 属性名为 password_hash
    # 使用 bcrypt 哈希，不存储明文密码
    password_hash = Column("password", String(255), nullable=False)

    # 用户角色：默认 "user"，管理员为 "admin"
    role = Column(String(32), nullable=False, default="user", index=True)

    # 个人简介
    bio = Column(String(500), nullable=True)

    # 偏好标签：逗号分隔的标签字符串，用于推荐算法个性化
    # 例如："Python,机器学习,深度学习"
    preference_tags = Column(String(512), nullable=True)

    # 账号创建时间，默认为当前 UTC 时间
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 最近登录时间，每次登录成功后更新
    last_login_time = Column(DateTime, nullable=True)
