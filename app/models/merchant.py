#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:52
# @Author     : fany
# @Project    : PyCharm
# @File       : merchant.py
# @Description:
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(50), unique=True, nullable=False, index=True, comment="商户唯一标识")
    client_id = Column(String(100), unique=True, nullable=False, index=True, comment="客户端ID，对应比邻平台的clientId")
    client_secret = Column(String(200), nullable=False, comment="客户端密钥，对应比邻平台的clientSecret")
    callback_address = Column(String(500), unique=True, nullable=False, index=True, comment="回调地址，全局唯一")
    password = Column(String(255), nullable=True, comment="商户密码，可为空")
    user_source = Column(String(10), nullable=False, default="U01", comment="用户来源")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    def __repr__(self):
        return f"<Merchant(merchant_id='{self.merchant_id}', client_id='{self.client_id}', is_active={self.is_active})>"

    def to_dict(self):
        """转换为字典，用于API返回（排除敏感信息）"""
        return {
            "id": self.id,
            "merchant_id": self.merchant_id,
            "client_id": self.client_id,
            # "client_secret": self.client_secret,  # 敏感信息，不返回
            "callback_address": self.callback_address,
            "user_source": self.user_source,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def to_dict_with_secret(self):
        """转换为字典，包含敏感信息（仅内部使用）"""
        return {
            "id": self.id,
            "merchant_id": self.merchant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,  # 包含敏感信息
            "callback_address": self.callback_address,
            "user_source": self.user_source,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True, comment="任务ID")
    task_name = Column(String(255), nullable=False, comment="任务名称")
    trigger_method = Column(String(50), nullable=True, comment="触发方式：cron/manual/api")
    port = Column(Integer, nullable=True, comment="端口号")
    status = Column(String(20), nullable=False, default="active", comment="任务状态：active/inactive/deleted")
    created_time = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    cron_expression = Column(String(100), nullable=True, comment="cron表达式")

    # 关联关系
    records = relationship("TaskRecord", back_populates="task", cascade="all, delete-orphan")
    task_tags = relationship("TaskTagRelation", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(task_id={self.task_id}, task_name='{self.task_name}', status='{self.status}')>"

    def to_dict(self):
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "trigger_method": self.trigger_method,
            "port": self.port,
            "status": self.status,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "updated_time": self.updated_time.isoformat() if self.updated_time else None,
            "cron_expression": self.cron_expression
        }


class TaskRecord(Base):
    __tablename__ = "task_records"

    record_id = Column(Integer, primary_key=True, index=True, comment="记录ID")
    task_id = Column(Integer, ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID")
    trigger_method = Column(String(50), nullable=True, comment="触发方式")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    execution_status = Column(String(20), nullable=True, comment="执行状态：success/failed/running")
    error_message = Column(String(1000), nullable=True, comment="错误信息")
    created_time = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    # 关联关系
    task = relationship("Task", back_populates="records")

    def __repr__(self):
        return f"<TaskRecord(record_id={self.record_id}, task_id={self.task_id}, execution_status='{self.execution_status}')>"

    def to_dict(self):
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "task_id": self.task_id,
            "trigger_method": self.trigger_method,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_status": self.execution_status,
            "error_message": self.error_message,
            "created_time": self.created_time.isoformat() if self.created_time else None
        }


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True, comment="标签ID")
    tag_name = Column(String(100), nullable=False, comment="标签名称")
    parent_id = Column(Integer, ForeignKey("tags.tag_id", ondelete="SET NULL"), nullable=True, comment="父标签ID")
    tag_level = Column(Integer, nullable=False, default=1, comment="标签层级")
    status = Column(String(20), nullable=False, default="active", comment="标签状态：active/inactive")
    created_time = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 添加复合唯一约束：同一层级下标签名称不能重复
    __table_args__ = (
        UniqueConstraint('tag_name', 'parent_id', name='uk_tag_name_parent'),
    )

    # 自关联关系
    parent = relationship("Tag", remote_side=[tag_id], backref="children")
    # 关联关系
    task_tags = relationship("TaskTagRelation", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tag(tag_id={self.tag_id}, tag_name='{self.tag_name}', tag_level={self.tag_level})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "tag_id": self.tag_id,
            "tag_name": self.tag_name,
            "parent_id": self.parent_id,
            "tag_level": self.tag_level,
            "status": self.status,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "updated_time": self.updated_time.isoformat() if self.updated_time else None
        }


class TaskTagRelation(Base):
    __tablename__ = "task_tag_relations"

    relation_id = Column(Integer, primary_key=True, index=True, comment="关系ID")
    task_id = Column(Integer, ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID")
    tag_id = Column(Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), nullable=False, index=True, comment="标签ID")
    created_time = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    # 添加复合唯一约束：防止同一任务关联同一标签多次
    __table_args__ = (
        UniqueConstraint('task_id', 'tag_id', name='uk_task_tag_relation'),
    )

    # 关联关系
    task = relationship("Task", back_populates="task_tags")
    tag = relationship("Tag", back_populates="task_tags")

    def __repr__(self):
        return f"<TaskTagRelation(relation_id={self.relation_id}, task_id={self.task_id}, tag_id={self.tag_id})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "relation_id": self.relation_id,
            "task_id": self.task_id,
            "tag_id": self.tag_id,
            "created_time": self.created_time.isoformat() if self.created_time else None
        }