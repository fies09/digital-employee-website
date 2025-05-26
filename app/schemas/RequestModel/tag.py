#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/24 17:54
# @Author     : fany
# @Project    : PyCharm
# @File       : tag.py
# @Description:
from pydantic import BaseModel, Field
from typing import Optional


class TagCreateRequest(BaseModel):
    """创建标签请求模型"""
    tag_name: str = Field(..., description="标签名称", min_length=1, max_length=100)
    parent_id: Optional[int] = Field(None, description="父标签ID")
    tag_level: Optional[int] = Field(1, description="标签层级", ge=1, le=5)
    description: Optional[str] = Field(None, description="标签描述", max_length=200)

    class Config:
        schema_extra = {
            "example": {
                "tag_name": "数据处理",
                "parent_id": None,
                "tag_level": 1,
                "description": "数据处理相关任务标签"
            }
        }


class TagUpdateRequest(BaseModel):
    """更新标签请求模型"""
    tag_name: Optional[str] = Field(None, description="标签名称", min_length=1, max_length=100)
    parent_id: Optional[int] = Field(None, description="父标签ID")
    tag_level: Optional[int] = Field(None, description="标签层级", ge=1, le=5)
    description: Optional[str] = Field(None, description="标签描述", max_length=200)

    class Config:
        schema_extra = {
            "example": {
                "tag_name": "数据处理V2",
                "description": "更新后的标签描述"
            }
        }