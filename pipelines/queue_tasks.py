"""
PDF 提取任务队列 - 使用 Huey 框架

Author: AI Assistant
Date: 2025-11-19
"""

import os
import logging
from huey import RedisExpireHuey

logger = logging.getLogger(__name__)

# 初始化 Huey - Redis 任务队列（使用 RedisExpireHuey 自动过期结果）
huey = RedisExpireHuey(
    name=os.getenv('HUEY_QUEUE_NAME', 'pdf-tasks'),
    url=os.getenv('HUEY_REDIS_URL', 'redis://:200105@localhost:6379'),
    immediate=os.getenv('HUEY_IMMEDIATE', 'false').lower() == 'true',
    results=True,  # 启用结果存储
    store_none=False,  # 不存储 None 结果
    expire_time=3600,  # 结果过期时间：1 小时（3600 秒）
)


@huey.task(retries=3, retry_delay=60)
def pdf_extract_process_task(task_id: str, high_resolution: bool = False):
    """
    异步处理 PDF 提取任务
    
    该任务由 FastAPI 路由提交，由 Huey worker 消费执行。
    支持自动重试：失败时最多重试 3 次，每次间隔 60 秒。
    
    Args:
        task_id: PDF 提取任务 ID (UUID)
        high_resolution: 是否启用高分辨率模式
        
    Returns:
        dict: 任务执行结果（包含 task_id 和状态）
        
    Raises:
        Exception: 任务执行失败时抛出异常，Huey 会自动重试
    """
    from pipelines.pdf_extraction_service import PDFExtractionService
    import asyncio
    import sys
    
    logger.info(f"[PDF Extract] Starting task: {task_id} (high_resolution={high_resolution})")
    
    try:
        service = PDFExtractionService()
        # 在 Huey worker 中执行异步函数
        # Windows 上需要设置 SelectorEventLoopPolicy 以兼容 psycopg
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(service.process_pdf(task_id, high_resolution))
        finally:
            loop.close()
        
        logger.info(f"[PDF Extract] Task completed successfully: {task_id}")
        
        # 返回任务结果（会被存储到 Redis）
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "PDF extraction completed successfully"
        }
        
    except Exception as e:
        logger.error(
            f"[PDF Extract] Task failed: {task_id}",
            exc_info=True,
            extra={"task_id": task_id, "error": str(e)}
        )
        raise  # Huey 会自动重试


def get_queue_status():
    """
    获取 Huey 队列状态
    
    Returns:
        dict: 包含队列统计信息
    """
    try:
        # 获取 Redis 连接
        redis_conn = huey.storage.conn
        queue_key = huey.storage.queue_key
        
        # 获取队列长度
        queue_length = redis_conn.llen(queue_key)
        
        return {
            "queue_length": queue_length,
            "is_running": True,
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return {
            "queue_length": 0,
            "is_running": False,
            "error": str(e),
        }
