#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/24 13:59
# @Author     : fany
# @Project    : PyCharm
# @File       : tag.py
# @Description:
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.core.database import get_db
from app.models.merchant import Tag, TaskTagRelation, Task
from app.schemas.RequestModel.tag import TagCreateRequest, TagUpdateRequest
from app.schemas.ResponseModel.task import TagResponse
from app.schemas.ResponseModel.base import BaseResponse, CommonResponses


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tag", tags=["标签管理"])
security = HTTPBearer()


@router.post("/create",
             summary="创建标签",
             description="创建一个新的标签",
             response_model=BaseResponse[TagResponse],
             responses={
                 200: {
                     "description": "标签创建成功",
                     "content": {
                         "application/json": {
                             "example": {
                                 "code": 200,
                                 "message": "标签创建成功",
                                 "success": True,
                                 "data": {
                                     "tag_id": 1,
                                     "tag_name": "数据处理",
                                     "parent_id": None,
                                     "tag_level": 1,
                                     "status": "active",
                                     "description": "数据处理相关任务标签",
                                     "task_count": 0,
                                     "created_time": "2025-05-24T16:00:00Z",
                                     "updated_time": "2025-05-24T16:00:00Z",
                                     "children": None
                                 },
                                 "timestamp": "2025-05-24T16:00:00Z",
                                 "request_id": "req_12345"
                             }
                         }
                     }
                 }
             })
async def create_tag(
        tag_data: TagCreateRequest,
        db: Session = Depends(get_db),
) -> BaseResponse[TagResponse]:
    """创建标签"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 参数验证
        if not tag_data.tag_name or not tag_data.tag_name.strip():
            logger.warning(f"[{request_id}] 标签名称不能为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "标签名称不能为空",
                    request_id
                ).dict()
            )

        # 检查标签名称是否已存在
        existing_tag = db.query(Tag).filter(
            Tag.tag_name == tag_data.tag_name.strip()
        ).first()

        if existing_tag:
            logger.warning(f"[{request_id}] 标签名称已存在: {tag_data.tag_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    f"标签名称 '{tag_data.tag_name}' 已存在",
                    request_id
                ).dict()
            )

        # 验证父标签是否存在（如果指定了父标签）
        if tag_data.parent_id:
            parent_tag = db.query(Tag).filter(Tag.tag_id == tag_data.parent_id).first()
            if not parent_tag:
                logger.warning(f"[{request_id}] 父标签不存在: {tag_data.parent_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        f"父标签ID {tag_data.parent_id} 不存在",
                        request_id
                    ).dict()
                )

            # 设置标签层级为父标签层级+1
            calculated_level = parent_tag.tag_level + 1
            if tag_data.tag_level and tag_data.tag_level != calculated_level:
                logger.warning(f"[{request_id}] 标签层级不匹配，期望: {calculated_level}, 实际: {tag_data.tag_level}")
            tag_level = calculated_level
        else:
            tag_level = tag_data.tag_level or 1

        # 创建标签
        new_tag = Tag(
            tag_name=tag_data.tag_name.strip(),
            parent_id=tag_data.parent_id,
            tag_level=tag_level,
            status="active"
        )

        db.add(new_tag)
        db.commit()
        db.refresh(new_tag)

        logger.info(f"[{request_id}] 标签创建成功，标签ID: {new_tag.tag_id}")

        # 构建响应数据
        tag_response = TagResponse(
            tag_id=new_tag.tag_id,
            tag_name=new_tag.tag_name,
            parent_id=new_tag.parent_id,
            tag_level=new_tag.tag_level,
            status=new_tag.status,
            description=tag_data.description,
            task_count=0,
            created_time=new_tag.created_time.isoformat(),
            updated_time=new_tag.updated_time.isoformat(),
            children=None
        )

        return CommonResponses.success(
            data=tag_response,
            message="标签创建成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 创建标签异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "创建标签失败，请稍后重试",
                request_id
            ).dict()
        )


@router.put("/{tag_id}",
            summary="更新标签",
            description="更新指定标签的信息",
            response_model=BaseResponse[TagResponse])
async def update_tag(
        tag_id: int,
        tag_data: TagUpdateRequest,
        db: Session = Depends(get_db),
) -> BaseResponse[TagResponse]:
    """更新标签"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找标签
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if not tag:
            logger.warning(f"[{request_id}] 标签不存在，tag_id: {tag_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"标签ID {tag_id} 不存在",
                    request_id
                ).dict()
            )

        # 更新标签信息
        if tag_data.tag_name and tag_data.tag_name.strip():
            # 检查新名称是否与其他标签冲突
            existing_tag = db.query(Tag).filter(
                and_(
                    Tag.tag_name == tag_data.tag_name.strip(),
                    Tag.tag_id != tag_id
                )
            ).first()

            if existing_tag:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=CommonResponses.bad_request(
                        f"标签名称 '{tag_data.tag_name}' 已被其他标签使用",
                        request_id
                    ).dict()
                )

            tag.tag_name = tag_data.tag_name.strip()

        if tag_data.parent_id is not None:
            # 验证父标签存在性
            if tag_data.parent_id != 0:  # 0表示设置为根标签
                parent_tag = db.query(Tag).filter(Tag.tag_id == tag_data.parent_id).first()
                if not parent_tag:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=CommonResponses.bad_request(
                            f"父标签ID {tag_data.parent_id} 不存在",
                            request_id
                        ).dict()
                    )

                # 防止循环引用
                if tag_data.parent_id == tag_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=CommonResponses.bad_request(
                            "不能将标签设置为自己的父标签",
                            request_id
                        ).dict()
                    )

                tag.parent_id = tag_data.parent_id
                tag.tag_level = parent_tag.tag_level + 1
            else:
                tag.parent_id = None
                tag.tag_level = 1

        if tag_data.tag_level and tag_data.parent_id is None:
            tag.tag_level = tag_data.tag_level

        db.commit()
        db.refresh(tag)

        # 获取任务数量
        task_count = db.query(TaskTagRelation).filter(TaskTagRelation.tag_id == tag_id).count()

        logger.info(f"[{request_id}] 标签更新成功，tag_id: {tag_id}")

        # 构建响应数据
        tag_response = TagResponse(
            tag_id=tag.tag_id,
            tag_name=tag.tag_name,
            parent_id=tag.parent_id,
            tag_level=tag.tag_level,
            status=tag.status,
            description=tag_data.description,
            task_count=task_count,
            created_time=tag.created_time.isoformat(),
            updated_time=tag.updated_time.isoformat(),
            children=None
        )

        return CommonResponses.success(
            data=tag_response,
            message="标签更新成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 更新标签异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "更新标签失败，请稍后重试",
                request_id
            ).dict()
        )


@router.delete("/{tag_id}",
               summary="删除标签",
               description="删除指定的标签",
               response_model=BaseResponse[dict])
async def delete_tag(
        tag_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """删除标签"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找标签
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"标签ID {tag_id} 不存在",
                    request_id
                ).dict()
            )

        # 检查是否有子标签
        child_tags = db.query(Tag).filter(Tag.parent_id == tag_id).first()
        if child_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "该标签下存在子标签，请先删除子标签",
                    request_id
                ).dict()
            )

        # 检查是否有关联的任务
        related_tasks = db.query(TaskTagRelation).filter(TaskTagRelation.tag_id == tag_id).first()
        if related_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "该标签下存在关联任务，请先解除关联",
                    request_id
                ).dict()
            )

        # 删除标签
        db.delete(tag)
        db.commit()

        logger.info(f"[{request_id}] 标签删除成功，tag_id: {tag_id}")

        return CommonResponses.success(
            data={"tag_id": tag_id, "deleted": True},
            message="标签删除成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 删除标签异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "删除标签失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/list",
            summary="获取标签列表",
            description="获取标签列表，支持树形结构和平铺结构",
            response_model=BaseResponse[List[TagResponse]])
async def get_tag_list(
        tree_structure: bool = Query(False, description="是否返回树形结构"),
        parent_id: Optional[int] = Query(None, description="父标签ID（获取子标签）"),
        tag_name: Optional[str] = Query(None, description="标签名称（模糊查询）"),
        tag_level: Optional[int] = Query(None, description="标签层级"),
        include_task_count: bool = Query(True, description="是否包含任务数量统计"),
        db: Session = Depends(get_db),
) -> BaseResponse[List[TagResponse]]:
    """获取标签列表"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 构建查询条件
        query = db.query(Tag).filter(Tag.status == "active")

        # 标签名称模糊查询
        if tag_name:
            query = query.filter(Tag.tag_name.like(f"%{tag_name}%"))

        # 标签层级筛选
        if tag_level:
            query = query.filter(Tag.tag_level == tag_level)

        # 父标签筛选
        if parent_id is not None:
            query = query.filter(Tag.parent_id == parent_id)
        elif tree_structure:
            # 树形结构只获取根标签
            query = query.filter(Tag.parent_id.is_(None))

        # 排序
        tags = query.order_by(Tag.tag_level, Tag.tag_name).all()

        # 构建响应数据
        def build_tag_response(tag: Tag, include_children: bool = False) -> TagResponse:
            # 获取任务数量
            task_count = 0
            if include_task_count:
                task_count = db.query(TaskTagRelation).filter(TaskTagRelation.tag_id == tag.tag_id).count()

            # 获取子标签（如果需要）
            children = None
            if include_children and tree_structure:
                child_tags = db.query(Tag).filter(
                    and_(Tag.parent_id == tag.tag_id, Tag.status == "active")
                ).order_by(Tag.tag_name).all()

                if child_tags:
                    children = [build_tag_response(child_tag, True) for child_tag in child_tags]

            return TagResponse(
                tag_id=tag.tag_id,
                tag_name=tag.tag_name,
                parent_id=tag.parent_id,
                tag_level=tag.tag_level,
                status=tag.status,
                description=None,  # 可以根据需要从数据库获取
                task_count=task_count,
                created_time=tag.created_time.isoformat(),
                updated_time=tag.updated_time.isoformat(),
                children=children
            )

        # 构建标签列表
        tag_list = []
        for tag in tags:
            tag_response = build_tag_response(tag, tree_structure)
            tag_list.append(tag_response)

        logger.info(f"[{request_id}] 获取标签列表成功，返回 {len(tag_list)} 条记录")

        return CommonResponses.success(
            data=tag_list,
            message="获取标签列表成功",
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"[{request_id}] 获取标签列表异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取标签列表失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/{tag_id}",
            summary="获取标签详情",
            description="获取指定标签的详细信息",
            response_model=BaseResponse[TagResponse])
async def get_tag_detail(
        tag_id: int,
        include_children: bool = Query(False, description="是否包含子标签"),
        db: Session = Depends(get_db),
) -> BaseResponse[TagResponse]:
    """获取标签详情"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找标签
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"标签ID {tag_id} 不存在",
                    request_id
                ).dict()
            )

        # 获取任务数量
        task_count = db.query(TaskTagRelation).filter(TaskTagRelation.tag_id == tag_id).count()

        # 获取子标签
        children = None
        if include_children:
            child_tags = db.query(Tag).filter(
                and_(Tag.parent_id == tag_id, Tag.status == "active")
            ).order_by(Tag.tag_name).all()

            if child_tags:
                children = []
                for child_tag in child_tags:
                    child_task_count = db.query(TaskTagRelation).filter(
                        TaskTagRelation.tag_id == child_tag.tag_id
                    ).count()

                    child_response = TagResponse(
                        tag_id=child_tag.tag_id,
                        tag_name=child_tag.tag_name,
                        parent_id=child_tag.parent_id,
                        tag_level=child_tag.tag_level,
                        status=child_tag.status,
                        description=None,
                        task_count=child_task_count,
                        created_time=child_tag.created_time.isoformat(),
                        updated_time=child_tag.updated_time.isoformat(),
                        children=None
                    )
                    children.append(child_response)

        # 构建响应数据
        tag_detail = TagResponse(
            tag_id=tag.tag_id,
            tag_name=tag.tag_name,
            parent_id=tag.parent_id,
            tag_level=tag.tag_level,
            status=tag.status,
            description=None,
            task_count=task_count,
            created_time=tag.created_time.isoformat(),
            updated_time=tag.updated_time.isoformat(),
            children=children
        )

        logger.info(f"[{request_id}] 获取标签详情成功，tag_id: {tag_id}")

        return CommonResponses.success(
            data=tag_detail,
            message="获取标签详情成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取标签详情异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取标签详情失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/{tag_id}/tasks",
            summary="获取标签关联的任务",
            description="获取指定标签关联的任务列表",
            response_model=BaseResponse[dict])
async def get_tag_tasks(
        tag_id: int,
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(10, ge=1, le=100, description="每页条数"),
        task_status: Optional[str] = Query(None, description="任务状态筛选"),
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """获取标签关联的任务"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 验证标签是否存在
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"标签ID {tag_id} 不存在",
                    request_id
                ).dict()
            )

        # 构建查询条件
        query = db.query(Task).join(TaskTagRelation).filter(TaskTagRelation.tag_id == tag_id)

        # 任务状态筛选
        if task_status:
            query = query.filter(Task.status == task_status)

        # 获取总数
        total = query.count()

        # 分页查询
        tasks = query.order_by(desc(Task.created_time)) \
            .offset((page - 1) * size) \
            .limit(size) \
            .all()

        # 构建任务列表
        task_list = []
        for task in tasks:
            task_info = {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "trigger_method": task.trigger_method,
                "status": task.status,
                "created_time": task.created_time.isoformat(),
                "updated_time": task.updated_time.isoformat()
            }
            task_list.append(task_info)

        # 分页信息
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        response_data = {
            "tag_id": tag_id,
            "tag_name": tag.tag_name,
            "tasks": task_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

        logger.info(f"[{request_id}] 获取标签关联任务成功，tag_id: {tag_id}, 返回 {len(task_list)} 条记录")

        return CommonResponses.success(
            data=response_data,
            message="获取标签关联任务成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] 获取标签关联任务异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取标签关联任务失败，请稍后重试",
                request_id
            ).dict()
        )


@router.post("/{tag_id}/tasks/{task_id}",
             summary="添加任务标签关联",
             description="为任务添加标签",
             response_model=BaseResponse[dict])
async def add_task_tag_relation(
        tag_id: int,
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """添加任务标签关联"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 验证标签是否存在
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    f"标签ID {tag_id} 不存在",
                    request_id
                ).dict()
            )

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

        # 检查关联是否已存在
        existing_relation = db.query(TaskTagRelation).filter(
            and_(
                TaskTagRelation.task_id == task_id,
                TaskTagRelation.tag_id == tag_id
            )
        ).first()

        if existing_relation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=CommonResponses.bad_request(
                    "任务与标签的关联已存在",
                    request_id
                ).dict()
            )

        # 创建关联
        new_relation = TaskTagRelation(
            task_id=task_id,
            tag_id=tag_id
        )

        db.add(new_relation)
        db.commit()
        db.refresh(new_relation)

        logger.info(f"[{request_id}] 任务标签关联创建成功，task_id: {task_id}, tag_id: {tag_id}")

        return CommonResponses.success(
            data={
                "relation_id": new_relation.relation_id,
                "task_id": task_id,
                "tag_id": tag_id,
                "task_name": task.task_name,
                "tag_name": tag.tag_name
            },
            message="任务标签关联创建成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 创建任务标签关联异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "创建任务标签关联失败，请稍后重试",
                request_id
            ).dict()
        )


@router.delete("/{tag_id}/tasks/{task_id}",
               summary="删除任务标签关联",
               description="删除任务与标签的关联",
               response_model=BaseResponse[dict])
async def remove_task_tag_relation(
        tag_id: int,
        task_id: int,
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """删除任务标签关联"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 查找关联记录
        relation = db.query(TaskTagRelation).filter(
            and_(
                TaskTagRelation.task_id == task_id,
                TaskTagRelation.tag_id == tag_id
            )
        ).first()

        if not relation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonResponses.not_found(
                    "任务与标签的关联不存在",
                    request_id
                ).dict()
            )

        # 删除关联
        db.delete(relation)
        db.commit()

        logger.info(f"[{request_id}] 任务标签关联删除成功，task_id: {task_id}, tag_id: {tag_id}")

        return CommonResponses.success(
            data={
                "task_id": task_id,
                "tag_id": tag_id,
                "deleted": True
            },
            message="任务标签关联删除成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] 删除任务标签关联异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "删除任务标签关联失败，请稍后重试",
                request_id
            ).dict()
        )


@router.get("/statistics",
            summary="获取标签统计信息",
            description="获取标签的统计信息",
            response_model=BaseResponse[dict])
async def get_tag_statistics(
        db: Session = Depends(get_db),
) -> BaseResponse[dict]:
    """获取标签统计信息"""
    request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    try:
        # 标签总数
        total_tags = db.query(Tag).filter(Tag.status == "active").count()

        # 按层级统计
        level_stats = db.query(Tag.tag_level, func.count(Tag.tag_id).label('count')) \
            .filter(Tag.status == "active") \
            .group_by(Tag.tag_level) \
            .all()

        level_distribution = {f"level_{level}": count for level, count in level_stats}

        # 有任务关联的标签数量
        tags_with_tasks = db.query(Tag.tag_id) \
            .join(TaskTagRelation) \
            .filter(Tag.status == "active") \
            .distinct() \
            .count()

        # 无任务关联的标签数量
        tags_without_tasks = total_tags - tags_with_tasks

        # 最受欢迎的标签（关联任务最多的前5个）
        popular_tags = db.query(
            Tag.tag_id,
            Tag.tag_name,
            func.count(TaskTagRelation.task_id).label('task_count')
        ).join(TaskTagRelation) \
            .filter(Tag.status == "active") \
            .group_by(Tag.tag_id, Tag.tag_name) \
            .order_by(func.count(TaskTagRelation.task_id).desc()) \
            .limit(5) \
            .all()

        popular_tags_list = [
            {
                "tag_id": tag_id,
                "tag_name": tag_name,
                "task_count": task_count
            }
            for tag_id, tag_name, task_count in popular_tags
        ]

        # 根标签数量
        root_tags = db.query(Tag).filter(
            and_(Tag.parent_id.is_(None), Tag.status == "active")
        ).count()

        response_data = {
            "total_tags": total_tags,
            "root_tags": root_tags,
            "tags_with_tasks": tags_with_tasks,
            "tags_without_tasks": tags_without_tasks,
            "level_distribution": level_distribution,
            "popular_tags": popular_tags_list,
            "usage_rate": round((tags_with_tasks / total_tags * 100), 2) if total_tags > 0 else 0
        }

        logger.info(f"[{request_id}] 获取标签统计信息成功")

        return CommonResponses.success(
            data=response_data,
            message="获取标签统计信息成功",
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"[{request_id}] 获取标签统计信息异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=CommonResponses.internal_error(
                "获取标签统计信息失败，请稍后重试",
                request_id
            ).dict()
        )