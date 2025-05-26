#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/26 09:39
# @Author     : fany
# @Project    : PyCharm
# @File       : task.py
# @Description:
import re
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from croniter import croniter
from app.models.merchant import Task, TaskRecord

logger = logging.getLogger(__name__)


class CronValidator:
    """Cron表达式验证器"""

    @staticmethod
    def validate_cron_expression(cron_expression: str) -> bool:
        """
        验证cron表达式的合法性

        Args:
            cron_expression: cron表达式字符串

        Returns:
            bool: 表达式是否合法
        """
        if not cron_expression or not cron_expression.strip():
            return False

        try:
            # 使用croniter验证表达式
            croniter(cron_expression.strip())
            return True
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid cron expression: {cron_expression}, error: {str(e)}")
            return False

    @staticmethod
    def get_next_run_time(cron_expression: str, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        获取下次运行时间

        Args:
            cron_expression: cron表达式
            base_time: 基准时间，默认为当前时间

        Returns:
            datetime: 下次运行时间，如果表达式无效则返回None
        """
        if not CronValidator.validate_cron_expression(cron_expression):
            return None

        try:
            base = base_time or datetime.now()
            cron = croniter(cron_expression.strip(), base)
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Error getting next run time for cron '{cron_expression}': {str(e)}")
            return None

    @staticmethod
    def get_readable_description(cron_expression: str) -> str:
        """
        获取cron表达式的可读描述

        Args:
            cron_expression: cron表达式

        Returns:
            str: 可读描述
        """
        if not CronValidator.validate_cron_expression(cron_expression):
            return "无效的cron表达式"

        # 简单的cron表达式描述映射
        common_patterns = {
            "0 0 * * *": "每天午夜执行",
            "0 0 * * 0": "每周日午夜执行",
            "0 0 1 * *": "每月1号午夜执行",
            "0 0 1 1 *": "每年1月1号午夜执行",
            "*/5 * * * *": "每5分钟执行一次",
            "0 */2 * * *": "每2小时执行一次",
            "0 9 * * 1-5": "工作日上午9点执行",
        }

        cron_expr = cron_expression.strip()
        if cron_expr in common_patterns:
            return common_patterns[cron_expr]

        # 解析cron表达式的各个部分
        try:
            parts = cron_expr.split()
            if len(parts) == 5:
                minute, hour, day, month, weekday = parts

                descriptions = []

                # 分钟
                if minute == "*":
                    descriptions.append("每分钟")
                elif minute.startswith("*/"):
                    descriptions.append(f"每{minute[2:]}分钟")
                elif minute.isdigit():
                    descriptions.append(f"{minute}分")

                # 小时
                if hour == "*":
                    if minute != "*":
                        descriptions.append("每小时")
                elif hour.startswith("*/"):
                    descriptions.append(f"每{hour[2:]}小时")
                elif hour.isdigit():
                    descriptions.append(f"{hour}点")

                # 日期
                if day == "*":
                    if hour != "*" or minute != "*":
                        descriptions.append("每天")
                elif day.isdigit():
                    descriptions.append(f"每月{day}号")

                # 月份
                if month != "*" and month.isdigit():
                    descriptions.append(f"{month}月")

                # 星期
                if weekday != "*":
                    weekday_names = {
                        "0": "周日", "1": "周一", "2": "周二", "3": "周三",
                        "4": "周四", "5": "周五", "6": "周六"
                    }
                    if weekday in weekday_names:
                        descriptions.append(weekday_names[weekday])
                    elif "-" in weekday:
                        descriptions.append("工作日")

                return " ".join(descriptions) + "执行"

        except Exception:
            pass

        return f"自定义时间执行: {cron_expression}"


class TaskExecutor:
    """任务执行器"""

    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task: 任务对象

        Returns:
            Dict: 执行结果
        """
        task_id = task.task_id

        try:
            logger.info(f"开始执行任务: {task.task_name} (ID: {task_id})")

            # 检查任务是否已在运行
            if task_id in self.running_tasks and not self.running_tasks[task_id].done():
                raise Exception("任务已在运行中")

            # 创建执行任务
            execution_task = asyncio.create_task(self._do_execute_task(task))
            self.running_tasks[task_id] = execution_task

            # 等待执行完成
            result = await execution_task

            logger.info(f"任务执行完成: {task.task_name} (ID: {task_id})")
            return result

        except Exception as e:
            logger.error(f"任务执行失败: {task.task_name} (ID: {task_id}), error: {str(e)}")
            raise
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    async def _do_execute_task(self, task: Task) -> Dict[str, Any]:
        """
        实际执行任务的逻辑

        Args:
            task: 任务对象

        Returns:
            Dict: 执行结果
        """
        start_time = datetime.now()

        try:
            # 根据不同的任务类型执行不同的逻辑
            if task.trigger_method == "手动触发":
                result = await self._execute_manual_task(task)
            elif task.trigger_method == "定时触发":
                result = await self._execute_scheduled_task(task)
            elif task.trigger_method == "事件触发":
                result = await self._execute_event_task(task)
            else:
                raise Exception(f"不支持的触发方式: {task.trigger_method}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "result": result,
                "message": "任务执行成功"
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": False,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e),
                "message": "任务执行失败"
            }

    async def _execute_manual_task(self, task: Task) -> Dict[str, Any]:
        """执行手动任务"""
        # 模拟任务执行过程
        logger.info(f"执行手动任务: {task.task_name}")

        # 这里可以根据实际业务需求实现具体的任务逻辑
        # 例如：数据处理、文件操作、API调用等

        # 模拟一些处理时间
        await asyncio.sleep(2)

        return {
            "task_type": "manual",
            "processed_items": 100,
            "status": "completed"
        }

    async def _execute_scheduled_task(self, task: Task) -> Dict[str, Any]:
        """执行定时任务"""
        logger.info(f"执行定时任务: {task.task_name}")

        # 定时任务的具体逻辑
        # 例如：定期数据同步、报告生成、清理操作等

        # 模拟处理
        await asyncio.sleep(3)

        return {
            "task_type": "scheduled",
            "next_run_time": CronValidator.get_next_run_time(
                task.cron_expression).isoformat() if task.cron_expression else None,
            "processed_items": 200,
            "status": "completed"
        }

    async def _execute_event_task(self, task: Task) -> Dict[str, Any]:
        """执行事件触发任务"""
        logger.info(f"执行事件触发任务: {task.task_name}")

        # 事件触发任务的具体逻辑
        # 例如：响应文件变化、消息队列事件等

        # 模拟处理
        await asyncio.sleep(1)

        return {
            "task_type": "event",
            "event_source": "file_system",
            "processed_events": 50,
            "status": "completed"
        }

    async def stop_task(self, task_id: int) -> bool:
        """
        停止正在运行的任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功停止
        """
        try:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"任务 {task_id} 已被取消")

                    del self.running_tasks[task_id]
                    return True

            logger.warning(f"任务 {task_id} 不在运行中")
            return False

        except Exception as e:
            logger.error(f"停止任务 {task_id} 时发生错误: {str(e)}")
            return False

    def get_running_tasks(self) -> Dict[int, Dict[str, Any]]:
        """获取正在运行的任务列表"""
        running_info = {}
        for task_id, task in self.running_tasks.items():
            running_info[task_id] = {
                "task_id": task_id,
                "is_running": not task.done(),
                "is_cancelled": task.cancelled() if task.done() else False
            }
        return running_info


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.scheduled_tasks: Dict[int, asyncio.Task] = {}
        self.executor = TaskExecutor()

    def schedule_task(self, task: Task) -> bool:
        """
        调度定时任务

        Args:
            task: 任务对象

        Returns:
            bool: 是否成功调度
        """
        if task.trigger_method != "定时触发" or not task.cron_expression:
            logger.warning(f"任务 {task.task_id} 不是定时任务或缺少cron表达式")
            return False

        if not CronValidator.validate_cron_expression(task.cron_expression):
            logger.error(f"任务 {task.task_id} 的cron表达式无效: {task.cron_expression}")
            return False

        try:
            # 取消现有的调度（如果存在）
            self.unschedule_task(task.task_id)

            # 创建新的调度任务
            schedule_task = asyncio.create_task(self._schedule_loop(task))
            self.scheduled_tasks[task.task_id] = schedule_task

            logger.info(f"任务 {task.task_id} ({task.task_name}) 已调度")
            return True

        except Exception as e:
            logger.error(f"调度任务 {task.task_id} 失败: {str(e)}")
            return False

    async def _schedule_loop(self, task: Task):
        """调度循环"""
        try:
            while True:
                # 计算下次执行时间
                next_run = CronValidator.get_next_run_time(task.cron_expression)
                if not next_run:
                    logger.error(f"无法计算任务 {task.task_id} 的下次执行时间")
                    break

                # 计算等待时间
                now = datetime.now()
                wait_seconds = (next_run - now).total_seconds()

                if wait_seconds > 0:
                    logger.info(f"任务 {task.task_id} 将在 {next_run} 执行，等待 {wait_seconds:.2f} 秒")
                    await asyncio.sleep(wait_seconds)

                # 执行任务
                try:
                    await self.executor.execute_task(task)
                except Exception as e:
                    logger.error(f"定时任务 {task.task_id} 执行失败: {str(e)}")

        except asyncio.CancelledError:
            logger.info(f"任务 {task.task_id} 的调度已取消")
        except Exception as e:
            logger.error(f"任务 {task.task_id} 调度循环异常: {str(e)}")

    def unschedule_task(self, task_id: int) -> bool:
        """
        取消任务调度

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        try:
            if task_id in self.scheduled_tasks:
                task = self.scheduled_tasks[task_id]
                task.cancel()
                del self.scheduled_tasks[task_id]
                logger.info(f"任务 {task_id} 的调度已取消")
                return True

            logger.warning(f"任务 {task_id} 没有被调度")
            return False

        except Exception as e:
            logger.error(f"取消任务 {task_id} 调度失败: {str(e)}")
            return False

    def get_scheduled_tasks(self) -> Dict[int, Dict[str, Any]]:
        """获取已调度的任务列表"""
        scheduled_info = {}
        for task_id, task in self.scheduled_tasks.items():
            scheduled_info[task_id] = {
                "task_id": task_id,
                "is_scheduled": not task.done(),
                "is_cancelled": task.cancelled() if task.done() else False
            }
        return scheduled_info


class TaskValidator:
    """任务验证器"""

    @staticmethod
    def validate_task_name(task_name: str) -> tuple[bool, str]:
        """
        验证任务名称

        Args:
            task_name: 任务名称

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if not task_name or not task_name.strip():
            return False, "任务名称不能为空"

        task_name = task_name.strip()

        if len(task_name) < 2:
            return False, "任务名称长度不能少于2个字符"

        if len(task_name) > 255:
            return False, "任务名称长度不能超过255个字符"

        # 检查特殊字符
        invalid_chars = ['<', '>', '"', "'", '&', '\\', '/', '|']
        for char in invalid_chars:
            if char in task_name:
                return False, f"任务名称不能包含特殊字符: {char}"

        return True, ""

    @staticmethod
    def validate_port(port: Optional[int]) -> tuple[bool, str]:
        """
        验证端口号

        Args:
            port: 端口号

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if port is None:
            return True, ""

        if not isinstance(port, int):
            return False, "端口号必须是整数"

        if port < 1 or port > 65535:
            return False, "端口号必须在1-65535之间"

        # 检查是否为系统保留端口
        reserved_ports = [22, 23, 25, 53, 80, 110, 443, 993, 995]
        if port in reserved_ports:
            return False, f"端口号 {port} 为系统保留端口，请使用其他端口"

        return True, ""

    @staticmethod
    def validate_task_data(task_name: str, trigger_method: str, port: Optional[int],
                           cron_expression: Optional[str]) -> tuple[bool, str]:
        """
        验证任务数据的完整性

        Args:
            task_name: 任务名称
            trigger_method: 触发方式
            port: 端口号
            cron_expression: cron表达式

        Returns:
            tuple: (是否有效, 错误信息)
        """
        # 验证任务名称
        is_valid, error_msg = TaskValidator.validate_task_name(task_name)
        if not is_valid:
            return False, error_msg

        # 验证触发方式
        valid_methods = ["手动触发", "定时触发", "事件触发"]
        if trigger_method not in valid_methods:
            return False, f"无效的触发方式: {trigger_method}"

        # 验证端口号
        is_valid, error_msg = TaskValidator.validate_port(port)
        if not is_valid:
            return False, error_msg

        # 定时触发任务必须有cron表达式
        if trigger_method == "定时触发":
            if not cron_expression:
                return False, "定时触发任务必须提供cron表达式"

            if not CronValidator.validate_cron_expression(cron_expression):
                return False, "cron表达式格式不正确"

        return True, ""


class TaskStatisticsCalculator:
    """任务统计计算器"""

    @staticmethod
    def calculate_success_rate(total_executions: int, success_executions: int) -> float:
        """
        计算成功率

        Args:
            total_executions: 总执行次数
            success_executions: 成功执行次数

        Returns:
            float: 成功率（百分比）
        """
        if total_executions == 0:
            return 0.0
        return round((success_executions / total_executions) * 100, 2)

    @staticmethod
    def calculate_average_duration(durations: list) -> float:
        """
        计算平均执行时长

        Args:
            durations: 执行时长列表（秒）

        Returns:
            float: 平均时长（秒）
        """
        if not durations:
            return 0.0
        return round(sum(durations) / len(durations), 2)

    @staticmethod
    def get_execution_trend(executions_by_date: Dict[str, int]) -> Dict[str, Any]:
        """
        获取执行趋势

        Args:
            executions_by_date: 按日期分组的执行次数

        Returns:
            Dict: 趋势分析结果
        """
        if not executions_by_date:
            return {"trend": "stable", "change_rate": 0.0}

        dates = sorted(executions_by_date.keys())
        if len(dates) < 2:
            return {"trend": "stable", "change_rate": 0.0}

        # 计算最近几天的变化趋势
        recent_dates = dates[-7:] if len(dates) >= 7 else dates
        if len(recent_dates) < 2:
            return {"trend": "stable", "change_rate": 0.0}

        first_half = recent_dates[:len(recent_dates) // 2]
        second_half = recent_dates[len(recent_dates) // 2:]

        first_avg = sum(executions_by_date[date] for date in first_half) / len(first_half)
        second_avg = sum(executions_by_date[date] for date in second_half) / len(second_half)

        if first_avg == 0:
            change_rate = 100.0 if second_avg > 0 else 0.0
        else:
            change_rate = ((second_avg - first_avg) / first_avg) * 100

        if change_rate > 10:
            trend = "increasing"
        elif change_rate < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_rate": round(change_rate, 2)
        }


# 全局实例
task_executor = TaskExecutor()
task_scheduler = TaskScheduler()


def validate_cron_expression(cron_expression: str) -> bool:
    """验证cron表达式（供外部调用）"""
    return CronValidator.validate_cron_expression(cron_expression)
