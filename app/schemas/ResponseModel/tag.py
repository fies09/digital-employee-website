#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/26 09:23
# @Author     : fany
# @Project    : PyCharm
# @File       : tag.py
# @Description:
from pydantic import BaseModel, Field
from typing import List, Optional

class TagResponse(BaseModel):
    """标签响应模型"""
    tag_id: int = Field(..., description="标签ID")
    tag_name: str = Field(..., description="标签名称")
    parent_id: Optional[int] = Field(None, description="父标签ID")
    tag_level: int = Field(..., description="标签层级")
    status: str = Field(..., description="标签状态")
    description: Optional[str] = Field(None, description="标签描述")
    task_count: Optional[int] = Field(None, description="关联任务数量")
    created_time: str = Field(..., description="创建时间")
    updated_time: str = Field(..., description="更新时间")
    children: Optional[List['TagResponse']] = Field(None, description="子标签列表")

    class Config:
        schema_extra = {
            "example": {
                "tag_id": 1,
                "tag_name": "数据处理",
                "parent_id": None,
                "tag_level": 1,
                "status": "active",
                "description": "数据处理相关任务标签",
                "task_count": 5,
                "created_time": "2025-05-24T15:00:00Z",
                "updated_time": "2025-05-24T15:00:00Z",
                "children": [
                    {
                        "tag_id": 2,
                        "tag_name": "数据同步",
                        "parent_id": 1,
                        "tag_level": 2,
                        "status": "active",
                        "description": "数据同步子标签",
                        "task_count": 3,
                        "created_time": "2025-05-24T15:00:00Z",
                        "updated_time": "2025-05-24T15:00:00Z",
                        "children": None
                    }
                ]
            }
        }


# 更新模型引用，解决前向引用问题
TagResponse.model_rebuild()