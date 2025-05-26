#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/24 17:46
# @Author     : fany
# @Project    : PyCharm
# @File       : task.py
# @Description:
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


# ==================== 枚举类 ====================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    ACTIVE = "active"
    STOPPED = "stopped"
    DISABLED = "disabled"


class TriggerMethod(str, Enum):
    """触发方式枚举"""
    MANUAL = "手动触发"
    SCHEDULED = "定时触发"
    EVENT = "事件触发"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchOperation(str, Enum):
    """批量操作类型枚举"""
    START = "start"
    STOP = "stop"
    DELETE = "delete"


# ==================== 请求模型 ====================

class TaskCreateRequest(BaseModel):
    """创建任务请求模型"""
    task_name: str = Field(..., description="任务名称", min_length=1, max_length=255)
    trigger_method: TriggerMethod = Field(..., description="触发方式")
    port: Optional[int] = Field(None, description="端口号", ge=1, le=65535)
    cron_expression: Optional[str] = Field(None, description="cron表达式", max_length=100)
    tag_ids: Optional[List[int]] = Field(default=[], description="标签ID列表")
    description: Optional[str] = Field(None, description="任务描述", max_length=500)

    @validator('cron_expression')
    def validate_cron_for_scheduled_tasks(cls, v, values):
        """验证定时任务必须有cron表达式"""
        if values.get('trigger_method') == TriggerMethod.SCHEDULED and not v:
            raise ValueError('定时触发任务必须提供cron表达式')
        return v

    class Config:
        schema_extra = {
            "example": {
                "task_name": "数据同步任务",
                "trigger_method": "定时触发",
                "port": 8080,
                "cron_expression": "0 0 2 * * ?",
                "tag_ids": [1, 2],
                "description": "每日凌晨2点执行数据同步"
            }
        }


class TaskUpdateRequest(BaseModel):
    """更新任务请求模型"""
    task_name: Optional[str] = Field(None, description="任务名称", min_length=1, max_length=255)
    trigger_method: Optional[TriggerMethod] = Field(None, description="触发方式")
    port: Optional[int] = Field(None, description="端口号", ge=1, le=65535)
    cron_expression: Optional[str] = Field(None, description="cron表达式", max_length=100)
    tag_ids: Optional[List[int]] = Field(None, description="标签ID列表")
    description: Optional[str] = Field(None, description="任务描述", max_length=500)

    class Config:
        schema_extra = {
            "example": {
                "task_name": "数据同步任务V2",
                "trigger_method": "手动触发",
                "port": 8081,
                "description": "更新后的任务描述"
            }
        }


class TaskExecuteRequest(BaseModel):
    """执行任务请求模型"""
    force_execute: bool = Field(False, description="是否强制执行（即使任务已在运行）")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="执行参数")

    class Config:
        schema_extra = {
            "example": {
                "force_execute": False,
                "parameters": {
                    "batch_size": 1000,
                    "timeout": 3600
                }
            }
        }


class TaskQueryRequest(BaseModel):
    """任务查询请求模型"""
    task_name: Optional[str] = Field(None, description="任务名称（模糊查询）")
    trigger_method: Optional[TriggerMethod] = Field(None, description="触发方式")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    tag_id: Optional[int] = Field(None, description="标签ID")
    created_start: Optional[str] = Field(None, description="创建开始时间 (YYYY-MM-DD)")
    created_end: Optional[str] = Field(None, description="创建结束时间 (YYYY-MM-DD)")

    class Config:
        schema_extra = {
            "example": {
                "task_name": "数据",
                "trigger_method": "定时触发",
                "status": "active",
                "tag_id": 1
            }
        }


class TaskBatchOperationRequest(BaseModel):
    """批量操作任务请求模型"""
    operation: BatchOperation = Field(..., description="操作类型")
    task_ids: List[int] = Field(..., description="任务ID列表", min_items=1)
    force: bool = Field(False, description="是否强制执行操作")

    class Config:
        schema_extra = {
            "example": {
                "operation": "start",
                "task_ids": [1, 2, 3],
                "force": "false"
            }
        }



