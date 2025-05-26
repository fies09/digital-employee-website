#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:49
# @Author     : fany
# @Project    : PyCharm
# @File       : merchant.py
# @Description:
# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/24 15:00
# @Author     : fany
# @Project    : PyCharm
# @File       : task.py
# @Description: 任务管理相关API接口

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi import status
from fastapi.security import HTTPBearer
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from app.core.database import get_db
from app.models.merchant import Task, TaskRecord, Tag, TaskTagRelation
from app.schemas.RequestModel.task import TaskCreateRequest, TaskUpdateRequest, TaskBatchOperationRequest
from app.schemas.ResponseModel.task import (
    TaskResponse, TaskDetailResponse, TaskListResponse,
    TaskExecutionResponse, TaskStatisticsResponse
)
from app.schemas.ResponseModel.base import BaseResponse, CommonResponses
from app.utils.task import validate_cron_expression, TaskExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/task", tags=["任务管理"])
security = HTTPBearer()


@router.post("/create",
             summary="创建新任务",
             description="创建一个新的任务，支持定时任务和手动任务",
             response_model=BaseResponse[TaskResponse],
             responses={
                 200: {
                     "description": "任务创建成功",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 200,
                                 "message": "任务创建成功",
                                 "success": True,
                                 "data": {
                                     "task_id": 1,
                                     "task_name": "数据同步任务",
                                     "trigger_method": "定时触发",
                                     "port": 8080,
                                     "status": "active",
                                     "cron_expression": "0 0 2 * * ?",
                                     "created_time": "2025-05-24T15:00:00Z",
                                     "updated_time": "2025-05-24T15:00:00Z"
                                 },
                                 "timestamp": "2025-05-24T15:00:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 }
             })
async def create_task(
        task_data: TaskCreateRequest,
        db: Session = Depends(get_db),
) -> BaseResponse[TaskResponse]:
    """
    创建新任务

    业务流程：
    1. 验证任务名称的唯一性
    2. 验证cron表达式的合法性（如果是定时任务）
    3. 创建任务记录
    4. 如果指定了标签，建立任务标签关联
    5. 返回创建结果
    """
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 参数验证
        if not task_data.task_name or not task_data.task_name.strip():
            logger.warning(f"[{request_id}] 任务名称不能为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "任务名称不能为空",
                    request_id
                ).dict()
            )

        # 检查任务名称是否已存在
        existing_task = db.query(Task).filter(
            Task.task_name == task_data.task_name.strip()
        ).first()

        if existing_task:
            logger.warning(f"[{request_id}] 任务名称已存在: {task_data.task_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    f"任务名称 '{task_data.task_name}' 已存在",
                    request_id
                ).dict()
            )

        # 验证cron表达式（如果是定时任务）
        if task_data.trigger_method == "定时触发" and task_data.cron_expression:
            if not validate_cron_expression(task_data.cron_expression):
                logger.warning(f"[{request_id}] 无效的cron表达式: {task_data.cron_expression}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "cron表达式格式不正确",
                        request_id
                    ).dict()
                )

        # 创建任务
        new_task = Task(
            task_name=task_data.task_name.strip(),
            trigger_method=task_data.trigger_method,
            port=task_data.port,
            status="active",
            cron_expression=task_data.cron_expression
        )

        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # 处理标签关联
        if task_data.tag_ids:
            for tag_id in task_data.tag_ids:
                # 验证标签是否存在
                tag_exists = db.query(Tag).filter(Tag.tag_id == tag_id).first()
                if tag_exists:
                    tag_relation = TaskTagRelation(
                        task_id=new_task.task_id,
                        tag_id=tag_id
                    )
                    db.add(tag_relation)

            db.commit()

        logger.info(f"[{request_id}] 任务创建成功，任务ID: {new_task.task_id}")

        # 构建响应数据
        task_response = TaskResponse(
            task_id=new_task.task_id,
            task_name=new_task.task_name,
            trigger_method=new_task.trigger_method,
            port=new_task.port,
            status=new_task.status,
            cron_expression=new_task.cron_expression,
            created_time=new_task.created_time.isoformat(),
            updated_time=new_task.updated_time.isoformat()
        )

        return CommonResponses.success(
            data=task_response,
            message="任务创建成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 创建任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "创建任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.put("/{task_id}",
            summary="更新任务",
            description="更新指定任务的信息",
            response_model=BaseResponse[TaskResponse])
async def update_task(
        task_id: int,
        task_data: TaskUpdateRequest,
        db: Session = Depends(get_db),
) -> BaseResponse[TaskResponse]:
    """更新任务信息"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找任务
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            logger.warning(f"[{request_id}] 任务不存在，task_id: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 更新任务信息
        if task_data.task_name and task_data.task_name.strip():
            # 检查新名称是否与其他任务冲突
            existing_task = db.query(Task).filter(
                and_(
                    Task.task_name == task_data.task_name.strip(),
                    Task.task_id != task_id
                )
            ).first()

            if existing_task:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        f"任务名称 '{task_data.task_name}' 已被其他任务使用",
                        request_id
                    ).dict()
                )

            task.task_name = task_data.task_name.strip()

        if task_data.trigger_method:
            task.trigger_method = task_data.trigger_method

        if task_data.port:
            task.port = task_data.port

        if task_data.cron_expression:
            # 验证cron表达式
            if not validate_cron_expression(task_data.cron_expression):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "cron表达式格式不正确",
                        request_id
                    ).dict()
                )
            task.cron_expression = task_data.cron_expression

        db.commit()
        db.refresh(task)

        logger.info(f"[{request_id}] 任务更新成功，task_id: {task_id}")

        # 构建响应数据
        task_response = TaskResponse(
            task_id=task.task_id,
            task_name=task.task_name,
            trigger_method=task.trigger_method,
            port=task.port,
            status=task.status,
            cron_expression=task.cron_expression,
            created_time=task.created_time.isoformat(),
            updated_time=task.updated_time.isoformat()
        )

        return CommonResponses.success(
            data=task_response,
            message="任务更新成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 更新任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "更新任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.post("/{task_id}/start",
             summary="启动任务",
             description="启动指定的任务",
             response_model=BaseResponse[TaskExecutionResponse])
async def start_task(
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[TaskExecutionResponse]:
    """启动任务"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找任务
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 检查任务状态
        if task.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    f"任务状态为 {task.status}，无法启动",
                    request_id
                ).dict()
            )

        # 创建执行记录
        execution_record = TaskRecord(
            task_id=task_id,
            trigger_method="手动执行",
            start_time=datetime.now(),
            execution_status="running"
        )
        db.add(execution_record)
        db.commit()
        db.refresh(execution_record)

        # 执行任务（这里需要根据实际业务逻辑实现）
        try:
            task_executor = TaskExecutor()
            result = await task_executor.execute_task(task)

            # 更新执行记录
            execution_record.end_time = datetime.now()
            execution_record.execution_status = "completed"
            db.commit()

            logger.info(f"[{request_id}] 任务执行成功，task_id: {task_id}")

        except Exception as exec_error:
            # 更新执行记录为失败状态
            execution_record.end_time = datetime.now()
            execution_record.execution_status = "failed"
            db.commit()

            logger.error(f"[{request_id}] 任务执行失败，task_id: {task_id}, error: {str(exec_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=CommonResponses.internal_error(
                    "任务执行失败",
                    request_id
                ).dict()
            )

        # 构建响应数据
        execution_response = TaskExecutionResponse(
            record_id=execution_record.record_id,
            task_id=task_id,
            execution_status=execution_record.execution_status,
            start_time=execution_record.start_time.isoformat(),
            end_time=execution_record.end_time.isoformat() if execution_record.end_time else None,
            message="任务启动成功"
        )

        return CommonResponses.success(
            data=execution_response,
            message="任务启动成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 启动任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "启动任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.post("/{task_id}/stop",
             summary="停止任务",
             description="停止指定的任务",
             response_model=BaseResponse[dict])
async def stop_task(
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """停止任务"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找任务
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 更新任务状态为停止
        task.status = "stopped"
        db.commit()

        # 停止正在运行的任务实例（这里需要根据实际业务逻辑实现）
        try:
            task_executor = TaskExecutor()
            await task_executor.stop_task(task_id)

            logger.info(f"[{request_id}] 任务停止成功，task_id: {task_id}")

        except Exception as stop_error:
            logger.warning(f"[{request_id}] 停止任务实例时出现警告，task_id: {task_id}, error: {str(stop_error)}")

        return CommonResponses.success(
            data={"task_id": task_id, "status": "stopped"},
            message="任务已停止",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 停止任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "停止任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.delete("/{task_id}",
               summary="删除任务",
               description="删除指定的任务及其相关记录",
               response_model=BaseResponse[dict])
async def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """删除任务"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找任务
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 检查任务是否正在运行
        running_records = db.query(TaskRecord).filter(
            and_(
                TaskRecord.task_id == task_id,
                TaskRecord.execution_status == "running"
            )
        ).first()

        if running_records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "任务正在运行中，请先停止任务后再删除",
                    request_id
                ).dict()
            )

        # 删除相关记录
        # 1. 删除任务标签关联
        db.query(TaskTagRelation).filter(TaskTagRelation.task_id == task_id).delete()

        # 2. 删除任务执行记录
        db.query(TaskRecord).filter(TaskRecord.task_id == task_id).delete()

        # 3. 删除任务本身
        db.delete(task)
        db.commit()

        logger.info(f"[{request_id}] 任务删除成功，task_id: {task_id}")

        return CommonResponses.success(
            data={"task_id": task_id, "deleted": True},
            message="任务删除成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 删除任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "删除任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/list",
            summary="获取任务列表",
            description="分页获取任务列表，支持多条件筛选",
            response_model=BaseResponse[TaskListResponse])
async def get_task_list(
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(10, ge=1, le=100, description="每页条数"),
        task_name: Optional[str] = Query(None, description="任务名称（模糊查询）"),
        trigger_method: Optional[str] = Query(None, description="触发方式"),
        status: Optional[str] = Query(None, description="任务状态"),
        tag_id: Optional[int] = Query(None, description="标签ID"),
        db: Session = Depends(get_db),
) -> BaseResponse[TaskListResponse]:
    """获取任务列表"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 构建查询条件
        query = db.query(Task)

        # 任务名称模糊查询
        if task_name:
            query = query.filter(Task.task_name.like(f"%{task_name}%"))

        # 触发方式筛选
        if trigger_method:
            query = query.filter(Task.trigger_method == trigger_method)

        # 状态筛选
        if status:
            query = query.filter(Task.status == status)

        # 标签筛选
        if tag_id:
            query = query.join(TaskTagRelation).filter(TaskTagRelation.tag_id == tag_id)

        # 获取总数
        total = query.count()

        # 分页查询
        tasks = query.options(joinedload(Task.task_tags).joinedload(TaskTagRelation.tag)) \
            .order_by(desc(Task.created_time)) \
            .offset((page - 1) * size) \
            .limit(size) \
            .all()

        # 构建响应数据
        task_list = []
        for task in tasks:
            # 获取标签信息
            tags = [relation.tag for relation in task.task_tags]

            # 获取最近的执行记录
            latest_record = db.query(TaskRecord).filter(TaskRecord.task_id == task.task_id) \
                .order_by(desc(TaskRecord.created_time)) \
                .first()

            task_detail = TaskDetailResponse(
                task_id=task.task_id,
                task_name=task.task_name,
                trigger_method=task.trigger_method,
                port=task.port,
                status=task.status,
                cron_expression=task.cron_expression,
                created_time=task.created_time.isoformat(),
                updated_time=task.updated_time.isoformat(),
                tags=[{"tag_id": tag.tag_id, "tag_name": tag.tag_name} for tag in tags],
                latest_execution=None if not latest_record else {
                    "record_id": latest_record.record_id,
                    "execution_status": latest_record.execution_status,
                    "start_time": latest_record.start_time.isoformat() if latest_record.start_time else None,
                    "end_time": latest_record.end_time.isoformat() if latest_record.end_time else None
                }
            )
            task_list.append(task_detail)

        # 分页信息
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = TaskListResponse(
            tasks=task_list,
            pagination={
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        )

        logger.info(f"[{request_id}] 获取任务列表成功，返回 {len(task_list)} 条记录")

        return CommonResponses.success(
            data=response_data,
            message="获取任务列表成功",
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"[{request_id}] 获取任务列表异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取任务列表失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/{task_id}",
            summary="获取任务详情",
            description="获取指定任务的详细信息",
            response_model=BaseResponse[TaskDetailResponse])
async def get_task_detail(
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[TaskDetailResponse]:
    """获取任务详情"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找任务
        task = db.query(Task).options(
            joinedload(Task.task_tags).joinedload(TaskTagRelation.tag)
        ).filter(Task.task_id == task_id).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 获取标签信息
        tags = [{"tag_id": relation.tag.tag_id, "tag_name": relation.tag.tag_name}
                for relation in task.task_tags]

        # 获取最近的执行记录
        latest_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id) \
            .order_by(desc(TaskRecord.created_time)) \
            .first()

        # 构建响应数据
        task_detail = TaskDetailResponse(
            task_id=task.task_id,
            task_name=task.task_name,
            trigger_method=task.trigger_method,
            port=task.port,
            status=task.status,
            cron_expression=task.cron_expression,
            created_time=task.created_time.isoformat(),
            updated_time=task.updated_time.isoformat(),
            tags=tags,
            latest_execution=None if not latest_record else {
                "record_id": latest_record.record_id,
                "execution_status": latest_record.execution_status,
                "start_time": latest_record.start_time.isoformat() if latest_record.start_time else None,
                "end_time": latest_record.end_time.isoformat() if latest_record.end_time else None
            }
        )

        logger.info(f"[{request_id}] 获取任务详情成功，task_id: {task_id}")

        return CommonResponses.success(
            data=task_detail,
            message="获取任务详情成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取任务详情异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取任务详情失败，请稍后重试",
                request_id
            ).dict()
        )


@router.post("/batch-operation",
             summary="批量操作任务",
             description="批量启动、停止或删除任务",
             response_model=BaseResponse[dict])
async def batch_operation_tasks(
        operation_data: TaskBatchOperationRequest,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """批量操作任务"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        if not operation_data.task_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "任务ID列表不能为空",
                    request_id
                ).dict()
            )

        success_count = 0
        failed_count = 0
        results = []

        for task_id in operation_data.task_ids:
            try:
                task = db.query(Task).filter(Task.task_id == task_id).first()
                if not task:
                    results.append({
                        "task_id": task_id,
                        "success": False,
                        "message": "任务不存在"
                    })
                    failed_count += 1
                    continue

                if operation_data.operation == "start":
                    # 启动任务逻辑
                    task.status = "active"
                    results.append({
                        "task_id": task_id,
                        "success": True,
                        "message": "任务启动成功"
                    })
                    success_count += 1

                elif operation_data.operation == "stop":
                    # 停止任务逻辑
                    task.status = "stopped"
                    results.append({
                        "task_id": task_id,
                        "success": True,
                        "message": "任务停止成功"
                    })
                    success_count += 1

                elif operation_data.operation == "delete":
                    # 检查任务是否正在运行
                    running_records = db.query(TaskRecord).filter(
                        and_(
                            TaskRecord.task_id == task_id,
                            TaskRecord.execution_status == "running"
                        )
                    ).first()

                    if running_records:
                        results.append({
                            "task_id": task_id,
                            "success": False,
                            "message": "任务正在运行中，无法删除"
                        })
                        failed_count += 1
                        continue

                    # 删除相关记录
                    db.query(TaskTagRelation).filter(TaskTagRelation.task_id == task_id).delete()
                    db.query(TaskRecord).filter(TaskRecord.task_id == task_id).delete()
                    db.delete(task)

                    results.append({
                        "task_id": task_id,
                        "success": True,
                        "message": "任务删除成功"
                    })
                    success_count += 1

                else:
                    results.append({
                        "task_id": task_id,
                        "success": False,
                        "message": f"不支持的操作: {operation_data.operation}"
                    })
                    failed_count += 1

            except Exception as e:
                logger.error(f"[{request_id}] 批量操作任务失败，task_id: {task_id}, error: {str(e)}")
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": f"操作失败: {str(e)}"
                })
                failed_count += 1

        # 提交所有更改
        db.commit()

        response_data = {
            "operation": operation_data.operation,
            "total_count": len(operation_data.task_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }

        logger.info(
            f"[{request_id}] 批量操作完成，操作: {operation_data.operation}, 成功: {success_count}, 失败: {failed_count}")

        return CommonResponses.success(
            data=response_data,
            message=f"批量{operation_data.operation}操作完成，成功: {success_count}, 失败: {failed_count}",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 批量操作任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "批量操作失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/{task_id}/records",
            summary="获取任务执行记录",
            description="获取指定任务的执行记录列表",
            response_model=BaseResponse[dict])
async def get_task_records(
        task_id: int,
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(10, ge=1, le=100, description="每页条数"),
        execution_status: Optional[str] = Query(None, description="执行状态"),
        start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """获取任务执行记录"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 验证任务是否存在
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"任务ID {task_id} 不存在",
                    request_id
                ).dict()
            )

        # 构建查询条件
        query = db.query(TaskRecord).filter(TaskRecord.task_id == task_id)

        # 执行状态筛选
        if execution_status:
            query = query.filter(TaskRecord.execution_status == execution_status)

        # 日期范围筛选
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(TaskRecord.start_time >= start_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "开始日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                # 设置为当天的最后一秒
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(TaskRecord.start_time <= end_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "结束日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        # 获取总数
        total = query.count()

        # 分页查询
        records = query.order_by(desc(TaskRecord.created_time)) \
            .offset((page - 1) * size) \
            .limit(size) \
            .all()

        # 构建响应数据
        record_list = []
        for record in records:
            duration = None
            if record.start_time and record.end_time:
                duration = int((record.end_time - record.start_time).total_seconds())

            record_data = {
                "record_id": record.record_id,
                "task_id": record.task_id,
                "trigger_method": record.trigger_method,
                "execution_status": record.execution_status,
                "start_time": record.start_time.isoformat() if record.start_time else None,
                "end_time": record.end_time.isoformat() if record.end_time else None,
                "duration_seconds": duration,
                "created_time": record.created_time.isoformat()
            }
            record_list.append(record_data)

        # 分页信息
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = {
            "task_id": task_id,
            "task_name": task.task_name,
            "records": record_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

        logger.info(f"[{request_id}] 获取任务执行记录成功，task_id: {task_id}, 返回 {len(record_list)} 条记录")

        return CommonResponses.success(
            data=response_data,
            message="获取任务执行记录成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取任务执行记录异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取任务执行记录失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/records",
            summary="获取所有任务执行记录",
            description="获取所有任务的执行记录列表，支持多条件筛选",
            response_model=BaseResponse[dict])
async def get_all_task_records(
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(10, ge=1, le=100, description="每页条数"),
        task_name: Optional[str] = Query(None, description="任务名称（模糊查询）"),
        execution_status: Optional[str] = Query(None, description="执行状态"),
        trigger_method: Optional[str] = Query(None, description="触发方式"),
        start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
        db: Session = Depends(get_db)
) -> BaseResponse[dict]:
    """获取所有任务执行记录"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 构建查询条件
        query = db.query(TaskRecord).join(Task)

        # 任务名称模糊查询
        if task_name:
            query = query.filter(Task.task_name.like(f"%{task_name}%"))

        # 执行状态筛选
        if execution_status:
            query = query.filter(TaskRecord.execution_status == execution_status)

        # 触发方式筛选
        if trigger_method:
            query = query.filter(TaskRecord.trigger_method == trigger_method)

        # 日期范围筛选
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(TaskRecord.start_time >= start_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "开始日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(TaskRecord.start_time <= end_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "结束日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        # 获取总数
        total = query.count()

        # 分页查询，包含任务信息
        records = query.options(joinedload(TaskRecord.task)) \
            .order_by(desc(TaskRecord.created_time)) \
            .offset((page - 1) * size) \
            .limit(size) \
            .all()

        # 构建响应数据
        record_list = []
        for record in records:
            duration = None
            if record.start_time and record.end_time:
                duration = int((record.end_time - record.start_time).total_seconds())

            record_data = {
                "record_id": record.record_id,
                "task_id": record.task_id,
                "task_name": record.task.task_name,
                "trigger_method": record.trigger_method,
                "execution_status": record.execution_status,
                "start_time": record.start_time.isoformat() if record.start_time else None,
                "end_time": record.end_time.isoformat() if record.end_time else None,
                "duration_seconds": duration,
                "created_time": record.created_time.isoformat()
            }
            record_list.append(record_data)

        # 分页信息
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = {
            "records": record_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

        logger.info(f"[{request_id}] 获取所有任务执行记录成功，返回 {len(record_list)} 条记录")

        return CommonResponses.success(
            data=response_data,
            message="获取任务执行记录成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取所有任务执行记录异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取任务执行记录失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/statistics",
            summary="获取任务统计信息",
            description="获取任务的统计信息，包括总数、状态分布、执行情况等",
            response_model=BaseResponse[TaskStatisticsResponse])
async def get_task_statistics(
        start_date: Optional[str] = Query(None, description="统计开始日期 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="统计结束日期 (YYYY-MM-DD)"),
        db: Session = Depends(get_db),
) -> BaseResponse[TaskStatisticsResponse]:
    """获取任务统计信息"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 任务状态统计
        task_status_stats = db.query(Task.status, db.func.count(Task.task_id).label('count')) \
            .group_by(Task.status) \
            .all()

        status_distribution = {status: count for status, count in task_status_stats}

        # 触发方式统计
        trigger_method_stats = db.query(Task.trigger_method, db.func.count(Task.task_id).label('count')) \
            .group_by(Task.trigger_method) \
            .all()

        trigger_distribution = {method: count for method, count in trigger_method_stats}

        # 执行记录统计查询
        record_query = db.query(TaskRecord)

        # 日期范围筛选
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                record_query = record_query.filter(TaskRecord.start_time >= start_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "开始日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                record_query = record_query.filter(TaskRecord.start_time <= end_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        "结束日期格式不正确，请使用 YYYY-MM-DD 格式",
                        request_id
                    ).dict()
                )

        # 执行状态统计
        execution_status_stats = record_query.query(TaskRecord.execution_status,
                                                    db.func.count(TaskRecord.record_id).label('count')) \
            .group_by(TaskRecord.execution_status) \
            .all()

        execution_distribution = {status: count for status, count in execution_status_stats}

        # 总执行次数
        total_executions = record_query.count()

        # 今日执行次数
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_executions = db.query(TaskRecord).filter(TaskRecord.start_time >= today).count()

        # 成功率计算
        success_executions = execution_distribution.get("completed", 0)
        success_rate = (success_executions / total_executions * 100) if total_executions > 0 else 0

        # 构建响应数据
        statistics_data = TaskStatisticsResponse(
            total_tasks=db.query(Task).count(),
            active_tasks=status_distribution.get("active", 0),
            stopped_tasks=status_distribution.get("stopped", 0),
            total_executions=total_executions,
            today_executions=today_executions,
            success_rate=round(success_rate, 2),
            status_distribution=status_distribution,
            trigger_distribution=trigger_distribution,
            execution_distribution=execution_distribution,
            statistics_period={
                "start_date": start_date,
                "end_date": end_date
            }
        )

        logger.info(f"[{request_id}] 获取任务统计信息成功")

        return CommonResponses.success(
            data=statistics_data,
            message="获取任务统计信息成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取任务统计信息异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取任务统计信息失败，请稍后重试",
                request_id
            ).dict()
        )


@router.delete("/records/{record_id}",
               summary="删除任务执行记录",
               description="删除指定的任务执行记录",
               response_model=BaseResponse[dict])
async def delete_task_record(
        record_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """删除任务执行记录"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找执行记录
        record = db.query(TaskRecord).filter(TaskRecord.record_id == record_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"执行记录ID {record_id} 不存在",
                    request_id
                ).dict()
            )

        # 检查记录状态，如果正在运行则不允许删除
        if record.execution_status == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "正在运行的任务记录不能删除",
                    request_id
                ).dict()
            )

        # 删除记录
        db.delete(record)
        db.commit()

        logger.info(f"[{request_id}] 任务执行记录删除成功，record_id: {record_id}")

        return CommonResponses.success(
            data={"record_id": record_id, "deleted": True},
            message="任务执行记录删除成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 删除任务执行记录异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "删除任务执行记录失败，请稍后重试",
                request_id
            ).dict()
        )