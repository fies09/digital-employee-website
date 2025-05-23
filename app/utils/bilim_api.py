#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:53
# @Author     : fany
# @Project    : PyCharm
# @File       : bilim_api.py
# @Description:
from fastapi import Request
import socket
from app.core.log import logger
from datetime import datetime, timedelta
import jwt
import hashlib
import httpx

from app.core.settings import settings


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
            port = 8000

    except Exception as e:
        logger.warning(f"获取服务器信息失败，使用默认值: {e}")
        host = "localhost"
        port = 8000

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
    # JWT payload
    payload = {
        "merchant_id": merchant_id,
        "app_key": app_key,
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
        "type": "access"
    }

    # 生成access token
    access_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # 生成refresh token (有效期更长)
    refresh_payload = payload.copy()
    refresh_payload.update({
        "exp": datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_DAYS),
        "type": "refresh"
    })
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.JWT_EXPIRE_HOURS * 3600
    }


def hash_password(password: str) -> str:
    """对密码进行哈希加密"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_callback_url(request: Request, merchant_id: str) -> str:
    """
    生成回调地址

    Args:
        request: FastAPI请求对象
        merchant_id: 商户ID

    Returns:
        str: 完整的回调地址
    """
    try:
        # 获取服务器信息
        host, port = get_server_info(request)

        # 确定协议
        protocol = "https" if request.url.scheme == "https" else "http"

        # 构建回调地址
        if (protocol == "https" and port == 443) or (protocol == "http" and port == 80):
            # 标准端口不需要显示
            callback_url = f"{protocol}://{host}/api/v1/auth/callback/{merchant_id}"
        else:
            # 非标准端口需要显示
            callback_url = f"{protocol}://{host}:{port}/api/v1/auth/callback/{merchant_id}"

        logger.info(f"为商户 {merchant_id} 生成回调地址: {callback_url}")
        return callback_url

    except Exception as e:
        logger.error(f"生成回调地址失败: {str(e)}")
        # 返回一个默认的回调地址
        return f"http://localhost:8000/api/v1/auth/callback/{merchant_id}"

