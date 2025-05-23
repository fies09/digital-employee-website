#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/23 11:01
# @Author     : fany
# @Project    : PyCharm
# @File       : base.py
# @Description:
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# 定义泛型类型
T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """
    标准API响应基类

    提供统一的响应格式，包含状态码、消息、数据等标准字段
    支持泛型，可以包装任意类型的数据
    """
    code: int = Field(
        description="状态码，200表示成功，其他表示各种错误",
        examples=[200]
    )

    message: str = Field(
        description="响应消息，描述操作结果",
        examples=["操作成功"]
    )

    success: bool = Field(
        description="操作是否成功，true表示成功，false表示失败",
        examples=[True]
    )

    data: Optional[T] = Field(
        default=None,
        description="响应数据，具体类型根据接口而定"
    )

    timestamp: str = Field(
        description="响应时间戳，ISO格式",
        examples=["2025-05-23T10:30:00Z"]
    )

    request_id: Optional[str] = Field(
        default=None,
        description="请求ID，用于链路追踪和日志关联",
        examples=["req_1716450600000"]
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 常用的响应类型别名
class SuccessResponse(BaseResponse[T], Generic[T]):
    """成功响应的便捷类"""
    code: int = 200
    success: bool = True
    message: str = "操作成功"


class ErrorResponse(BaseResponse[None]):
    """错误响应的便捷类"""
    success: bool = False
    data: None = None


# 预定义的常用响应
class CommonResponses:
    """常用响应模板"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功", request_id: str = None) -> BaseResponse:
        """成功响应"""
        return BaseResponse(
            code=200,
            message=message,
            success=True,
            data=data,
            timestamp=datetime.now().isoformat(),
            request_id=request_id
        )

    @staticmethod
    def error(code: int, message: str, request_id: str = None) -> BaseResponse:
        """错误响应"""
        return BaseResponse(
            code=code,
            message=message,
            success=False,
            data=None,
            timestamp=datetime.now().isoformat(),
            request_id=request_id
        )

    @staticmethod
    def bad_request(message: str = "请求参数错误", request_id: str = None) -> BaseResponse:
        """400错误响应"""
        return CommonResponses.error(400, message, request_id)

    @staticmethod
    def unauthorized(message: str = "未授权访问", request_id: str = None) -> BaseResponse:
        """401错误响应"""
        return CommonResponses.error(401, message, request_id)

    @staticmethod
    def forbidden(message: str = "权限不足", request_id: str = None) -> BaseResponse:
        """403错误响应"""
        return CommonResponses.error(403, message, request_id)

    @staticmethod
    def not_found(message: str = "资源不存在", request_id: str = None) -> BaseResponse:
        """404错误响应"""
        return CommonResponses.error(404, message, request_id)

    @staticmethod
    def internal_error(message: str = "服务器内部错误", request_id: str = None) -> BaseResponse:
        """500错误响应"""
        return CommonResponses.error(500, message, request_id)