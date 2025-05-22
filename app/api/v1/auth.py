#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:48
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.database import get_db
from ...core.security import verify_token
from ...services.auth_service import AuthService
from ...schemas.auth import Token, AutoRegisterRequest, MerchantInfo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()


async def get_current_merchant(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> str:
    """获取当前商户ID的依赖项"""
    payload = verify_token(credentials.credentials)
    merchant_id = payload.get("merchant_id")

    if merchant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证信息"
        )

    return merchant_id


@router.get("/check", summary="检查商户状态并自动登录")
async def check_merchant_status(
        merchantId: str = Query(..., description="商户ID", alias="merchantId"),
        db: AsyncSession = Depends(get_db)
):
    """
    检查商户状态的统一入口

    - 如果商户未注册或信息不完整，返回need_register=true
    - 如果商户已注册且信息完整，直接返回登录token

    这是iframe集成的主要入口点
    """
    auth_service = AuthService(db)

    try:
        result = await auth_service.check_and_auto_login(merchantId)

        if result["need_register"]:
            return {
                "need_register": True,
                "message": result["message"],
                "merchant_info": result.get("merchant_info"),
                "callback_address": f"https://your-domain.com/api/callback/{merchantId}"  # 系统生成的回调地址
            }
        else:
            return {
                "need_register": False,
                "access_token": result["token"],
                "token_type": "bearer",
                "expires_in": 3600 * 24,
                "message": result["message"],
                "merchant_info": result["merchant_info"]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查商户状态异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系统异常，请稍后重试"
        )


@router.post("/register", response_model=Token, summary="自动注册接口")
async def auto_register(
        register_data: AutoRegisterRequest,
        merchantId: str = Query(..., description="商户ID", alias="merchantId"),
        db: AsyncSession = Depends(get_db)
):
    """
    自动注册接口

    业务流程：
    1. 验证比邻应用key和密钥
    2. 验证回调地址配置
    3. 创建或更新商户信息
    4. 返回登录token
    """
    auth_service = AuthService(db)

    try:
        result = await auth_service.auto_register(merchantId, register_data)

        return {
            "access_token": result["token"],
            "token_type": "bearer",
            "expires_in": 3600 * 24
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动注册异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册服务异常，请稍后重试"
        )


@router.get("/", summary="兼容原接口的自动登录")
async def auto_login_legacy(
        merchantId: str = Query(..., description="商户ID", alias="merchantId"),
        db: AsyncSession = Depends(get_db)
):
    """
    兼容原有接口的自动登录
    重定向到新的check接口
    """
    return await check_merchant_status(merchantId, db)


@router.get("/me", response_model=MerchantInfo, summary="获取当前商户信息")
async def get_current_merchant_info(
        current_merchant_id: str = Depends(get_current_merchant),
        db: AsyncSession = Depends(get_db)
):
    """获取当前登录商户的详细信息"""
    auth_service = AuthService(db)
    result = await auth_service.check_and_auto_login(current_merchant_id)

    if result["need_register"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="商户信息不完整"
        )

    return result["merchant_info"]


@router.post("/refresh", response_model=Token, summary="刷新访问令牌")
async def refresh_token(
        current_merchant_id: str = Depends(get_current_merchant),
        db: AsyncSession = Depends(get_db)
):
    """刷新当前用户的访问令牌"""
    auth_service = AuthService(db)
    result = await auth_service.check_and_auto_login(current_merchant_id)

    if result["need_register"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="商户信息不完整，无法刷新令牌"
        )

    return {
        "access_token": result["token"],
        "token_type": "bearer",
        "expires_in": 3600 * 24
    }


@router.get("/callback/{merchant_id}", summary="系统回调地址")
async def system_callback(merchant_id: str):
    """
    系统生成的回调地址
    用于比邻系统的回调配置
    """
    return {
        "message": f"这是商户 {merchant_id} 的系统回调地址",
        "merchant_id": merchant_id,
        "timestamp": "2025-05-22T00:00:00Z"
    }
