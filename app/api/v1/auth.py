#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:48
# @Author     : fany
# @Project    : PyCharm
# @File       : auth.py
# @Description:
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer
import logging
from datetime import datetime
from app.schemas.RequestModel.auth import CallbackRequest, AutoLoginRequest
from app.schemas.ResponseModel.auth import CallbackResponse, LoginResponse
from app.schemas.ResponseModel.base import BaseResponse, CommonResponses
from app.utils.bilim_api import get_server_info, generate_jwt_token
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.merchant import Merchant
from sqlalchemy.exc import IntegrityError
from app.utils.bilim_api import generate_callback_url as generate_callback_url_util


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()


@router.post("/callback",
             summary="生成回调地址",
             response_model=BaseResponse[CallbackResponse],
             responses={
                 200: {
                     "description": "成功生成回调地址",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 200,
                                 "message": "操作成功",
                                 "success": True,
                                 "data": {
                                     "callback_url": "https://api.example.com/api/auth/callback/merchant001",
                                     "merchant_id": "merchant001",
                                     "message": "商户 merchant001 的回调地址已生成"
                                 },
                                 "timestamp": "2025-05-23T10:30:00Z",
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
                                 "message": "请求参数错误",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-23T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 500: {
                     "description": "服务器内部错误",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 500,
                                 "message": "生成回调地址失败，请稍后重试",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-23T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 }
             })
async def generate_callback_url(
        callback_data: CallbackRequest,
        request: Request
) -> BaseResponse[CallbackResponse]:
    """
    生成商户回调地址

    业务说明：
    - 为指定商户生成唯一的回调地址
    - 回调地址格式：http(s)://ip:port/api/auth/callback/{merchant_id}
    - 返回标准格式的响应，包含状态码、消息等完整信息

    参数:
        callback_data: 回调请求数据，包含merchant_id等信息
        request: 请求对象，用于获取服务器信息

    返回:
        BaseResponse[CallbackResponse]: 标准格式的响应对象

    异常:
        HTTPException: 当参数验证失败或服务器错误时抛出
    """
    # 生成请求ID用于链路追踪
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 参数验证
        if not callback_data.merchant_id or not callback_data.merchant_id.strip():
            logger.warning(f"[{request_id}] 商户ID为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": "商户ID不能为空",
                    "success": False,
                    "data": None,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id
                }
            )

        merchant_id = callback_data.merchant_id.strip()

        # 获取当前服务的IP和端口
        host, port = get_server_info(request)

        # 构建回调地址
        protocol = "https" if request.url.scheme == "https" else "http"
        callback_url = f"{protocol}://{host}:{port}/api/auth/callback/{merchant_id}"

        logger.info(f"[{request_id}] 为商户 {merchant_id} 生成回调地址: {callback_url}")

        # 构建响应数据
        callback_response = CallbackResponse(
            callback_url=callback_url,
            merchant_id=merchant_id,
            message=f"商户 {merchant_id} 的回调地址已生成"
        )

        # 返回标准格式响应
        return BaseResponse[CallbackResponse](
            code=200,
            message="操作成功",
            success=True,
            data=callback_response,
            timestamp=datetime.now().isoformat(),
            request_id=request_id
        )

    except HTTPException:
        # 重新抛出HTTP异常，保持原有的错误处理逻辑
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 生成回调地址异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "生成回调地址失败，请稍后重试",
                "success": False,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
        )


@router.post("/auto-login",
             summary="自动注册/登录",
             description="通过app_key和app_secret自动注册和登录，如果用户未注册则自动注册并生成回调地址",
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
                                     "callback_url": "https://api.example.com/api/auth/callback/merchant001",
                                     "is_new_user": False
                                 },
                                 "timestamp": "2025-05-23T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "请求参数错误或应用验证失败",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 400,
                                 "message": "应用key或密钥错误，请检查后重试",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-23T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 },
                 500: {
                     "description": "服务器内部错误",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 500,
                                 "message": "注册失败，请稍后重试",
                                 "success": False,
                                 "data": None,
                                 "timestamp": "2025-05-23T10:30:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 }
             })
async def auto_register_login(
        login_data: AutoLoginRequest,
        request: Request,
        db: Session = Depends(get_db)
) -> BaseResponse[LoginResponse]:
    """
    自动注册/登录接口

    业务流程：
    1. 通过app_key和app_secret在数据库中查询用户是否存在
    2. 如果存在且有callback_address，直接使用现有信息生成JWT令牌
    3. 如果存在但没有callback_address，通过merchant_id生成回调地址并更新数据库
    4. 如果不存在，通过merchant_id生成回调地址，创建新用户并生成JWT令牌
    5. 返回JWT令牌和相关信息

    Args:
        login_data: 登录请求数据，包含merchant_id、app_key、app_secret
        request: 请求对象，用于生成回调地址
        db: 数据库会话

    Returns:
        BaseResponse[LoginResponse]: 包含JWT令牌的标准响应
    """
    # 生成请求ID
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 参数验证
        if not all([login_data.merchant_id, login_data.app_key, login_data.app_secret]):
            logger.warning(f"[{request_id}] 必要参数缺失")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "merchant_id、app_key、app_secret为必填项",
                    request_id
                ).dict()
            )

        merchant_id = login_data.merchant_id.strip()
        app_key = login_data.app_key.strip()
        app_secret = login_data.app_secret.strip()

        # 1. 通过app_key和app_secret查询用户是否存在
        logger.info(f"[{request_id}] 通过app_key查询用户: {app_key}")
        existing_merchant = db.query(Merchant).filter(
            Merchant.app_key == app_key,
            Merchant.app_secret == app_secret
        ).first()

        is_new_user = False
        callback_url_generated = False

        if existing_merchant:
            # 用户已存在，检查账户状态
            logger.info(f"[{request_id}] 找到已存在用户: {existing_merchant.merchant_id}")

            # 检查用户状态
            if not existing_merchant.is_active:
                logger.warning(f"[{request_id}] 用户 {existing_merchant.merchant_id} 账户已被禁用")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "账户已被禁用，请联系管理员",
                        request_id
                    ).dict()
                )

            # 检查是否存在回调地址
            if not existing_merchant.callback_address:
                logger.info(f"[{request_id}] 用户 {existing_merchant.merchant_id} 缺少回调地址，开始生成")

                # 通过merchant_id生成回调地址
                callback_url = generate_callback_url_util(request, existing_merchant.merchant_id)

                # 更新数据库中的回调地址
                try:
                    existing_merchant.callback_address = callback_url
                    db.commit()
                    db.refresh(existing_merchant)
                    callback_url_generated = True
                    logger.info(
                        f"[{request_id}] 已为用户 {existing_merchant.merchant_id} 生成并保存回调地址: {callback_url}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"[{request_id}] 更新回调地址失败: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=CommonResponses.internal_error(
                            "更新回调地址失败，请稍后重试",
                            request_id
                        ).dict()
                    )
            else:
                logger.info(
                    f"[{request_id}] 用户 {existing_merchant.merchant_id} 已有回调地址: {existing_merchant.callback_address}")

            merchant = existing_merchant

        else:
            # 用户不存在，创建新用户
            logger.info(f"[{request_id}] 用户不存在，开始自动注册流程，merchant_id: {merchant_id}")
            is_new_user = True

            # 验证merchant_id是否已被其他应用占用
            existing_merchant_id = db.query(Merchant).filter(
                Merchant.merchant_id == merchant_id
            ).first()

            if existing_merchant_id:
                logger.warning(f"[{request_id}] merchant_id {merchant_id} 已被其他应用占用")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        f"商户ID {merchant_id} 已被占用，请使用其他商户ID",
                        request_id
                    ).dict()
                )

            # 生成回调地址
            callback_url = generate_callback_url_util(request, merchant_id)
            callback_url_generated = True

            # 创建新用户记录
            try:
                new_merchant = Merchant(
                    merchant_id=merchant_id,
                    app_key=app_key,
                    app_secret=app_secret,  # 在生产环境中应该加密存储
                    callback_address=callback_url,
                    user_source="U01",  # 比邻用户
                    is_active=True
                )

                db.add(new_merchant)
                db.commit()
                db.refresh(new_merchant)

                merchant = new_merchant
                logger.info(f"[{request_id}] 用户 {merchant_id} 自动注册成功")

            except IntegrityError as e:
                db.rollback()
                logger.error(f"[{request_id}] 用户注册失败，可能存在重复数据: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "用户注册失败，数据冲突",
                        request_id
                    ).dict()
                )
            except Exception as e:
                db.rollback()
                logger.error(f"[{request_id}] 用户注册异常: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=CommonResponses.internal_error(
                        "注册失败，请稍后重试",
                        request_id
                    ).dict()
                )

        # 2. 生成JWT令牌（使用数据库中的实际信息）
        token_data = generate_jwt_token(merchant.merchant_id, merchant.app_key)

        # 3. 构建响应数据
        response_data = LoginResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            merchant_id=merchant.merchant_id,
            user_source=merchant.user_source,
            callback_url=merchant.callback_address,
            is_new_user=is_new_user
        )

        # 4. 构建成功响应消息
        if is_new_user:
            action = "注册并登录"
        elif callback_url_generated:
            action = "登录并生成回调地址"
        else:
            action = "登录"

        logger.info(f"[{request_id}] 用户 {merchant.merchant_id} {action}成功")

        return CommonResponses.success(
            data=response_data,
            message=f"{action}成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 自动登录接口异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "系统异常，请稍后重试",
                request_id
            ).dict()
        )