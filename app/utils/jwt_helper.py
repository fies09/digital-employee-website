#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/23 14:55
# @Author     : fany
# @Project    : PyCharm
# @File       : jwt_helper.py
# @Description:
import jwt
from datetime import datetime, timedelta
from typing import Dict

from app.core.log import logger
from app.core.settings import settings


def generate_jwt_token(merchant_id: str, app_key: str) -> Dict[str, any]:
    """
    生成JWT令牌

    Args:
        merchant_id: 商户ID
        app_key: 应用Key

    Returns:
        dict: 包含access_token和refresh_token的字典
    """
    try:
        # 当前时间
        now = datetime.utcnow()

        # JWT payload（访问令牌）
        access_payload = {
            "merchant_id": merchant_id,
            "app_key": app_key,
            "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
            "iat": now,
            "type": "access",
            "jti": f"acc_{merchant_id}_{int(now.timestamp())}"  # JWT ID，用于唯一标识
        }

        # 生成access token
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # JWT payload（刷新令牌）
        refresh_payload = {
            "merchant_id": merchant_id,
            "app_key": app_key,
            "exp": now + timedelta(days=settings.JWT_REFRESH_DAYS),
            "iat": now,
            "type": "refresh",
            "jti": f"ref_{merchant_id}_{int(now.timestamp())}"  # JWT ID，用于唯一标识
        }

        # 生成refresh token
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.info(f"为商户 {merchant_id} 成功生成JWT令牌")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600  # 转换为秒
        }

    except Exception as e:
        logger.error(f"生成JWT令牌失败: {str(e)}")
        raise Exception(f"JWT令牌生成失败: {str(e)}")


def verify_jwt_token(token: str, token_type: str = "access") -> Dict[str, any]:
    """
    验证JWT令牌

    Args:
        token: JWT令牌
        token_type: 令牌类型，access 或 refresh

    Returns:
        dict: 解码后的payload

    Raises:
        jwt.ExpiredSignatureError: 令牌已过期
        jwt.InvalidTokenError: 令牌无效
    """
    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 验证令牌类型
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError(f"令牌类型错误，期望: {token_type}, 实际: {payload.get('type')}")

        logger.info(f"JWT令牌验证成功，商户: {payload.get('merchant_id')}, 类型: {token_type}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("JWT令牌已过期")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT令牌无效: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"JWT令牌验证异常: {str(e)}")
        raise jwt.InvalidTokenError(f"令牌验证失败: {str(e)}")


def refresh_access_token(refresh_token: str) -> Dict[str, any]:
    """
    使用刷新令牌生成新的访问令牌

    Args:
        refresh_token: 刷新令牌

    Returns:
        dict: 新的访问令牌信息
    """
    try:
        # 验证刷新令牌
        payload = verify_jwt_token(refresh_token, "refresh")

        merchant_id = payload.get("merchant_id")
        app_key = payload.get("app_key")

        if not merchant_id or not app_key:
            raise jwt.InvalidTokenError("刷新令牌缺少必要信息")

        # 生成新的访问令牌
        token_data = generate_jwt_token(merchant_id, app_key)

        logger.info(f"为商户 {merchant_id} 成功刷新访问令牌")

        return {
            "access_token": token_data["access_token"],
            "token_type": "Bearer",
            "expires_in": token_data["expires_in"]
        }

    except Exception as e:
        logger.error(f"刷新访问令牌失败: {str(e)}")
        raise