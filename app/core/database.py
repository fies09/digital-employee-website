#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:49
# @Author     : fany
# @Project    : PyCharm
# @File       : database.py
# @Description:
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.log import logger
from app.core.settings import settings



# 数据库引擎配置参数
engine_kwargs = {
    "pool_pre_ping": True,  # 连接池预检查
    "echo": settings.DEBUG,  # 调试模式下输出SQL语句
}

engine_kwargs.update({
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_POOL_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
})
logger.info("使用PostgreSQL数据库配置")


# 创建数据库引擎
engine = create_engine(settings.SYNC_DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

def get_db():
    """数据库依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建数据库表"""
    try:
        logger.info("开始创建数据库表...")
        logger.info(f"使用数据库URL: {settings.SYNC_DATABASE_URL}")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        raise