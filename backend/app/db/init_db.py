"""
db/init_db.py —— 数据库初始化与迁移

职责：
  1. 根据所有 ORM 模型的元数据，自动创建尚不存在的数据库表（create_all）
  2. 对已存在的旧数据库执行字段补全（_ensure_user_columns），
     处理 username 和 phone 字段后期新增的情况，保证向后兼容

注意：本模块不使用 Alembic 等迁移工具，而是通过 SQLAlchemy 的
      inspect + ALTER TABLE 手动处理增量迁移，适合小型项目快速迭代。
"""

from sqlalchemy import inspect, text

from backend.app.db.base import Base
from backend.app.db.session import engine
# 导入所有模型，确保 Base.metadata 中包含所有表定义
from backend.app.models.article import Article
from backend.app.models.article_collect import ArticleCollect
from backend.app.models.article_read_later import ArticleReadLater
from backend.app.models.article_like import ArticleLike
from backend.app.models.behavior import UserBehavior
from backend.app.models.comment import Comment
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User
from backend.app.models.user_follow import UserFollow
from backend.app.models.user_notification import UserNotification


def _ensure_user_columns() -> None:
    """检查并补全 user 表中后期新增的字段（username、phone）。

    背景：项目早期 user 表可能没有 username 和 phone 字段，
    后续版本新增后需要对已有数据库执行 ALTER TABLE 补全。

    处理逻辑：
      1. 检查 user 表是否存在，不存在则直接返回（首次建表由 create_all 处理）
      2. 获取当前表的所有列名
      3. 若缺少 username 列：添加列 → 用 email 或 id 填充默认值
      4. 若缺少 phone 列：添加列 → 将空字符串置为 NULL
      5. 对 MySQL（非 SQLite）：将 username 改为 NOT NULL，并创建唯一索引
    """
    inspector = inspect(engine)
    # 若 user 表还不存在，跳过（首次启动时 create_all 会建表）
    if "user" not in inspector.get_table_names():
        return

    # 获取当前 user 表已有的列名集合
    columns = {column["name"] for column in inspector.get_columns("user")}
    statements: list[str] = []

    # 收集需要执行的 ALTER TABLE 语句
    if "username" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN username VARCHAR(64)")
    if "phone" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN phone VARCHAR(32)")

    with engine.begin() as connection:
        # 执行 ALTER TABLE 添加缺失列
        for statement in statements:
            connection.execute(text(statement))

        # 为新增的 username 列填充默认值
        if "username" not in columns:
            # SQLite 和 MySQL 的字符串拼接语法不同
            username_fill_sql = (
                # SQLite 语法：使用 || 拼接
                "UPDATE user SET username = COALESCE(NULLIF(email, ''), 'user_' || id) "
                "WHERE username IS NULL OR username = ''"
                if engine.dialect.name == "sqlite"
                # MySQL 语法：使用 CONCAT 函数
                else "UPDATE user SET username = COALESCE(NULLIF(email, ''), CONCAT('user_', id)) "
                "WHERE username IS NULL OR username = ''"
            )
            connection.execute(text(username_fill_sql))

        # 将 phone 列的空字符串统一置为 NULL（保持数据一致性）
        if "phone" not in columns:
            connection.execute(text("UPDATE user SET phone = NULL WHERE phone = ''"))

        # MySQL 专属操作：设置 NOT NULL 约束并创建唯一索引
        if engine.dialect.name != "sqlite":
            if "username" not in columns:
                # 数据填充完成后，将 username 改为 NOT NULL
                connection.execute(text("ALTER TABLE user MODIFY username VARCHAR(64) NOT NULL"))
            # 获取已有索引名，避免重复创建
            index_names = {index["name"] for index in inspector.get_indexes("user")}
            if "ix_user_username" not in index_names:
                connection.execute(text("CREATE UNIQUE INDEX ix_user_username ON user (username)"))
            if "ix_user_phone" not in index_names:
                connection.execute(text("CREATE UNIQUE INDEX ix_user_phone ON user (phone)"))


def init_db():
    """初始化数据库：建表 + 字段迁移。

    在应用启动时（startup 事件）调用，执行两步操作：
      1. create_all：根据所有 ORM 模型自动创建尚不存在的表，已存在的表不会修改
      2. _ensure_user_columns：对旧数据库补全新增字段，保证向后兼容
    """
    # 根据 Base.metadata 中注册的所有模型，创建对应的数据库表
    Base.metadata.create_all(bind=engine)
    # 补全旧数据库中可能缺失的字段
    _ensure_user_columns()
