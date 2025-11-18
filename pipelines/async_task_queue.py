"""
Async task queue for PDF extraction.

Simple priority-based queue using asyncio, no external dependencies.
"""

import os
import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class QueueTask:
    """队列任务"""
    task_id: str
    priority: TaskPriority


class AsyncTaskQueue:
    """
    异步任务队列管理器
    
    特点:
    - 基于优先级的任务调度
    - 可配置的并发数
    - 零外部依赖 (仅用 asyncio)
    - 简单易扩展
    """
    
    def __init__(self):
        # 从环境变量读取配置
        self.max_concurrent = int(os.getenv("PDF_MAX_CONCURRENT_TASKS", "5"))
        self.max_queue_size = int(os.getenv("PDF_QUEUE_SIZE", "100"))
        
        # 优先级队列
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=self.max_queue_size
        )
        
        # 活跃任务追踪
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # 工作线程
        self._workers: List[asyncio.Task] = []
        self._running = False
        
        logger.info(
            f"AsyncTaskQueue initialized: max_concurrent={self.max_concurrent}, "
            f"max_queue_size={self.max_queue_size}"
        )
    
    async def start(self):
        """启动工作线程"""
        if self._running:
            logger.warning("Queue already running")
            return
            
        self._running = True
        
        # 创建工作线程
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(
                self._worker(f"worker-{i}"),
                name=f"pdf-worker-{i}"
            )
            self._workers.append(worker)
            
        logger.info(f"Started {len(self._workers)} workers")
    
    async def stop(self):
        """停止工作线程"""
        if not self._running:
            return
            
        self._running = False
        
        # 等待队列清空
        await self.queue.join()
        
        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()
            
        # 等待所有工作线程结束
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        logger.info("All workers stopped")
    
    async def submit_task(
        self,
        task_id: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> bool:
        """
        提交任务到队列
        
        Args:
            task_id: 任务 ID
            priority: 任务优先级
            
        Returns:
            是否成功提交
        """
        if not self._running:
            logger.error("Queue is not running, cannot submit task")
            return False
            
        try:
            # 检查队列是否已满
            if self.queue.full():
                logger.warning(f"Queue is full, rejecting task {task_id}")
                return False
            
            # 添加到队列 (优先级越小越先执行)
            queue_task = QueueTask(task_id=task_id, priority=priority)
            await self.queue.put((priority.value, queue_task))
            
            logger.info(
                f"Task {task_id} submitted with priority {priority.name}, "
                f"queue_size={self.queue.qsize()}"
            )
            return True
            
        except asyncio.QueueFull:
            logger.error(f"Failed to submit task {task_id}: queue is full")
            return False
        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}")
            return False
    
    async def _worker(self, name: str):
        """
        工作线程
        
        Args:
            name: 工作线程名称
        """
        logger.info(f"{name} started")
        
        while self._running:
            try:
                # 从队列获取任务 (带超时,避免阻塞)
                try:
                    priority_value, queue_task = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                task_id = queue_task.task_id
                logger.info(f"{name} processing task {task_id}")
                
                # 处理任务
                task = asyncio.create_task(
                    self._process_pdf_task(task_id),
                    name=f"pdf-task-{task_id}"
                )
                self.active_tasks[task_id] = task
                
                try:
                    await task
                    logger.info(f"{name} completed task {task_id}")
                except Exception as e:
                    logger.error(f"{name} task {task_id} failed: {e}")
                finally:
                    # 清理
                    self.active_tasks.pop(task_id, None)
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info(f"{name} cancelled")
                break
            except Exception as e:
                logger.error(f"{name} unexpected error: {e}")
    
    async def _process_pdf_task(self, task_id: str):
        """
        处理单个 PDF 任务
        
        Args:
            task_id: 任务 ID
        """
        # 导入放在这里避免循环依赖
        from pipelines.pdf_extraction_service import PDFExtractionService
        
        service = PDFExtractionService()
        await service.process_pdf(task_id)
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()
    
    def get_active_tasks(self) -> List[str]:
        """获取正在处理的任务列表"""
        return list(self.active_tasks.keys())
    
    def get_active_count(self) -> int:
        """获取活跃任务数"""
        return len(self.active_tasks)
    
    def get_status(self) -> Dict[str, any]:
        """
        获取队列状态
        
        Returns:
            队列状态信息
        """
        return {
            "is_running": self._running,
            "queue_length": self.get_queue_size(),
            "active_tasks": self.get_active_count(),
            "completed_tasks": 0,  # 可以后续从数据库统计
            "active_workers": len([w for w in self._workers if not w.done()]),
            "pending_tasks": self.get_queue_size(),
            "queue_capacity": self.max_queue_size,
            "max_workers": self.max_concurrent,
            "max_queue_size": self.max_queue_size,
        }


# 全局单例实例
_task_queue: Optional[AsyncTaskQueue] = None


def get_task_queue() -> AsyncTaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = AsyncTaskQueue()
    return _task_queue
