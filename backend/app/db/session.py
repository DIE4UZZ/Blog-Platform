"""
db/session.py —— 数据库引擎与会话工厂

职责：
  1. 根据配置创建 SQLAlchemy 数据库引擎（engine）
  2. 创建会话工厂（SessionLocal）
  3. 提供 FastAPI 依赖注入用的 get_db 生成器函数

每个 HTTP 请求通过 Depends(get_db) 获得独立的数据库会话，
请求结束后会话自动关闭，保证连接不泄漏。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import get_settings

# 读取应用配置（数据库连接 URL 等）
_settings = get_settings()

# 创建数据库引擎
# pool_pre_ping=True：每次从连接池取连接前先发送 ping，
# 自动丢弃已断开的连接，避免"MySQL server has gone away"错误
engine = create_engine(_settings.database_url, pool_pre_ping=True)

# 会话工厂：每次调用 SessionLocal() 返回一个新的数据库会话
# autocommit=False：不自动提交，需要手动调用 db.commit()
# autoflush=False：不自动刷新，避免意外的隐式 SQL 执行
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖注入函数：为每个请求提供独立的数据库会话。

    使用 yield 实现上下文管理：
      - yield 之前：创建会话并注入到路由函数
      - yield 之后（finally）：无论是否发生异常，都关闭会话归还连接

    使用方式：
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    Yields:
        sqlalchemy.orm.Session: 当前请求专用的数据库会话实例。
    """
    db = SessionLocal()
    try:
        yield db          # 将会话注入到路由函数中
    finally:
        db.close()        # 请求结束后关闭会话，归还连接池
