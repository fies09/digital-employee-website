#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/27 10:56
# @Author     : fany
# @Project    : PyCharm
# @File       : cache_tool.py
# @Description:

import json
from typing import Optional

from fastapi import Depends

from app.core.log import logger
from app.core.redis_client import get_redis_client, AsyncRedisOperations
from app.utils.bilim_api import generate_cache_key


async def batch_cache_operations_example(
        merchant_id: str,
        client_id: str,
        data: dict,
        redis_client=Depends(get_redis_client)
):
    """批量Redis操作示例"""
    try:
        redis_ops = AsyncRedisOperations(redis_client)

        # 定义批量操作
        operations = [
            ('setex', f"merchant:{merchant_id}", 3600, json.dumps(data)),
            ('setex', f"auth:{client_id}", 3600, json.dumps(data)),
            ('setex', f"mapping:{merchant_id}", 3600, client_id),
        ]

        # 执行批量操作
        results = await redis_ops.pipeline_operations(operations)
        logger.info(f"批量操作完成，结果: {results}")

        return True

    except Exception as e:
        logger.error(f"批量Redis操作失败: {str(e)}")
        return False


# ============ 缓存工具函数 ============

async def get_cached_merchant_info(
        merchant_id: str,
        redis_client=Depends(get_redis_client)
) -> Optional[dict]:
    """从缓存获取商户信息"""
    try:
        redis_ops = AsyncRedisOperations(redis_client)
        cache_key = generate_cache_key("merchant", merchant_id)

        data = await redis_ops.get_json(cache_key)
        if data:
            logger.debug(f"缓存命中，merchant_id: {merchant_id}")
            return data

        logger.debug(f"缓存未命中，merchant_id: {merchant_id}")
        return None

    except Exception as e:
        logger.error(f"获取缓存商户信息失败: {str(e)}")
        return None


async def invalidate_merchant_cache(
        merchant_id: str,
        redis_client=Depends(get_redis_client)
) -> bool:
    """清除商户相关缓存"""
    try:
        redis_ops = AsyncRedisOperations(redis_client)

        # 清除相关的所有缓存键
        keys_to_delete = [
            generate_cache_key("merchant", merchant_id),
            generate_cache_key("merchant_mapping", merchant_id),
        ]

        # 也可以通过模式匹配清除相关缓存
        pattern_keys = await redis_ops.get_keys_by_pattern(f"*{merchant_id}*")
        keys_to_delete.extend(pattern_keys)

        # 批量删除
        for key in keys_to_delete:
            await redis_ops.delete_key(key)

        logger.info(f"已清除merchant_id: {merchant_id} 相关缓存，共 {len(keys_to_delete)} 个键")
        return True

    except Exception as e:
        logger.error(f"清除商户缓存失败: {str(e)}")
        return False