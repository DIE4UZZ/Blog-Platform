"""
db/base.py —— SQLAlchemy 声明式基类

所有 ORM 模型类均继承自 Base，SQLAlchemy 通过 Base.metadata
统一管理所有表的元数据（表名、列定义、索引等）。

使用方式：
    from backend.app.db.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
        ...
"""

from sqlalchemy.orm import declarative_base

# 声明式基类：所有 ORM 模型的父类
# declarative_base() 返回一个基类，子类通过 __tablename__ 映射到数据库表
Base = declarative_base()
