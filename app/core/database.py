#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:49
# @Author     : fany
# @Project    : PyCharm
# @File       : database.py
# @Description: 数据库配置（同步+异步支持）

from sqlalchemy import create_engine, text  # 确保导入text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from functools import wraps
from typing import Callable, Any

from app.core.log import logger
from app.core.settings import settings

# ========== 同步数据库配置 ==========

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

# 创建同步数据库引擎
engine = create_engine(settings.SYNC_DATABASE_URL, **engine_kwargs)

# 创建同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ========== 异步数据库配置 ==========

# 异步数据库引擎配置参数
async_engine_kwargs = {
    "echo": settings.DEBUG,  # 调试模式下输出SQL语句
    "future": True,  # 使用SQLAlchemy 2.0风格
}

async_engine_kwargs.update({
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_POOL_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,  # 连接池预检查
})

logger.info("配置异步PostgreSQL数据库连接")

# 创建异步数据库引擎
async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, **async_engine_kwargs)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # 避免在commit后对象过期
)

# ========== 共用基类 ==========

# 创建基类
Base = declarative_base()


# ========== 依赖注入函数 ==========

def get_db():
    """同步数据库依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """异步数据库依赖注入"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ========== 数据库管理函数 ==========

def create_tables():
    """创建数据库表（同步方式）"""
    try:
        logger.info("开始创建数据库表...")
        logger.info(f"使用数据库URL: {settings.SYNC_DATABASE_URL}")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        raise


async def create_tables_async():
    """创建数据库表（异步方式）"""
    try:
        logger.info("开始异步创建数据库表...")
        logger.info(f"使用异步数据库URL: {settings.ASYNC_DATABASE_URL}")

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("异步数据库表创建完成")
    except Exception as e:
        logger.error(f"异步创建数据库表失败: {str(e)}")
        raise


async def drop_tables_async():
    """删除数据库表（异步方式）"""
    try:
        logger.warning("开始异步删除数据库表...")

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("异步数据库表删除完成")
    except Exception as e:
        logger.error(f"异步删除数据库表失败: {str(e)}")
        raise


async def check_database_connection():
    """检查数据库连接状态（修复版本）"""
    try:
        async with AsyncSessionLocal() as session:
            # 修复：使用 text() 包装原始SQL，fetchone() 不需要 await
            result = await session.execute(text("SELECT 1"))
            result.fetchone()  # 移除 await
            logger.info("异步数据库连接正常")
            return True
    except Exception as e:
        logger.error(f"异步数据库连接失败: {str(e)}")
        return False


def check_sync_database_connection():
    """检查同步数据库连接状态（修复版本）"""
    try:
        with SessionLocal() as session:
            # 修复：使用 text() 包装原始SQL
            session.execute(text("SELECT 1"))
            logger.info("同步数据库连接正常")
            return True
    except Exception as e:
        logger.error(f"同步数据库连接失败: {str(e)}")
        return False


async def close_async_engine():
    """关闭异步数据库引擎"""
    try:
        await async_engine.dispose()
        logger.info("异步数据库引擎已关闭")
    except Exception as e:
        logger.error(f"关闭异步数据库引擎失败: {str(e)}")


def close_sync_engine():
    """关闭同步数据库引擎"""
    try:
        engine.dispose()
        logger.info("同步数据库引擎已关闭")
    except Exception as e:
        logger.error(f"关闭同步数据库引擎失败: {str(e)}")


# ========== 数据库健康检查 ==========

async def get_database_info():
    """获取数据库信息（修复版本）"""
    try:
        async with AsyncSessionLocal() as session:
            # 修复：使用 text() 包装所有原始SQL，fetchone() 不需要 await

            # 获取数据库版本
            result = await session.execute(text("SELECT version()"))
            version = result.fetchone()[0]  # 移除 await

            # 获取连接数
            result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            )
            active_connections = result.fetchone()[0]  # 移除 await

            # 获取数据库大小
            result = await session.execute(
                text(f"SELECT pg_size_pretty(pg_database_size('{settings.POSTGRES_DB}'))")
            )
            db_size = result.fetchone()[0]  # 移除 await

            return {
                "version": version,
                "active_connections": active_connections,
                "database_size": db_size,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_POOL_OVERFLOW
            }
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        return None


# ========== 数据库初始化 ==========

async def init_database():
    """初始化数据库（修复版本）"""
    try:
        logger.info("开始初始化数据库...")

        # 检查连接
        if not await check_database_connection():
            raise Exception("数据库连接失败")

        # 创建表
        await create_tables_async()

        # 获取数据库信息
        db_info = await get_database_info()
        if db_info:
            logger.info(f"数据库初始化完成，信息: {db_info}")

        logger.info("数据库初始化成功")
        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False


# ========== 额外的数据库工具函数 ==========

async def test_database_operations():
    """测试数据库基本操作"""
    try:
        async with AsyncSessionLocal() as session:
            # 测试基本查询
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.fetchone()[0]  # 移除 await
            logger.info(f"数据库当前时间: {current_time}")

            # 测试数据库信息
            result = await session.execute(text("SELECT current_database()"))
            current_db = result.fetchone()[0]  # 移除 await
            logger.info(f"当前数据库: {current_db}")

            return True
    except Exception as e:
        logger.error(f"数据库操作测试失败: {str(e)}")
        return False


async def get_connection_pool_status():
    """获取连接池状态"""
    try:
        pool = async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalidated": pool.invalidated()
        }
    except Exception as e:
        logger.error(f"获取连接池状态失败: {str(e)}")
        return None


def get_sync_connection_pool_status():
    """获取同步连接池状态"""
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalidated": pool.invalidated()
        }
    except Exception as e:
        logger.error(f"获取同步连接池状态失败: {str(e)}")
        return None


# ========== 事务装饰器 ==========

def async_transaction(func: Callable) -> Callable:
    """异步事务装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        async with AsyncSessionLocal() as session:
            try:
                # 将session注入到kwargs中
                kwargs['session'] = session
                result = await func(*args, **kwargs)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"事务回滚: {str(e)}")
                raise
            finally:
                await session.close()

    return wrapper


def sync_transaction(func: Callable) -> Callable:
    """同步事务装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        with SessionLocal() as session:
            try:
                # 将session注入到kwargs中
                kwargs['session'] = session
                result = func(*args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"同步事务回滚: {str(e)}")
                raise
            finally:
                session.close()

    return wrapper


# ========== 数据库健康检查增强版 ==========

async def comprehensive_health_check():
    """全面的数据库健康检查"""
    health_info = {
        "database": {
            "status": "unknown",
            "connection": False,
            "tables_exist": False,
            "response_time": 0.0,
            "pool_status": None,
            "database_info": None
        }
    }

    import time
    start_time = time.time()

    try:
        # 检查连接
        connection_ok = await check_database_connection()
        health_info["database"]["connection"] = connection_ok

        if connection_ok:
            # 检查表是否存在
            try:
                async with AsyncSessionLocal() as session:
                    # 检查是否有表
                    result = await session.execute(
                        text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
                    )
                    table_count = result.fetchone()[0]  # 移除 await
                    health_info["database"]["tables_exist"] = table_count > 0
                    health_info["database"]["table_count"] = table_count
            except Exception as e:
                logger.warning(f"检查表存在性失败: {str(e)}")

            # 获取连接池状态
            pool_status = await get_connection_pool_status()
            health_info["database"]["pool_status"] = pool_status

            # 获取数据库信息
            db_info = await get_database_info()
            health_info["database"]["database_info"] = db_info

            health_info["database"]["status"] = "healthy"
        else:
            health_info["database"]["status"] = "unhealthy"

    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        health_info["database"]["status"] = "error"
        health_info["database"]["error"] = str(e)

    finally:
        health_info["database"]["response_time"] = round(time.time() - start_time, 3)

    return health_info


# ========== 导出配置 ==========

__all__ = [
    # 引擎
    'engine',
    'async_engine',

    # 会话
    'SessionLocal',
    'AsyncSessionLocal',

    # 基类
    'Base',

    # 依赖注入
    'get_db',
    'get_async_db',

    # 表管理
    'create_tables',
    'create_tables_async',
    'drop_tables_async',

    # 连接检查
    'check_database_connection',
    'check_sync_database_connection',

    # 引擎管理
    'close_async_engine',
    'close_sync_engine',

    # 数据库信息
    'get_database_info',
    'get_connection_pool_status',
    'get_sync_connection_pool_status',

    # 初始化
    'init_database',

    # 测试和健康检查
    'test_database_operations',
    'comprehensive_health_check',

    # 装饰器
    'async_transaction',
    'sync_transaction'
]