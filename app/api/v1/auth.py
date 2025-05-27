#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:48
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from fastapi import APIRouter, HTTPException, status, Request, Depends, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from datetime import datetime, timedelta
from app.core.redis import get_optional_redis_client, AsyncRedisOperations
from app.core.settings import settings
from app.schemas.RequestModel.auth import ClientCredentialsRequest, EnhancedAutoLoginRequest, CallbackData
from app.schemas.ResponseModel.auth import LoginResponse, BaseResponse
from app.utils.bilim_api import generate_jwt_token, verify_bilin_credentials, generate_callback_url, \
    build_error_response, generate_cache_key, build_success_response, process_fastgpt_request, callback_handlers
from sqlalchemy.orm import Session
from app.core.database import get_db, get_async_db
from app.models.merchant import Merchant
import uuid
import json
from app.utils.common_responses import CommonResponses
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()

# Redis缓存相关配置
CACHE_PREFIX = "auto_login"
CACHE_EXPIRE_TIME = 3600  # 1小时过期


@router.post("/verify-credentials",
             summary="验证应用凭证",
             description="通过比邻平台验证clientId和clientSecret是否正确",
             responses={
                 200: {
                     "description": "验证成功，返回商户信息和Token",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 200,
                                 "message": "凭证验证成功",
                                 "success": True,
                                 "data": {
                                     "merchant_info": {
                                         "merchant_id": "merchant_001",
                                         "client_id": "your_client_id",
                                         "callback_address": "https://yourserver.com/api/v1/auth/callback/merchant_001_xxx",
                                         "is_active": True,
                                         "is_existing": True
                                     },
                                     "auth_info": {
                                         "access_token": "jwt_token...",
                                         "refresh_token": "jwt_refresh_token...",
                                         "token_type": "Bearer",
                                         "expires_in": 7200,
                                         "refresh_expires_in": 604800
                                     },
                                     "bilin_response": {"code": 0, "message": "success"},
                                     "integration_status": "success"
                                 },
                                 "timestamp": "2025-05-27T11:30:00",
                                 "request_id": "req_1234567890"
                             }
                         }
                     }
                 }
             })
async def verify_client_credentials(
        credentials: ClientCredentialsRequest,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        redis_client=Depends(get_optional_redis_client)
):
    """
    验证客户端应用凭证接口（使用新字段名）

    功能：
    1. 接收前端传来的clientId、clientSecret和merchant_id
    2. 调用比邻平台API进行验证
    3. 检查商户是否已存在：
       - 如果存在：直接使用现有信息，更新client凭证
       - 如果不存在：创建新商户记录
    4. 将认证信息写入Redis缓存
    5. 返回包含回调地址的完整响应

    注意：字段映射关系
    - credentials.client_id -> merchants.client_id (直接存储比邻平台的clientId)
    - credentials.client_secret -> merchants.client_secret (直接存储比邻平台的clientSecret)
    """
    # 生成请求ID用于链路追踪
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 1. 基础参数验证
        client_id = credentials.client_id.strip()
        client_secret = credentials.client_secret.strip()
        merchant_id = credentials.merchant_id.strip()

        logger.info(f"[{request_id}] 开始验证客户端凭证，clientId: {client_id}, merchantId: {merchant_id}")

        # 2. 调用比邻平台验证凭证
        try:
            bilin_response = await verify_bilin_credentials(client_id, client_secret, request_id)

            # 检查比邻平台响应
            if bilin_response.get('code') != 0:  # 假设0表示成功
                error_message = bilin_response.get('message', '未知错误')
                logger.warning(f"[{request_id}] 比邻平台验证失败: {error_message}")

                return build_error_response(
                    code=bilin_response.get('code', 400),
                    message=f"比邻平台验证失败: {error_message}",
                    request_id=request_id,
                    data=bilin_response.get('data')
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[{request_id}] 调用比邻平台异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=build_error_response(500, "比邻平台调用失败", request_id)
            )

        # 3. 比邻平台验证成功，开始处理商户信息
        try:
            # 3.1 检查商户是否已存在
            from sqlalchemy import select

            stmt = select(Merchant).where(Merchant.merchant_id == merchant_id)
            result = await db.execute(stmt)
            existing_merchant = result.scalar_one_or_none()

            is_existing_merchant = existing_merchant is not None
            callback_address = None

            if existing_merchant:
                # 3.2 商户已存在，更新凭证信息
                logger.info(f"[{request_id}] 发现已存在商户: {merchant_id}")

                # 使用现有的回调地址
                callback_address = existing_merchant.callback_address

                # 更新商户的客户端凭证和时间戳
                existing_merchant.client_id = client_id  # 更新为当前的client_id
                existing_merchant.client_secret = client_secret  # 更新为当前的client_secret
                existing_merchant.updated_at = datetime.now()
                existing_merchant.is_active = True

                await db.commit()
                await db.refresh(existing_merchant)

                merchant = existing_merchant
                logger.info(f"[{request_id}] 更新现有商户凭证信息: {merchant_id}")

            else:
                # 3.3 商户不存在，创建新商户
                logger.info(f"[{request_id}] 创建新商户: {merchant_id}")

                # 生成新的回调地址
                callback_address = generate_callback_url(request, merchant_id)

                # 创建新商户记录 - 直接使用比邻平台的凭证
                merchant = Merchant(
                    merchant_id=merchant_id,
                    client_id=client_id,  # 直接存储比邻平台的client_id
                    client_secret=client_secret,  # 直接存储比邻平台的client_secret
                    callback_address=callback_address,
                    user_source="U01",
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                db.add(merchant)
                await db.commit()
                await db.refresh(merchant)

                logger.info(f"[{request_id}] 新商户创建成功: {merchant_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"[{request_id}] 数据库操作失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=build_error_response(500, "数据库操作失败", request_id)
            )

        # 4. 生成JWT令牌（使用merchant_id和client_id）
        try:
            token_data = generate_jwt_token(merchant_id, merchant.client_id)
            logger.info(f"[{request_id}] JWT令牌生成成功")
        except Exception as e:
            logger.error(f"[{request_id}] JWT令牌生成失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=build_error_response(500, "令牌生成失败", request_id)
            )

        # 5. 写入Redis缓存
        try:
            if redis_client is not None:
                # 创建异步Redis操作实例
                from app.core.redis import AsyncRedisOperations
                redis_ops = AsyncRedisOperations(redis_client)

                # 5.1 缓存商户基本信息（使用新字段名）
                merchant_cache_key = generate_cache_key("merchant", merchant_id)
                merchant_cache_data = {
                    "merchant_id": merchant_id,
                    "client_id": merchant.client_id,  # 使用新字段名
                    "client_secret": merchant.client_secret,  # 使用新字段名（缓存中保留）
                    "callback_address": callback_address,
                    "is_active": True,
                    "is_existing": is_existing_merchant,
                    "cached_at": datetime.now().isoformat()
                }

                await redis_ops.set_json(
                    merchant_cache_key,
                    merchant_cache_data,
                    settings.CACHE_EXPIRE_TIME
                )

                # 5.2 缓存认证信息（以client_id为键）
                auth_cache_key = generate_cache_key("auth", merchant.client_id)
                auth_cache_data = {
                    "merchant_id": merchant_id,
                    "client_id": merchant.client_id,
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "callback_address": callback_address,
                    "bilin_response": bilin_response,
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now().timestamp() + token_data["expires_in"])
                }

                await redis_ops.set_json(
                    auth_cache_key,
                    auth_cache_data,
                    settings.CACHE_EXPIRE_TIME
                )

                # 5.3 缓存回调地址映射
                callback_id = callback_address.split('/')[-1]
                callback_cache_key = generate_cache_key("callback", callback_id)
                callback_cache_data = {
                    "merchant_id": merchant_id,
                    "client_id": merchant.client_id,
                    "callback_address": callback_address,
                    "cached_at": datetime.now().isoformat()
                }

                await redis_ops.set_json(
                    callback_cache_key,
                    callback_cache_data,
                    settings.CACHE_EXPIRE_TIME
                )

                # 5.4 缓存merchant_id到client_id的映射
                merchant_mapping_key = generate_cache_key("merchant_mapping", merchant_id)
                mapping_data = {
                    "merchant_id": merchant_id,
                    "client_id": merchant.client_id,
                    "is_existing": is_existing_merchant,
                    "created_at": datetime.now().isoformat()
                }

                await redis_ops.set_json(
                    merchant_mapping_key,
                    mapping_data,
                    settings.CACHE_EXPIRE_TIME
                )

                logger.info(f"[{request_id}] 认证信息已缓存到Redis")
            else:
                logger.warning(f"[{request_id}] Redis不可用，跳过缓存操作")

        except Exception as e:
            logger.error(f"[{request_id}] Redis缓存操作失败: {str(e)}")
            # Redis失败不影响主流程，记录日志即可

        # 6. 构建响应数据（使用新字段名）
        response_data = {
            "merchant_info": {
                "merchant_id": merchant_id,
                "client_id": merchant.client_id,  # 返回数据库中的client_id
                "callback_address": callback_address,
                "is_active": merchant.is_active,
                "is_existing": is_existing_merchant,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
                "updated_at": merchant.updated_at.isoformat() if merchant.updated_at else None
            },
            "auth_info": {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "token_type": token_data["token_type"],
                "expires_in": token_data["expires_in"],
                "refresh_expires_in": token_data["refresh_expires_in"]
            },
            "bilin_response": bilin_response,
            "integration_status": "success"
        }

        # 根据是否为已存在商户，返回不同的消息
        response_message = (
            "凭证验证成功，商户信息已更新" if is_existing_merchant
            else "凭证验证成功，商户信息已创建"
        )

        logger.info(
            f"[{request_id}] 客户端凭证验证完成，商户ID: {merchant_id}, "
            f"客户端ID: {merchant.client_id}, 回调地址: {callback_address}, "
            f"是否已存在: {is_existing_merchant}"
        )

        # 7. 返回成功响应
        return build_success_response(
            data=response_data,
            message=response_message,
            request_id=request_id
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 验证凭证接口异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error_response(500, "系统异常，请稍后重试", request_id)
        )

@router.post("/auto-login",
             summary="自动登录",
             description="通过merchant_id进行自动登录，如果商户存在则返回token，如果不存在则缓存状态信息",
             response_model=BaseResponse[LoginResponse],
             responses={
                 200: {
                     "description": "登录成功",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 200,
                                 "message": "登录成功",
                                 "success": True,
                                 "data": {
                                     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                     "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                     "token_type": "Bearer",
                                     "expires_in": 7200,
                                     "merchant_id": "merchant001",
                                     "user_source": "U01",
                                     "callback_url": "https://api.example.com/callback",
                                     "is_registered": True,
                                     "status": "active"
                                 },
                                 "timestamp": "2025-05-26T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 202: {
                     "description": "商户未注册，状态已缓存",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 202,
                                 "message": "商户未注册，请先完成注册流程",
                                 "success": True,
                                 "data": {
                                     "merchant_id": "merchant001",
                                     "is_registered": False,
                                     "status": "unregistered",
                                     "cache_id": "cache_67890",
                                     "register_url": "/api/auth/register",
                                     "expires_at": "2025-05-26T11:30:00Z"
                                 },
                                 "timestamp": "2025-05-26T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "请求参数错误",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 400,
                                 "message": "merchant_id为必填项",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-26T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 403: {
                     "description": "账户被禁用",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 403,
                                 "message": "账户已被禁用，请联系管理员",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-26T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 }
             })
async def auto_login(
        login_data: EnhancedAutoLoginRequest,
        request: Request,
        db: Session = Depends(get_db),
        redis_client = Depends(get_optional_redis_client)
) -> BaseResponse[LoginResponse]:
    """
    自动登录接口

    业务流程：
    1. 验证merchant_id参数
    2. 在Merchant表中查询商户是否存在
    3. 如果存在：
       - 检查账户状态（是否激活）
       - 生成JWT token
       - 返回登录成功响应
    4. 如果不存在：
       - 生成缓存ID
       - 将未注册状态信息存储到Redis
       - 返回未注册状态响应

    Args:
        login_data: 登录请求数据，包含merchant_id
        request: 请求对象
        db: 数据库会话
        redis_client: Redis客户端

    Returns:
        BaseResponse[LoginResponse]: 标准响应格式
    """
    # 生成请求ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now()

    try:
        # 1. 参数验证
        if not login_data.merchant_id or not login_data.merchant_id.strip():
            logger.warning(f"[{request_id}] merchant_id参数缺失或为空")
            error_response = CommonResponses.bad_request(
                "merchant_id为必填项",
                request_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
            )

        merchant_id = login_data.merchant_id.strip()
        logger.info(f"[{request_id}] 开始处理自动登录请求，merchant_id: {merchant_id}")

        # 2. 查询商户是否存在
        merchant = db.query(Merchant).filter(
            Merchant.merchant_id == merchant_id
        ).first()

        if merchant:
            # 商户存在的情况
            logger.info(f"[{request_id}] 找到商户记录，merchant_id: {merchant_id}")

            # 3. 检查账户状态
            if not merchant.is_active:
                logger.warning(f"[{request_id}] 商户账户已被禁用，merchant_id: {merchant_id}")
                error_response = CommonResponses.forbidden(
                    "账户已被禁用，请联系管理员",
                    request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                )

            # 4. 生成JWT token
            try:
                token_data = generate_jwt_token(merchant.merchant_id, merchant.client_id)
                logger.info(f"JWT token生成成功，merchant_id: {merchant_id}")
            except Exception as e:
                logger.error(f"[{request_id}] JWT token生成失败: {str(e)}")
                error_response = CommonResponses.internal_error(
                    "token生成失败，请稍后重试",
                    request_id
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                )

            # 5. 构建成功响应
            response_data = LoginResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                merchant_id=merchant.merchant_id,
                user_source=merchant.user_source,
                callback_url=merchant.callback_address,
                is_registered=True,
                status="active",
                # 添加必需的字段
                merchant_info={
                    "merchant_id": merchant.merchant_id,
                    "client_id": getattr(merchant, 'client_id', ''),
                    "callback_address": merchant.callback_address,
                    "user_source": merchant.user_source,
                    "is_active": merchant.is_active
                },
                auth_info={
                    "login_time": timestamp.isoformat(),
                    "login_method": "auto",
                    "session_id": f"sess_{uuid.uuid4().hex[:12]}"
                },
                bilin_response=None,
                integration_status="active"
            )

            logger.info(f"[{request_id}] 商户登录成功，merchant_id: {merchant_id}")
            return CommonResponses.success(
                data=response_data,
                message="登录成功",
                request_id=request_id
            )

        else:
            # 商户不存在的情况
            logger.info(f"[{request_id}] 商户不存在，开始缓存未注册状态，merchant_id: {merchant_id}")

            # 检查是否提供了凭证信息
            if login_data.client_id and login_data.client_secret:
                # 6. 验证比邻平台凭证
                logger.info(f"[{request_id}] 开始验证比邻平台凭证并自动注册")

                client_id = login_data.client_id.strip()
                client_secret = login_data.client_secret.strip()

                # 验证凭证
                bilin_response = await verify_bilin_credentials(client_id, client_secret, request_id)

                # 7. 生成回调地址
                try:
                    callback_url = generate_callback_url(request)
                    logger.info(f"[{request_id}] 生成回调地址: {callback_url}")
                except Exception as e:
                    logger.error(f"[{request_id}] 生成回调地址失败: {str(e)}")
                    error_response = CommonResponses.internal_error(
                        "生成回调地址失败",
                        request_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                    )

                # 8. 创建新商户记录
                try:
                    new_merchant = Merchant(
                        merchant_id=merchant_id,
                        client_id=client_id,  # 使用client_id作为app_key
                        client_secret=client_secret,  # 在生产环境中应该加密存储
                        callback_address=callback_url,
                        user_source="U01",  # 比邻用户
                        is_active=True
                    )

                    db.add(new_merchant)
                    db.commit()
                    db.refresh(new_merchant)

                    logger.info(f"[{request_id}] 商户自动注册成功，merchant_id: {merchant_id}")

                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"[{request_id}] 商户注册失败，数据冲突: {str(e)}")
                    error_response = CommonResponses.bad_request(
                        "商户注册失败，可能存在重复数据",
                        request_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                    )
                except Exception as e:
                    db.rollback()
                    logger.error(f"[{request_id}] 商户注册异常: {str(e)}")
                    error_response = CommonResponses.internal_error(
                        "商户注册失败，请稍后重试",
                        request_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                    )

                # 9. 将注册信息缓存到Redis
                try:
                    cache_key = f"{CACHE_PREFIX}:registered:{merchant_id}"
                    registration_data = {
                        "merchant_id": merchant_id,
                        "app_key": client_id,
                        "callback_url": callback_url,
                        "status": "registered",
                        "registered_at": timestamp.isoformat(),
                        "bilin_response": bilin_response,
                        "request_id": request_id
                    }

                    redis_client.setex(
                        cache_key,
                        CACHE_EXPIRE_TIME,
                        json.dumps(registration_data, ensure_ascii=False)
                    )
                    logger.info(f"[{request_id}] 注册信息已缓存到Redis")
                except Exception as e:
                    logger.warning(f"[{request_id}] Redis缓存失败: {str(e)}")
                    # 缓存失败不影响业务流程

                # 10. 生成JWT token
                try:
                    token_data = generate_jwt_token(new_merchant.merchant_id, new_merchant.app_key)
                    logger.info(f"[{request_id}] 新商户JWT token生成成功")
                except Exception as e:
                    logger.error(f"[{request_id}] 新商户JWT token生成失败: {str(e)}")
                    error_response = CommonResponses.internal_error(
                        "token生成失败，请稍后重试",
                        request_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
                    )

                # 11. 构建注册成功响应
                response_data = LoginResponse(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    token_type=token_data["token_type"],
                    expires_in=token_data["expires_in"],
                    merchant_id=new_merchant.merchant_id,
                    user_source=new_merchant.user_source,
                    callback_url=new_merchant.callback_address,
                    is_registered=True,
                    status="active",
                    # 添加必需的字段
                    merchant_info={
                        "merchant_id": new_merchant.merchant_id,
                        "app_key": new_merchant.app_key,
                        "callback_address": new_merchant.callback_address,
                        "user_source": new_merchant.user_source,
                        "is_active": new_merchant.is_active
                    },
                    auth_info={
                        "login_time": timestamp.isoformat(),
                        "login_method": "auto_register",
                        "session_id": f"sess_{uuid.uuid4().hex[:12]}"
                    },
                    bilin_response=bilin_response,
                    integration_status="active"
                )

                logger.info(f"[{request_id}] 商户自动注册并登录成功，merchant_id: {merchant_id}")
                return CommonResponses.success(
                    data=response_data,
                    message="注册并登录成功",
                    request_id=request_id
                )
            else:
                # 未提供凭证信息，缓存未注册状态
                logger.info(f"[{request_id}] 商户不存在且未提供凭证，缓存未注册状态")

                # 6. 生成缓存相关信息
                cache_id = f"cache_{uuid.uuid4().hex[:12]}"
                expires_at = timestamp + timedelta(seconds=CACHE_EXPIRE_TIME)
                cache_key = f"{CACHE_PREFIX}:{merchant_id}"

                # 7. 准备缓存数据
                cache_data = {
                    "merchant_id": merchant_id,
                    "status": "unregistered",
                    "cache_id": cache_id,
                    "request_id": request_id,
                    "created_at": timestamp.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "attempt_count": 1
                }

                # 8. 检查是否已有缓存记录
                try:
                    existing_cache = redis_client.get(cache_key)
                    if existing_cache:
                        existing_data = json.loads(existing_cache.decode('utf-8'))
                        cache_data["attempt_count"] = existing_data.get("attempt_count", 0) + 1
                        logger.info(f"[{request_id}] 发现已有缓存记录，更新尝试次数: {cache_data['attempt_count']}")
                except Exception as e:
                    logger.warning(f"[{request_id}] 读取已有缓存失败: {str(e)}")

                # 9. 存储到Redis缓存
                try:
                    redis_client.setex(
                        cache_key,
                        CACHE_EXPIRE_TIME,
                        json.dumps(cache_data, ensure_ascii=False)
                    )
                    logger.info(f"[{request_id}] 未注册状态已缓存到Redis，cache_id: {cache_id}")
                except Exception as e:
                    logger.error(f"[{request_id}] Redis缓存失败: {str(e)}")
                    # 缓存失败不影响业务流程，继续执行

                # 10. 构建未注册响应
                unregistered_response = {
                    "merchant_id": merchant_id,
                    "is_registered": False,
                    "status": "unregistered",
                    "cache_id": cache_id,
                    "register_url": "/api/v1/auth/auto-login",
                    "message": "请提供client_id和client_secret进行自动注册",
                    "expires_at": expires_at.isoformat(),
                    "attempt_count": cache_data["attempt_count"]
                }

                logger.info(f"[{request_id}] 返回未注册状态响应，merchant_id: {merchant_id}")
                return BaseResponse(
                    code=202,  # 使用202状态码表示已接受但需要进一步处理
                    message="商户未注册，请先完成注册流程",
                    success=True,
                    data=unregistered_response,
                    timestamp=timestamp.isoformat(),
                    request_id=request_id
                )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 自动登录接口异常: {str(e)}", exc_info=True)
        error_response = CommonResponses.internal_error(
            "系统异常，请稍后重试",
            request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict() if hasattr(error_response, 'dict') else error_response
        )


@router.post("/callback/{callback_id}")
async def handle_callback(
        callback_id: str,
        request: Request,
        background_tasks: BackgroundTasks
):
    """统一回调处理接口"""
    try:
        # 记录请求信息
        logger.info(f"收到回调请求 - ID: {callback_id}")
        logger.info(f"请求方法: {request.method}")
        logger.info(f"请求URL: {request.url}")

        # 获取请求体
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"解析JSON失败: {str(e)}")
            # 尝试获取原始body
            raw_body = await request.body()
            logger.error(f"原始请求体: {raw_body}")
            raise HTTPException(status_code=400, detail="无效的JSON数据")

        logger.info(f"回调数据: {json.dumps(body, ensure_ascii=False, indent=2)}")

        # 创建回调数据对象
        callback_data = CallbackData(callback_id, body)

        # 验证回调ID是否存在于处理器中
        if callback_id in callback_handlers:
            logger.info(f"使用自定义处理器处理回调: {callback_id}")
            handler = callback_handlers[callback_id]
            result = await handler(callback_data)
        else:
            logger.info(f"使用默认FastGPT处理器处理回调: {callback_id}")
            result = await process_fastgpt_request(callback_data)

        # 记录处理结果
        logger.info(f"回调处理完成: {json.dumps(result, ensure_ascii=False)}")

        return {
            "code": 0,
            "callback_id": callback_id,
            "timestamp": callback_data.timestamp.isoformat(),
            "result": result,
            "message": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理回调时发生未知错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理回调失败: {str(e)}")


@router.get("/callback/{callback_id}")
async def get_callback_status(callback_id: str):
    """获取回调状态"""
    status = "active" if callback_id in callback_handlers else "inactive"
    logger.info(f"查询回调状态 - ID: {callback_id}, 状态: {status}")

    return {
        "code": 0,
        "callback_id": callback_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "message": "success"
    }