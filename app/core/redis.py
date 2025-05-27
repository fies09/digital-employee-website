#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:49
# @Author     : fany
# @Project    : PyCharm
# @File       : redis.py
# @Description:
import asyncio
from typing import Optional, List, Dict, Any, Union
import json

# 导入异步Redis客户端
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from app.core.log import logger
from app.core.settings import settings


class AsyncRedisClient:
    """异步Redis客户端管理类"""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None

    async def init_redis(
            self,
            host: str = "localhost",
            port: int = 6379,
            db: int = 0,
            password: Optional[str] = None,
            max_connections: int = 10
    ):
        """异步初始化Redis连接"""
        try:
            # 创建异步连接池
            self._connection_pool = ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # 创建异步Redis客户端
            self._redis_client = redis.Redis(
                connection_pool=self._connection_pool
            )

            # 测试连接
            await self._redis_client.ping()
            logger.info(f"异步Redis连接成功: {host}:{port}/{db}")

        except Exception as e:
            logger.error(f"异步Redis连接失败: {str(e)}")
            raise

    def get_client(self) -> redis.Redis:
        """获取异步Redis客户端"""
        if self._redis_client is None:
            raise RuntimeError("异步Redis客户端未初始化，请先调用init_redis()")
        return self._redis_client

    async def close(self):
        """关闭异步Redis连接"""
        if self._redis_client:
            await self._redis_client.aclose()  # 使用 aclose() 而不是 close()
        if self._connection_pool:
            await self._connection_pool.aclose()  # 使用 aclose() 而不是 disconnect()
        logger.info("异步Redis连接已关闭")

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self._redis_client:
                await self._redis_client.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Redis健康检查失败: {str(e)}")
            return False


# 全局异步Redis客户端实例
async_redis_client_manager = AsyncRedisClient()


async def init_redis_client():
    """异步初始化Redis客户端（在应用启动时调用）"""
    try:
        await async_redis_client_manager.init_redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 10)
        )
        logger.info("异步Redis客户端初始化完成")
    except Exception as e:
        logger.error(f"异步Redis客户端初始化失败: {str(e)}")
        raise


def get_redis_client() -> Optional[redis.Redis]:
    """依赖注入函数：获取异步Redis客户端（安全版本）"""
    try:
        return async_redis_client_manager.get_client()
    except RuntimeError as e:
        logger.warning(f"Redis客户端获取失败: {str(e)}")
        return None


async def close_redis_client():
    """关闭异步Redis客户端（在应用关闭时调用）"""
    await async_redis_client_manager.close()


# =============================================
# 异步Redis操作工具类
# =============================================

class AsyncRedisOperations:
    """异步Redis操作工具类"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set_with_expire(self, key: str, value: str, expire_seconds: int) -> bool:
        """异步设置键值对并设置过期时间"""
        try:
            result = await self.redis.setex(key, expire_seconds, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis异步设置失败，key: {key}, error: {str(e)}")
            return False

    async def get_value(self, key: str) -> Optional[str]:
        """异步获取键对应的值"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis异步获取失败，key: {key}, error: {str(e)}")
            return None

    async def delete_key(self, key: str) -> bool:
        """异步删除键"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis异步删除失败，key: {key}, error: {str(e)}")
            return False

    async def exists_key(self, key: str) -> bool:
        """异步检查键是否存在"""
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis异步检查存在失败，key: {key}, error: {str(e)}")
            return False

    async def get_ttl(self, key: str) -> int:
        """异步获取键的剩余过期时间"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis异步获取TTL失败，key: {key}, error: {str(e)}")
            return -1

    async def increment(self, key: str, amount: int = 1) -> int:
        """异步原子性递增"""
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis异步递增失败，key: {key}, error: {str(e)}")
            return -1

    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """异步根据模式获取键列表"""
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Redis异步获取键列表失败，pattern: {pattern}, error: {str(e)}")
            return []

    async def set_json(self, key: str, value: Dict[str, Any], expire_seconds: int) -> bool:
        """异步设置JSON数据"""
        try:
            json_str = json.dumps(value, ensure_ascii=False, default=str)
            return await self.set_with_expire(key, json_str, expire_seconds)
        except Exception as e:
            logger.error(f"Redis异步设置JSON失败，key: {key}, error: {str(e)}")
            return False

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """异步获取JSON数据"""
        try:
            json_str = await self.get_value(key)
            if json_str:
                return json.loads(json_str)
            return None
        except Exception as e:
            logger.error(f"Redis异步获取JSON失败，key: {key}, error: {str(e)}")
            return None

    async def expire_key(self, key: str, seconds: int) -> bool:
        """异步设置键的过期时间"""
        try:
            result = await self.redis.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis异步设置过期时间失败，key: {key}, error: {str(e)}")
            return False

    async def pipeline_operations(self, operations: List[tuple]) -> List[Any]:
        """异步批量操作"""
        try:
            pipe = self.redis.pipeline()

            for operation in operations:
                op_type = operation[0]
                args = operation[1:]

                if op_type == 'set':
                    pipe.set(*args)
                elif op_type == 'setex':
                    pipe.setex(*args)
                elif op_type == 'get':
                    pipe.get(*args)
                elif op_type == 'delete':
                    pipe.delete(*args)

            results = await pipe.execute()
            return results
        except Exception as e:
            logger.error(f"Redis异步批量操作失败: {str(e)}")
            return []


# =============================================
# 可选的Redis客户端依赖注入
# =============================================

def get_optional_redis_client():
    """可选的Redis客户端依赖注入（不会因为Redis未初始化而崩溃）"""
    if not async_redis_client_manager._redis_client:
        logger.warning("Redis客户端未初始化，返回None")
        return None

    try:
        return async_redis_client_manager.get_client()
    except Exception as e:
        logger.warning(f"获取Redis客户端失败: {str(e)}")
        return None
