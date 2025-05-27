#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/27 09:04
# @Author     : fany
# @Project    : PyCharm
# @File       : common_responses.py
# @Description:
from datetime import datetime
from typing import Any, Optional, Dict, Union
import uuid


class CommonResponses:
    """通用响应处理类"""

    @staticmethod
    def _get_current_timestamp() -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()

    @staticmethod
    def _generate_request_id() -> str:
        """生成请求ID"""
        return f"req_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def success(
            data: Any = None,
            message: str = "操作成功",
            request_id: Optional[str] = None,
            code: int = 200
    ) -> Dict[str, Any]:
        """
        构建成功响应

        Args:
            data: 响应数据
            message: 响应消息
            request_id: 请求ID
            code: 状态码

        Returns:
            dict: 标准成功响应
        """
        return {
            "code": code,
            "message": message,
            "success": True,
            "data": data,
            "timestamp": CommonResponses._get_current_timestamp(),
            "request_id": request_id or CommonResponses._generate_request_id()
        }

    @staticmethod
    def error(
            message: str = "操作失败",
            code: int = 500,
            data: Optional[Dict] = None,
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建错误响应

        Args:
            message: 错误消息
            code: 错误码
            data: 错误详情
            request_id: 请求ID

        Returns:
            dict: 标准错误响应
        """
        return {
            "code": code,
            "message": message,
            "success": False,
            "data": data,
            "timestamp": CommonResponses._get_current_timestamp(),
            "request_id": request_id or CommonResponses._generate_request_id()
        }

    @staticmethod
    def bad_request(
            message: str = "请求参数错误",
            request_id: Optional[str] = None,
            validation_errors: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        构建400错误响应

        Args:
            message: 错误消息
            request_id: 请求ID
            validation_errors: 验证错误列表

        Returns:
            dict: 400错误响应
        """
        data = None
        if validation_errors:
            data = {"validation_errors": validation_errors}

        return CommonResponses.error(
            message=message,
            code=400,
            data=data,
            request_id=request_id
        )

    @staticmethod
    def unauthorized(
            message: str = "未授权访问",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建401错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 401错误响应
        """
        return CommonResponses.error(
            message=message,
            code=401,
            request_id=request_id
        )

    @staticmethod
    def forbidden(
            message: str = "禁止访问",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建403错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 403错误响应
        """
        return CommonResponses.error(
            message=message,
            code=403,
            request_id=request_id
        )

    @staticmethod
    def not_found(
            message: str = "资源不存在",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建404错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 404错误响应
        """
        return CommonResponses.error(
            message=message,
            code=404,
            request_id=request_id
        )

    @staticmethod
    def method_not_allowed(
            message: str = "请求方法不允许",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建405错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 405错误响应
        """
        return CommonResponses.error(
            message=message,
            code=405,
            request_id=request_id
        )

    @staticmethod
    def conflict(
            message: str = "资源冲突",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建409错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 409错误响应
        """
        return CommonResponses.error(
            message=message,
            code=409,
            request_id=request_id
        )

    @staticmethod
    def validation_error(
            message: str = "请求验证失败",
            validation_errors: Optional[list] = None,
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建422验证错误响应

        Args:
            message: 错误消息
            validation_errors: 验证错误列表
            request_id: 请求ID

        Returns:
            dict: 422错误响应
        """
        return CommonResponses.bad_request(
            message=message,
            request_id=request_id,
            validation_errors=validation_errors
        )

    @staticmethod
    def internal_error(
            message: str = "服务器内部错误",
            request_id: Optional[str] = None,
            error_details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        构建500错误响应

        Args:
            message: 错误消息
            request_id: 请求ID
            error_details: 错误详情

        Returns:
            dict: 500错误响应
        """
        return CommonResponses.error(
            message=message,
            code=500,
            data=error_details,
            request_id=request_id
        )

    @staticmethod
    def service_unavailable(
            message: str = "服务暂时不可用",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建503错误响应

        Args:
            message: 错误消息
            request_id: 请求ID

        Returns:
            dict: 503错误响应
        """
        return CommonResponses.error(
            message=message,
            code=503,
            request_id=request_id
        )

    @staticmethod
    def accepted(
            data: Any = None,
            message: str = "请求已接受，正在处理",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建202响应（请求已接受但需要进一步处理）

        Args:
            data: 响应数据
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 202响应
        """
        return CommonResponses.success(
            data=data,
            message=message,
            request_id=request_id,
            code=202
        )

    @staticmethod
    def created(
            data: Any = None,
            message: str = "资源创建成功",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建201响应（资源创建成功）

        Args:
            data: 响应数据
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 201响应
        """
        return CommonResponses.success(
            data=data,
            message=message,
            request_id=request_id,
            code=201
        )

    @staticmethod
    def no_content(
            message: str = "操作成功",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建204响应（无内容）

        Args:
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 204响应
        """
        return CommonResponses.success(
            data=None,
            message=message,
            request_id=request_id,
            code=204
        )

    @staticmethod
    def paginated_response(
            data: list,
            total: int,
            page: int = 1,
            page_size: int = 10,
            message: str = "查询成功",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建分页响应

        Args:
            data: 数据列表
            total: 总数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 分页响应
        """
        total_pages = (total + page_size - 1) // page_size

        paginated_data = {
            "items": data,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

        return CommonResponses.success(
            data=paginated_data,
            message=message,
            request_id=request_id
        )

    @staticmethod
    def batch_response(
            success_items: list,
            failed_items: list,
            message: str = "批量操作完成",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建批量操作响应

        Args:
            success_items: 成功项列表
            failed_items: 失败项列表
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 批量操作响应
        """
        batch_data = {
            "success_count": len(success_items),
            "failed_count": len(failed_items),
            "total_count": len(success_items) + len(failed_items),
            "success_items": success_items,
            "failed_items": failed_items
        }

        # 根据结果确定状态码
        if len(failed_items) == 0:
            code = 200  # 全部成功
        elif len(success_items) == 0:
            code = 400  # 全部失败
        else:
            code = 207  # 部分成功

        return CommonResponses.success(
            data=batch_data,
            message=message,
            request_id=request_id,
            code=code
        )

    @staticmethod
    def cache_response(
            data: Any,
            cached: bool = False,
            cache_ttl: Optional[int] = None,
            message: str = "查询成功",
            request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建带缓存信息的响应

        Args:
            data: 响应数据
            cached: 是否来自缓存
            cache_ttl: 缓存TTL（秒）
            message: 响应消息
            request_id: 请求ID

        Returns:
            dict: 带缓存信息的响应
        """
        response = CommonResponses.success(
            data=data,
            message=message,
            request_id=request_id
        )

        # 添加缓存元信息
        response["meta"] = {
            "cached": cached,
            "cache_ttl": cache_ttl,
            "generated_at": CommonResponses._get_current_timestamp()
        }

        return response