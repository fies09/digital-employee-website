#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/22 16:59
# @Author     : fany
# @Project    : PyCharm
# @File       : base.py
# @Description:
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.settings import settings

# 动态添加项目根目录到 PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# 创建异步引擎
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,  # 使用异步数据库 URL
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_OVERFLOW,
    connect_args={
        "command_timeout": 600  # 设置所有语句默认超时时间为 600 秒
    }
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=True
)

# 创建基础模型类
Base = declarative_base()

# 获取数据库会话的依赖函数
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
