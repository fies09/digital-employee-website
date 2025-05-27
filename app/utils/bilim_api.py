#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:53
# @Author     : fany
# @Project    : PyCharm
# @File       : bilim_api.py
# @Description:
import json
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import Request, HTTPException, status, Depends
import socket
from app.core.log import logger
from datetime import datetime, timedelta, timezone
import jwt
import secrets
import uuid
from sqlalchemy import select

from app.core.redis import get_redis_client
from app.core.settings import settings
from typing import Tuple, Optional, Dict, Any, List
from app.core.database import get_async_db
from app.models.merchant import Merchant
from app.schemas.RequestModel.auth import CallbackData

def get_server_info(request: Request) -> tuple[str, int]:
    """
    获取当前服务的IP和端口

    参数:
        request: FastAPI请求对象

    返回:
        tuple: (ip, port)
    """
    # 获取服务器IP
    try:
        # 首先尝试从request中获取
        host = request.url.hostname
        port = request.url.port

        # 如果获取不到，使用本机IP
        if not host or host in ['localhost', '127.0.0.1', '0.0.0.0']:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                host = s.getsockname()[0]
            finally:
                s.close()

        # 如果端口获取不到，使用默认端口
        if not port:
            port = getattr(settings, 'PORT', 8000)

    except Exception as e:
        logger.warning(f"获取服务器信息失败，使用默认值: {e}")
        host = "localhost"
        port = getattr(settings, 'PORT', 8000)

    return host, port

def generate_jwt_token(merchant_id: str, app_key: str) -> dict:
    """
    生成JWT令牌

    Args:
        merchant_id: 商户ID
        app_key: 应用Key

    Returns:
        dict: 包含access_token和refresh_token的字典
    """
    try:
        current_time = datetime.utcnow()
        # JWT payload
        payload = {
            "merchant_id": merchant_id,
            "app_key": app_key,
            "exp": current_time + timedelta(hours=settings.JWT_EXPIRE_HOURS),
            "iat": current_time,
            "nbf": current_time,  # 不早于时间
            "jti": str(uuid.uuid4()),  # JWT唯一标识
            "type": "access"
        }

        # 生成access token
        access_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        # 生成refresh token (有效期更长)
        refresh_payload = payload.copy()
        refresh_payload.update({
            "exp": current_time + timedelta(days=settings.JWT_REFRESH_DAYS),
            "jti": str(uuid.uuid4()),  # 不同的JTI
            "type": "refresh"
        })
        refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        logger.info(f"JWT token生成成功，merchant_id: {merchant_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "refresh_expires_in": settings.JWT_REFRESH_DAYS * 24 * 3600
        }
    except Exception as e:
        logger.error(f"JWT token生成失败: {str(e)}")
        raise

def verify_jwt_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    验证JWT令牌

    Args:
        token: JWT令牌
        token_type: 令牌类型 access/refresh

    Returns:
        dict: 解码后的payload

    Raises:
        jwt.ExpiredSignatureError: 令牌过期
        jwt.InvalidTokenError: 令牌无效
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 验证令牌类型
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError(f"Invalid token type: expected {token_type}")

        logger.info(f"JWT token验证成功，type: {token_type}, merchant_id: {payload.get('merchant_id')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning(f"JWT token已过期，type: {token_type}")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token无效，type: {token_type}, error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"JWT token验证异常: {str(e)}")
        raise

def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    使用refresh token生成新的access token

    Args:
        refresh_token: 刷新令牌

    Returns:
        dict: 新的access token信息

    Raises:
        jwt.ExpiredSignatureError: 刷新令牌过期
        jwt.InvalidTokenError: 刷新令牌无效
    """
    try:
        # 验证refresh token
        payload = verify_jwt_token(refresh_token, "refresh")

        # 生成新的access token
        merchant_id = payload.get("merchant_id")
        app_key = payload.get("app_key")

        if not merchant_id or not app_key:
            raise jwt.InvalidTokenError("Invalid refresh token payload")

        # 生成新的access token（只返回access token，不返回新的refresh token）
        current_time = datetime.now(timezone.utc)
        new_payload = {
            "merchant_id": merchant_id,
            "app_key": app_key,
            "exp": current_time + timedelta(hours=settings.JWT_EXPIRE_HOURS),
            "iat": current_time,
            "nbf": current_time,
            "jti": str(uuid.uuid4()),
            "type": "access"
        }

        new_access_token = jwt.encode(
            new_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.info(f"Access token刷新成功，merchant_id: {merchant_id}")

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600
        }

    except Exception as e:
        logger.error(f"Access token刷新失败: {str(e)}")
        raise

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    对密码进行哈希加密

    Args:
        password: 明文密码
        salt: 盐值（可选，如果不提供会自动生成）

    Returns:
        tuple: (hashed_password, salt)
    """
    try:
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2进行密码哈希
        import hashlib
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )

        return hashed.hex(), salt

    except Exception as e:
        logger.error(f"密码哈希失败: {str(e)}")
        raise

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        hashed_password: 哈希密码
        salt: 盐值

    Returns:
        bool: 密码是否正确
    """
    try:
        new_hash, _ = hash_password(password, salt)
        return new_hash == hashed_password

    except Exception as e:
        logger.error(f"密码验证失败: {str(e)}")
        return False

def generate_callback_url(request: Request, merchant_id: Optional[str] = None) -> str:
    """
    生成回调地址

    Args:
        request: FastAPI请求对象
        merchant_id: 商户ID（可选，用于生成更有意义的callback_id）

    Returns:
        str: 完整的回调地址

    示例:
        https://api.example.com/api/v1/auth/callback/MERCHANT_001_kL8mN9pQx7Y2zB4F
    """
    try:
        # 获取服务器信息
        protocol = request.url.scheme or "http"
        host = request.url.hostname or "localhost"
        port = request.url.port or getattr(settings, 'PORT', 8000)

        # 生成回调ID
        if merchant_id:
            # 如果提供了merchant_id，生成更有意义的callback_id
            random_suffix = secrets.token_urlsafe(16)
            callback_id = f"{merchant_id}_{random_suffix}"
        else:
            # 否则生成纯随机ID
            callback_id = secrets.token_urlsafe(24)

        # 构建URL(处理标准端口)
        if (protocol == "https" and port == 443) or (protocol == "http" and port == 80):
            callback_url = f"{protocol}://{host}/api/v1/auth/callback/{callback_id}"
        else:
            callback_url = f"{protocol}://{host}:{port}/api/v1/auth/callback/{callback_id}"

        logger.info(f"生成回调地址: {callback_url}")
        return callback_url

    except Exception as e:
        logger.error(f"生成回调地址失败: {str(e)}")
        # fallback地址
        fallback_id = secrets.token_urlsafe(16)
        if merchant_id:
            fallback_id = f"{merchant_id}_{fallback_id}"

        fallback_url = f"http://localhost:{getattr(settings, 'PORT', 8000)}/api/v1/auth/callback/{fallback_id}"
        logger.warning(f"使用fallback地址: {fallback_url}")
        return fallback_url

def generate_secure_token(length: int = 32) -> str:
    """
    生成安全令牌

    Args:
        length: 令牌长度

    Returns:
        str: 安全令牌
    """
    try:
        return secrets.token_urlsafe(length)
    except Exception as e:
        logger.error(f"生成安全令牌失败: {str(e)}")
        raise

def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳

    Args:
        dt: 时间对象，默认为当前时间

    Returns:
        str: ISO格式的时间字符串
    """
    if dt is None:
        dt = datetime.now()

    return dt.isoformat()

def build_error_response(code: int, message: str, request_id: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    构建标准错误响应

    Args:
        code: 错误码
        message: 错误消息
        request_id: 请求ID
        data: 额外数据

    Returns:
        dict: 标准错误响应
    """
    return {
        "code": code,
        "message": message,
        "success": False,
        "data": data,
        "timestamp": format_timestamp(),
        "request_id": request_id
    }

def build_success_response(data: Any, message: str = "操作成功", request_id: str = "") -> Dict[str, Any]:
    """
    构建标准成功响应

    Args:
        data: 响应数据
        message: 响应消息
        request_id: 请求ID

    Returns:
        dict: 标准成功响应
    """
    return {
        "code": 200,
        "message": message,
        "success": True,
        "data": data,
        "timestamp": format_timestamp(),
        "request_id": request_id
    }

def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """
    隐藏敏感数据

    Args:
        data: 原始数据
        sensitive_keys: 敏感字段列表

    Returns:
        dict: 隐藏敏感信息后的数据
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'app_secret', 'client_secret', 'password', 'token', 'secret',
            'key', 'credential', 'auth', 'jwt', 'refresh_token'
        ]

    try:
        masked_data = data.copy()

        for key, value in masked_data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                if isinstance(value, str) and len(value) > 8:
                    # 显示前4位和后4位，中间用*替换
                    masked_data[key] = f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
                else:
                    masked_data[key] = "***"

        return masked_data

    except Exception as e:
        logger.warning(f"隐藏敏感数据失败: {str(e)}")
        return data

def extract_request_info(request: Request) -> Dict[str, Any]:
    """
    提取请求信息用于日志记录

    Args:
        request: FastAPI请求对象

    Returns:
        dict: 请求信息
    """
    try:
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": {
                "user-agent": request.headers.get("user-agent"),
                "content-type": request.headers.get("content-type"),
                "authorization": "***" if request.headers.get("authorization") else None,
                "x-forwarded-for": request.headers.get("x-forwarded-for"),
                "x-real-ip": request.headers.get("x-real-ip")
            },
            "client": {
                "host": request.client.host if request.client else None,
                "port": request.client.port if request.client else None
            }
        }

    except Exception as e:
        logger.warning(f"提取请求信息失败: {str(e)}")
        return {}

def calculate_token_expiration(hours: int) -> Tuple[datetime, int]:
    """
    计算令牌过期时间

    Args:
        hours: 有效期小时数

    Returns:
        tuple: (过期时间, 过期时间戳)
    """
    try:
        expiration_time = datetime.utcnow() + timedelta(hours=hours)
        expiration_timestamp = int(expiration_time.timestamp())

        return expiration_time, expiration_timestamp

    except Exception as e:
        logger.error(f"计算令牌过期时间失败: {str(e)}")
        raise

def is_token_expired(exp_timestamp: int) -> bool:
    """
    检查令牌是否过期

    Args:
        exp_timestamp: 过期时间戳

    Returns:
        bool: 是否过期
    """
    try:
        current_timestamp = int(datetime.utcnow().timestamp())
        return current_timestamp >= exp_timestamp

    except Exception as e:
        logger.warning(f"检查令牌过期状态失败: {str(e)}")
        return True  # 安全起见，返回已过期

def generate_cache_key(prefix: str, identifier: str, suffix: Optional[str] = None) -> str:
    """
    生成缓存键

    Args:
        prefix: 前缀
        identifier: 标识符
        suffix: 后缀（可选）

    Returns:
        str: 缓存键
    """
    try:
        parts = [prefix, identifier]
        if suffix:
            parts.append(suffix)

        cache_key = ":".join(parts)
        logger.debug(f"生成缓存键: {cache_key}")
        return cache_key

    except Exception as e:
        logger.error(f"生成缓存键失败: {str(e)}")
        raise

def sanitize_log_data(data: Any) -> Any:
    """
    清理日志数据，移除敏感信息

    Args:
        data: 原始数据

    Returns:
        清理后的数据
    """
    try:
        if isinstance(data, dict):
            return mask_sensitive_data(data)
        elif isinstance(data, str):
            # 简单的字符串敏感信息检查
            if any(keyword in data.lower() for keyword in ['password', 'secret', 'token']):
                return "***SENSITIVE***"
            return data
        else:
            return data

    except Exception as e:
        logger.warning(f"清理日志数据失败: {str(e)}")
        return "***ERROR***"

async def verify_bilin_credentials(client_id: str, client_secret: str, request_id: str) -> dict:
    """
    内部方法：验证比邻平台凭证

    Args:
        client_id: 客户端ID
        client_secret: 客户端密钥
        request_id: 请求ID

    Returns:
        dict: 比邻平台响应结果

    Raises:
        HTTPException: 验证失败时抛出异常
    """
    logger.info(f"[{request_id}] 开始验证比邻平台凭证，clientId: {client_id}")

    bilin_request_data = {
        "clientId": client_id,
        "clientSecret": client_secret
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.BILIN_LOGIN_ENDPOINT,
                json=bilin_request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DigitalEmployee/1.0"
                }
            )

            logger.info(f"[{request_id}] 比邻平台响应状态: {response.status_code}")

            if response.status_code == 200:
                bilin_response = response.json()
                # 检查比邻平台的业务状态码
                if bilin_response.get('code') == 0:  # 假设0表示成功
                    logger.info(f"[{request_id}] 比邻平台凭证验证成功")
                    return bilin_response
                else:
                    logger.warning(f"[{request_id}] 比邻平台凭证验证失败: {bilin_response.get('message')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": 400,
                            "message": f"凭证验证失败: {bilin_response.get('message', '未知错误')}",
                            "success": False,
                            "data": None,
                            "timestamp": datetime.now().isoformat(),
                            "request_id": request_id
                        }
                    )
            else:
                logger.error(f"[{request_id}] 比邻平台HTTP错误: {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "code": 500,
                        "message": "比邻平台服务异常",
                        "success": False,
                        "data": None,
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id
                    }
                )

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] 比邻平台调用超时")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "比邻平台调用超时",
                "success": False,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 比邻平台调用异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "比邻平台调用失败",
                "success": False,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
        )

async def get_merchant_by_id(
        merchant_id: str,
        redis_client=Depends(get_redis_client),
        db: AsyncSession = Depends(get_async_db)
) -> Optional[Dict[str, Any]]:
    """
    根据merchant_id获取商户信息

    Args:
        merchant_id: 商户ID
        redis_client: Redis客户端
        db: 数据库会话

    Returns:
        商户信息字典或None
    """
    try:
        # 首先从Redis缓存获取
        cache_key = generate_cache_key("merchant", merchant_id)
        cached_data = await redis_client.get(cache_key)

        if cached_data:
            logger.info(f"从缓存获取商户信息: {merchant_id}")
            return json.loads(cached_data)

        # 缓存未命中，从数据库查询
        result = await db.execute(
            select(Merchant).where(Merchant.merchant_id == merchant_id)
        )
        merchant = result.scalar_one_or_none()

        if merchant:
            merchant_data = merchant.to_dict()

            # 重新缓存数据
            await redis_client.setex(
                cache_key,
                settings.CACHE_EXPIRE_TIME,
                json.dumps(merchant_data, default=str)  # default=str处理datetime序列化
            )

            logger.info(f"从数据库获取并缓存商户信息: {merchant_id}")
            return merchant_data

        logger.warning(f"未找到商户信息: {merchant_id}")
        return None

    except Exception as e:
        logger.error(f"获取商户信息失败: {str(e)}")
        return None

async def get_client_by_merchant(
        merchant_id: str,
        redis_client=Depends(get_redis_client)
) -> Optional[str]:
    """
    根据merchant_id获取对应的client_id

    Args:
        merchant_id: 商户ID
        redis_client: Redis客户端

    Returns:
        client_id或None
    """
    try:
        # 从Redis映射缓存获取
        mapping_key = generate_cache_key("merchant_mapping", merchant_id)
        cached_data = await redis_client.get(mapping_key)

        if cached_data:
            mapping_data = json.loads(cached_data)
            return mapping_data.get("client_id")

        logger.warning(f"未找到merchant_id映射: {merchant_id}")
        return None

    except Exception as e:
        logger.error(f"获取client_id映射失败: {str(e)}")
        return None

def generate_jwt_token_updated(merchant_id: str, client_id: str) -> dict:
    """
    生成JWT令牌（使用新字段名）

    Args:
        merchant_id: 商户ID
        client_id: 客户端ID（对应比邻平台的clientId）

    Returns:
        dict: 包含access_token和refresh_token的字典
    """
    try:
        current_time = datetime.utcnow()
        # JWT payload
        payload = {
            "merchant_id": merchant_id,
            "client_id": client_id,  # 使用新字段名
            "exp": current_time + timedelta(hours=settings.JWT_EXPIRE_HOURS),
            "iat": current_time,
            "nbf": current_time,
            "jti": str(uuid.uuid4()),
            "type": "access"
        }

        # 生成access token
        access_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        # 生成refresh token
        refresh_payload = payload.copy()
        refresh_payload.update({
            "exp": current_time + timedelta(days=settings.JWT_REFRESH_DAYS),
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        })
        refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        logger.info(f"JWT token生成成功，merchant_id: {merchant_id}, client_id: {client_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "refresh_expires_in": settings.JWT_REFRESH_DAYS * 24 * 3600
        }
    except Exception as e:
        logger.error(f"JWT token生成失败: {str(e)}")
        raise

# 存储回调处理器
callback_handlers = {}

async def handle_wechat_moments_callback(callback_data: CallbackData) -> Dict[str, Any]:
    """处理微信朋友圈回调"""
    logger.info("处理微信朋友圈回调")

    # 提取数据
    wx_id = callback_data.data.get('wxId', '')
    fre_wx_id = callback_data.data.get('freWxId', '')
    latest_timeline_id = callback_data.data.get('latestTimelineId', '0')

    # 检查是否有朋友圈数据
    moments_data = callback_data.data.get('moments', {})

    return {
        "status": "success",
        "message": "朋友圈回调处理成功",
        "callback_type": "wechat_moments",
        "processed_data": {
            "wxId": wx_id,
            "freWxId": fre_wx_id,
            "latestTimelineId": latest_timeline_id,
            "moments_count": len(moments_data) if isinstance(moments_data, list) else (1 if moments_data else 0),
            "timestamp": callback_data.timestamp.isoformat()
        },
        "next_actions": [
            "可以基于latestTimelineId获取更多朋友圈数据",
            "可以处理朋友圈内容分析",
            "可以触发后续的自动化操作"
        ]
    }

async def handle_wechat_friend_request(callback_data: CallbackData) -> Dict[str, Any]:
    """处理微信好友请求回调"""
    logger.info("处理微信好友请求回调")

    friend_data = callback_data.data.get('friend_request', {})
    from_user = friend_data.get('from_user')
    message = friend_data.get('message', '')

    # 自动同意好友请求的逻辑
    auto_accept = should_auto_accept_friend(from_user, message)

    return {
        "status": "success",
        "message": "好友请求回调处理成功",
        "action": "accept" if auto_accept else "pending",
        "from_user": from_user
    }


async def handle_wechat_group_message(callback_data: CallbackData) -> Dict[str, Any]:
    """处理微信群消息回调"""
    logger.info("处理微信群消息回调")

    group_data = callback_data.data.get('group_message', {})
    group_id = group_data.get('group_id')
    sender = group_data.get('sender')
    message = group_data.get('message', '')

    # 处理群消息逻辑
    response_needed = should_respond_to_group_message(message)

    return {
        "status": "success",
        "message": "群消息回调处理成功",
        "group_id": group_id,
        "sender": sender,
        "response_needed": response_needed
    }


def should_auto_accept_friend(from_user: str, message: str) -> bool:
    """判断是否自动同意好友请求"""
    # 这里可以添加你的判断逻辑
    # 例如：检查用户是否在白名单中、消息是否包含特定关键词等
    keywords = ["合作", "商务", "朋友推荐"]
    return any(keyword in message for keyword in keywords)

def should_respond_to_group_message(message: str) -> bool:
    """判断是否需要回复群消息"""
    # 这里可以添加你的判断逻辑
    # 例如：检查消息是否@了机器人、是否包含特定关键词等
    trigger_words = ["@bot", "帮助", "查询"]
    return any(word in message for word in trigger_words)


async def _execute_moments_business_logic(wx_id: str, fre_wx_id: str, timeline_id: str):
    """执行朋友圈相关的业务逻辑"""
    # 这里可以添加你的具体业务逻辑
    # 比如：
    # 1. 记录到数据库
    # 2. 触发后续API调用
    # 3. 发送通知
    # 4. 数据分析处理

    logger.info(f"执行朋友圈业务逻辑 - wxId: {wx_id}, timelineId: {timeline_id}")

    # 示例：记录获取朋友圈的操作
    operation_record = {
        "operation_type": "get_moments",
        "wx_id": wx_id,
        "friend_wx_id": fre_wx_id,
        "timeline_id": timeline_id,
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }

    # 这里可以保存到数据库或发送到消息队列
    logger.info(f"朋友圈操作记录: {operation_record}")


# 6. 监控和统计功能
class CallbackMonitor:
    """回调监控器"""

    @staticmethod
    def record_callback_metrics(callback_id: str, callback_type: str, processing_time: float):
        """记录回调指标"""
        metrics = {
            "callback_id": callback_id,
            "type": callback_type,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

        # 可以发送到监控系统
        logger.info(f"回调指标: {metrics}")

    @staticmethod
    def get_callback_statistics():
        """获取回调统计信息"""
        # 这里可以从数据库或缓存中获取统计信息
        return {
            "total_callbacks": 0,
            "success_rate": 0.0,
            "avg_processing_time": 0.0,
            "most_common_types": []
        }

async def enhanced_wechat_moments_callback(callback_data: CallbackData) -> Dict[str, Any]:
    """增强版的朋友圈回调处理器"""
    logger.info(f"处理微信朋友圈回调 - ID: {callback_data.callback_id}")

    # 提取和验证数据
    wx_id = callback_data.data.get('wxId', '')
    fre_wx_id = callback_data.data.get('freWxId', '')
    latest_timeline_id = callback_data.data.get('latestTimelineId', '0')

    # 详细日志记录
    logger.info(f"朋友圈回调详情 - wxId: {wx_id}, freWxId: {fre_wx_id}, timelineId: {latest_timeline_id}")

    # 数据验证
    if not wx_id:
        logger.warning(f"朋友圈回调缺少wxId: {callback_data.callback_id}")
        return {
            "status": "warning",
            "message": "缺少必要的wxId参数",
            "callback_type": "wechat_moments"
        }

    # 检查是否为初始请求（timelineId为"0"）
    is_initial_request = latest_timeline_id == "0"

    # 分析请求类型
    request_type = "获取自己的朋友圈" if not fre_wx_id else f"获取好友({fre_wx_id})的朋友圈"

    # 构建详细响应
    result = {
        "status": "success",
        "message": "朋友圈回调处理成功",
        "callback_type": "wechat_moments",
        "request_analysis": {
            "wx_id": wx_id,
            "friend_wx_id": fre_wx_id or "自己",
            "timeline_id": latest_timeline_id,
            "is_initial_request": is_initial_request,
            "request_type": request_type,
            "processed_at": callback_data.timestamp.isoformat()
        },
        "business_suggestions": {
            "next_steps": [
                "可以基于wxId获取用户详细信息",
                "可以继续获取更多朋友圈数据" if is_initial_request else "可以获取后续的朋友圈更新",
                "可以分析朋友圈内容和互动数据",
                "可以触发自动化营销或客服流程"
            ],
            "data_quality": "基础数据完整" if wx_id else "数据不完整，缺少wxId"
        }
    }

    # 异步执行业务逻辑（如果需要）
    try:
        await _execute_moments_business_logic(wx_id, fre_wx_id, latest_timeline_id)
    except Exception as e:
        logger.error(f"朋友圈业务逻辑执行失败: {str(e)}")
        # 不影响主流程，只记录错误

    return result


async def process_fastgpt_request(callback_data: CallbackData) -> Dict[str, Any]:
    """处理FastGPT回调请求"""
    try:
        logger.info(f"处理FastGPT回调: {callback_data.callback_id}, 类型: {callback_data.type}")

        # 首先尝试根据callback_id推断回调类型
        callback_id = callback_data.callback_id
        inferred_type = None

        # 根据callback_id模式推断类型
        if 'moments' in callback_id.lower() or 'timeline' in callback_id.lower():
            inferred_type = '6001'  # 朋友圈相关
        elif 'friend' in callback_id.lower():
            inferred_type = '3005'  # 好友相关
        elif 'group' in callback_id.lower():
            inferred_type = '20004'  # 群消息相关
        elif callback_data.data.get('wxId') or callback_data.data.get('freWxId'):
            # 如果包含微信ID，很可能是朋友圈回调
            inferred_type = '6001'

        # 使用推断的类型或原始类型
        callback_type = inferred_type or callback_data.type

        logger.info(f"推断的回调类型: {callback_type}")

        # 根据回调类型处理不同逻辑
        type_handlers = {
            '0001': handle_wechat_moments_callback,  # 读取微信朋友圈回调
            '3005': handle_wechat_friend_request,  # 微信好友请求回调
            '20004': handle_wechat_group_message,  # 微信群消息回调
            '6001': enhanced_wechat_moments_callback,  # 获取朋友圈回调
        }

        handler = type_handlers.get(callback_type)
        if handler:
            return await handler(callback_data)
        else:
            # 如果没有匹配的处理器，但有微信相关数据，使用默认处理
            if callback_data.data.get('wxId') or callback_data.data.get('freWxId'):
                logger.info(f"检测到微信数据，使用朋友圈处理器")
                return await handle_wechat_moments_callback(callback_data)

            logger.warning(f"未知回调类型: {callback_type}")
            return {
                "status": "success",
                "message": f"回调接收成功，类型: {callback_type}",
                "callback_id": callback_data.callback_id,
                "data_summary": {
                    "wxId": callback_data.data.get('wxId', ''),
                    "freWxId": callback_data.data.get('freWxId', ''),
                    "latestTimelineId": callback_data.data.get('latestTimelineId', ''),
                    "has_moments": bool(callback_data.data.get('moments')),
                    "has_friend_request": bool(callback_data.data.get('friend_request')),
                    "has_group_message": bool(callback_data.data.get('group_message'))
                }
            }

    except Exception as e:
        logger.error(f"处理回调时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理回调失败: {str(e)}")


def register_callback_handler(callback_id: str, handler):
    """注册回调处理器"""
    callback_handlers[callback_id] = handler
    logger.info(f"注册回调处理器: {callback_id}")

def unregister_callback_handler(callback_id: str):
    """注销回调处理器"""
    if callback_id in callback_handlers:
        del callback_handlers[callback_id]
        logger.info(f"注销回调处理器: {callback_id}")

