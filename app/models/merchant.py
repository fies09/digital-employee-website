#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:52
# @Author     : fany
# @Project    : PyCharm
# @File       : merchant.py
# @Description:
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(50), unique=True, nullable=False, index=True)
    app_key = Column(String(100))
    app_secret = Column(String(200))  # 加密存储
    callback_address = Column(String(500))
    password = Column(String(255))  # 可为空
    user_source = Column(String(10), default="U01")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Merchant(merchant_id='{self.merchant_id}', user_source='{self.user_source}')>"


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    trigger_method = Column(String(50))  # 触发方式
    port = Column(Integer)
    status = Column(String(20), default="active")
    created_time = Column(DateTime, server_default=func.now())
    updated_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    cron_expression = Column(String(100))  # cron表达式

    # 关联关系
    records = relationship("TaskRecord", back_populates="task")
    task_tags = relationship("TaskTagRelation", back_populates="task")

    def __repr__(self):
        return f"<Task(task_id={self.task_id}, task_name='{self.task_name}', status='{self.status}')>"


class TaskRecord(Base):
    __tablename__ = "task_records"

    record_id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False, index=True)
    trigger_method = Column(String(50))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    execution_status = Column(String(20))  # 执行状态
    created_time = Column(DateTime, server_default=func.now())

    # 关联关系
    task = relationship("Task", back_populates="records")

    def __repr__(self):
        return f"<TaskRecord(record_id={self.record_id}, task_id={self.task_id}, execution_status='{self.execution_status}')>"


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True)
    tag_name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("tags.tag_id"), nullable=True)  # 自关联父标签
    tag_level = Column(Integer, default=1)  # 标签层级
    status = Column(String(20), default="active")
    created_time = Column(DateTime, server_default=func.now())
    updated_time = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 自关联关系
    parent = relationship("Tag", remote_side=[tag_id], backref="children")
    # 关联关系
    task_tags = relationship("TaskTagRelation", back_populates="tag")

    def __repr__(self):
        return f"<Tag(tag_id={self.tag_id}, tag_name='{self.tag_name}', tag_level={self.tag_level})>"


class TaskTagRelation(Base):
    __tablename__ = "task_tag_relations"

    relation_id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.tag_id"), nullable=False, index=True)
    created_time = Column(DateTime, server_default=func.now())

    # 关联关系
    task = relationship("Task", back_populates="task_tags")
    tag = relationship("Tag", back_populates="task_tags")

    def __repr__(self):
        return f"<TaskTagRelation(relation_id={self.relation_id}, task_id={self.task_id}, tag_id={self.tag_id})>"