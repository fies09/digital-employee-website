#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/24 17:54
# @Author     : fany
# @Project    : PyCharm
# @File       : task.py
# @Description:
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.RequestModel.task import ExecutionStatus, TriggerMethod, TaskStatus, BatchOperation
from app.schemas.ResponseModel.tag import TagResponse


class TagInfo(BaseModel):
    """标签信息模型"""
    tag_id: int = Field(..., description="标签ID")
    tag_name: str = Field(..., description="标签名称")
    tag_level: Optional[int] = Field(None, description="标签层级")


class LatestExecutionInfo(BaseModel):
    """最近执行信息模型"""
    record_id: int = Field(..., description="记录ID")
    execution_status: ExecutionStatus = Field(..., description="执行状态")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration_seconds: Optional[int] = Field(None, description="执行时长（秒）")


class TaskResponse(BaseModel):
    """任务基本响应模型"""
    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    trigger_method: TriggerMethod = Field(..., description="触发方式")
    port: Optional[int] = Field(None, description="端口号")
    status: TaskStatus = Field(..., description="任务状态")
    cron_expression: Optional[str] = Field(None, description="cron表达式")
    description: Optional[str] = Field(None, description="任务描述")
    created_time: str = Field(..., description="创建时间")
    updated_time: str = Field(..., description="更新时间")

    class Config:
        schema_extra = {
            "example": {
                "task_id": 1,
                "task_name": "数据同步任务",
                "trigger_method": "定时触发",
                "port": 8080,
                "status": "active",
                "cron_expression": "0 0 2 * * ?",
                "description": "每日凌晨2点执行数据同步",
                "created_time": "2025-05-24T15:00:00Z",
                "updated_time": "2025-05-24T15:00:00Z"
            }
        }


class TaskDetailResponse(BaseModel):
    """任务详情响应模型"""
    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    trigger_method: TriggerMethod = Field(..., description="触发方式")
    port: Optional[int] = Field(None, description="端口号")
    status: TaskStatus = Field(..., description="任务状态")
    cron_expression: Optional[str] = Field(None, description="cron表达式")
    description: Optional[str] = Field(None, description="任务描述")
    created_time: str = Field(..., description="创建时间")
    updated_time: str = Field(..., description="更新时间")
    tags: List[TagInfo] = Field(default=[], description="标签列表")
    latest_execution: Optional[LatestExecutionInfo] = Field(None, description="最近执行信息")
    execution_count: Optional[int] = Field(None, description="总执行次数")
    success_count: Optional[int] = Field(None, description="成功执行次数")

    class Config:
        schema_extra = {
            "example": {
                "task_id": 1,
                "task_name": "数据同步任务",
                "trigger_method": "定时触发",
                "port": 8080,
                "status": "active",
                "cron_expression": "0 0 2 * * ?",
                "description": "每日凌晨2点执行数据同步",
                "created_time": "2025-05-24T15:00:00Z",
                "updated_time": "2025-05-24T15:00:00Z",
                "tags": [
                    {"tag_id": 1, "tag_name": "数据处理", "tag_level": 1},
                    {"tag_id": 2, "tag_name": "定时任务", "tag_level": 2}
                ],
                "latest_execution": {
                    "record_id": 123,
                    "execution_status": "completed",
                    "start_time": "2025-05-24T02:00:00Z",
                    "end_time": "2025-05-24T02:05:30Z",
                    "duration_seconds": 330
                },
                "execution_count": 30,
                "success_count": 28
            }
        }


class TaskExecutionResponse(BaseModel):
    """任务执行响应模型"""
    record_id: int = Field(..., description="执行记录ID")
    task_id: int = Field(..., description="任务ID")
    execution_status: ExecutionStatus = Field(..., description="执行状态")
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration_seconds: Optional[int] = Field(None, description="执行时长（秒）")
    message: str = Field(..., description="执行信息")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        schema_extra = {
            "example": {
                "record_id": 123,
                "task_id": 1,
                "execution_status": "running",
                "start_time": "2025-05-24T15:00:00Z",
                "end_time": None,
                "duration_seconds": None,
                "message": "任务启动成功",
                "error_message": None
            }
        }


class PaginationInfo(BaseModel):
    """分页信息模型"""
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页条数")
    total: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskDetailResponse] = Field(..., description="任务列表")
    pagination: PaginationInfo = Field(..., description="分页信息")

    class Config:
        schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": 1,
                        "task_name": "数据同步任务",
                        "trigger_method": "定时触发",
                        "port": 8080,
                        "status": "active",
                        "cron_expression": "0 0 2 * * ?",
                        "description": "每日凌晨2点执行数据同步",
                        "created_time": "2025-05-24T15:00:00Z",
                        "updated_time": "2025-05-24T15:00:00Z",
                        "tags": [
                            {"tag_id": 1, "tag_name": "数据处理", "tag_level": 1}
                        ],
                        "latest_execution": {
                            "record_id": 123,
                            "execution_status": "completed",
                            "start_time": "2025-05-24T02:00:00Z",
                            "end_time": "2025-05-24T02:05:30Z",
                            "duration_seconds": 330
                        },
                        "execution_count": 30,
                        "success_count": 28
                    }
                ],
                "pagination": {
                    "page": 1,
                    "size": 10,
                    "total": 50,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }


class TaskStatisticsResponse(BaseModel):
    """任务统计响应模型"""
    total_tasks: int = Field(..., description="任务总数")
    active_tasks: int = Field(..., description="活跃任务数")
    stopped_tasks: int = Field(..., description="停止任务数")
    total_executions: int = Field(..., description="总执行次数")
    today_executions: int = Field(..., description="今日执行次数")
    success_rate: float = Field(..., description="成功率（百分比）")
    status_distribution: Dict[str, int] = Field(..., description="状态分布")
    trigger_distribution: Dict[str, int] = Field(..., description="触发方式分布")
    execution_distribution: Dict[str, int] = Field(..., description="执行状态分布")
    statistics_period: Dict[str, Optional[str]] = Field(..., description="统计周期")

    class Config:
        schema_extra = {
            "example": {
                "total_tasks": 25,
                "active_tasks": 20,
                "stopped_tasks": 5,
                "total_executions": 1250,
                "today_executions": 35,
                "success_rate": 92.5,
                "status_distribution": {
                    "active": 20,
                    "stopped": 5
                },
                "trigger_distribution": {
                    "定时触发": 15,
                    "手动触发": 8,
                    "事件触发": 2
                },
                "execution_distribution": {
                    "completed": 1156,
                    "failed": 84,
                    "running": 10
                },
                "statistics_period": {
                    "start_date": "2025-05-01",
                    "end_date": "2025-05-24"
                }
            }
        }


class TaskRecordResponse(BaseModel):
    """任务执行记录响应模型"""
    record_id: int = Field(..., description="记录ID")
    task_id: int = Field(..., description="任务ID")
    task_name: Optional[str] = Field(None, description="任务名称")
    trigger_method: str = Field(..., description="触发方式")
    execution_status: ExecutionStatus = Field(..., description="执行状态")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration_seconds: Optional[int] = Field(None, description="执行时长（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_time: str = Field(..., description="创建时间")

    class Config:
        schema_extra = {
            "example": {
                "record_id": 123,
                "task_id": 1,
                "task_name": "数据同步任务",
                "trigger_method": "定时触发",
                "execution_status": "completed",
                "start_time": "2025-05-24T02:00:00Z",
                "end_time": "2025-05-24T02:05:30Z",
                "duration_seconds": 330,
                "error_message": None,
                "created_time": "2025-05-24T02:00:00Z"
            }
        }


class TaskRecordListResponse(BaseModel):
    """任务执行记录列表响应模型"""
    records: List[TaskRecordResponse] = Field(..., description="执行记录列表")
    pagination: PaginationInfo = Field(..., description="分页信息")
    task_info: Optional[Dict[str, Any]] = Field(None, description="任务信息（单个任务的记录时提供）")

    class Config:
        schema_extra = {
            "example": {
                "records": [
                    {
                        "record_id": 123,
                        "task_id": 1,
                        "task_name": "数据同步任务",
                        "trigger_method": "定时触发",
                        "execution_status": "completed",
                        "start_time": "2025-05-24T02:00:00Z",
                        "end_time": "2025-05-24T02:05:30Z",
                        "duration_seconds": 330,
                        "error_message": None,
                        "created_time": "2025-05-24T02:00:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "size": 10,
                    "total": 100,
                    "total_pages": 10,
                    "has_next": True,
                    "has_prev": False
                },
                "task_info": {
                    "task_id": 1,
                    "task_name": "数据同步任务"
                }
            }
        }


class BatchOperationResult(BaseModel):
    """批量操作结果模型"""
    task_id: int = Field(..., description="任务ID")
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果信息")

    class Config:
        schema_extra = {
            "example": {
                "task_id": 1,
                "success": True,
                "message": "任务启动成功"
            }
        }


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    operation: BatchOperation = Field(..., description="操作类型")
    total_count: int = Field(..., description="操作总数")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[BatchOperationResult] = Field(..., description="详细结果")

    class Config:
        schema_extra = {
            "example": {
                "operation": "start",
                "total_count": 3,
                "success_count": 2,
                "failed_count": 1,
                "results": [
                    {
                        "task_id": 1,
                        "success": True,
                        "message": "任务启动成功"
                    },
                    {
                        "task_id": 2,
                        "success": True,
                        "message": "任务启动成功"
                    },
                    {
                        "task_id": 3,
                        "success": False,
                        "message": "任务不存在"
                    }
                ]
            }
        }

# 更新模型引用，解决前向引用问题
TagResponse.model_rebuild()