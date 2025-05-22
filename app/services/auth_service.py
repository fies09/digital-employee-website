#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:53
# @Author     : fany
# @Project    : PyCharm
# @File       : auth_service.py
# @Description:
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import timedelta
from ..models.merchant import Merchant
from ..schemas.auth import AutoRegisterRequest
from ..core.security import create_access_token, encrypt_app_secret, ACCESS_TOKEN_EXPIRE_MINUTES
from .bilin_api_service import BilinAPIService
import logging

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bilin_api = BilinAPIService()

    async def check_and_auto_login(self, merchant_id: str) -> dict:
        """
        检查商户状态并自动登录

        Returns:
            dict: {
                "need_register": bool,  # 是否需要注册
                "token": str,          # 如果已注册，返回token
                "merchant_info": dict  # 商户信息
            }
        """
        if not merchant_id or merchant_id.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="缺少merchantId参数，禁止访问"
            )

        # 查询商户
        stmt = select(Merchant).where(Merchant.merchant_id == merchant_id.strip())
        result = await self.db.execute(stmt)
        merchant = result.scalar_one_or_none()

        if not merchant:
            # 商户不存在，需要注册
            return {
                "need_register": True,
                "token": None,
                "merchant_info": None,
                "message": "商户未注册，请完成注册流程"
            }

        if not merchant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="商户账户已被禁用"
            )

        # 检查是否完成注册（有app_key和app_secret）
        if not merchant.app_key or not merchant.app_secret:
            return {
                "need_register": True,
                "token": None,
                "merchant_info": {
                    "merchant_id": merchant.merchant_id,
                    "user_source": merchant.user_source,
                    "is_registered": False
                },
                "message": "商户信息不完整，请完成注册流程"
            }

        # 已注册，生成token
        token = await self._generate_token(merchant)

        return {
            "need_register": False,
            "token": token,
            "merchant_info": {
                "merchant_id": merchant.merchant_id,
                "app_key": merchant.app_key,
                "callback_address": merchant.callback_address,
                "user_source": merchant.user_source,
                "is_registered": True
            },
            "message": "登录成功"
        }

    async def auto_register(self, merchant_id: str, register_data: AutoRegisterRequest) -> dict:
        """
        自动注册流程

        1. 验证比邻应用凭证
        2. 创建或更新商户信息
        3. 返回登录token
        """
        if not merchant_id or merchant_id.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="缺少merchantId参数，禁止访问"
            )

        merchant_id = merchant_id.strip()

        # 1. 验证比邻API凭证
        logger.info(f"开始验证商户 {merchant_id} 的比邻API凭证")
        verification_result = await self.bilin_api.verify_credentials(
            register_data.app_key,
            register_data.app_secret,
            register_data.callback_address
        )

        if not verification_result.get("success", False):
            error_msg = verification_result.get("error", "验证失败")
            error_code = verification_result.get("error_code", "UNKNOWN")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": error_msg,
                    "error_code": error_code,
                    "suggestions": self._get_error_suggestions(error_code)
                }
            )

        # 2. 检查app_key是否已被其他商户使用
        stmt = select(Merchant).where(
            Merchant.app_key == register_data.app_key,
            Merchant.merchant_id != merchant_id
        )
        result = await self.db.execute(stmt)
        existing_merchant = result.scalar_one_or_none()

        if existing_merchant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该应用key已被其他商户使用"
            )

        # 3. 创建或更新商户信息
        stmt = select(Merchant).where(Merchant.merchant_id == merchant_id)
        result = await self.db.execute(stmt)
        merchant = result.scalar_one_or_none()

        if merchant:
            # 更新现有商户
            merchant.app_key = register_data.app_key
            merchant.app_secret = encrypt_app_secret(register_data.app_secret)
            merchant.callback_address = register_data.callback_address
            merchant.is_active = True
            logger.info(f"更新商户 {merchant_id} 信息")
        else:
            # 创建新商户
            merchant = Merchant(
                merchant_id=merchant_id,
                app_key=register_data.app_key,
                app_secret=encrypt_app_secret(register_data.app_secret),
                callback_address=register_data.callback_address,
                password=None,  # U01来源用户无密码
                user_source="U01",
                is_active=True
            )
            self.db.add(merchant)
            logger.info(f"创建新商户 {merchant_id}")

        await self.db.flush()

        # 4. 生成登录token
        token = await self._generate_token(merchant)

        return {
            "success": True,
            "token": token,
            "merchant_info": {
                "merchant_id": merchant.merchant_id,
                "app_key": merchant.app_key,
                "callback_address": merchant.callback_address,
                "user_source": merchant.user_source,
                "is_registered": True
            },
            "message": "注册成功"
        }

    async def _generate_token(self, merchant: Merchant) -> str:
        """生成JWT token"""
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": merchant.merchant_id,
                "merchant_id": merchant.merchant_id,
                "user_source": merchant.user_source,
                "app_key": merchant.app_key
            },
            expires_delta=access_token_expires
        )
        return access_token

    def _get_error_suggestions(self, error_code: str) -> list:
        """根据错误代码返回建议"""
        suggestions = {
            "INVALID_CREDENTIALS": [
                "请检查应用key和密钥是否正确",
                "确认应用key和密钥来自比邻系统",
                "联系比邻系统管理员确认应用状态"
            ],
            "INVALID_CALLBACK": [
                "请登录比邻系统检查回调地址配置",
                "确保回调地址与系统生成的地址完全一致",
                "回调地址必须使用HTTPS协议"
            ],
            "TIMEOUT": [
                "请检查网络连接",
                "稍后重试",
                "如持续出现请联系技术支持"
            ]
        }
        return suggestions.get(error_code, ["请联系技术支持"])
