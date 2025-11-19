"""
PDF extraction tasks database operations.

Provides CRUD operations for pdf_extraction_tasks table.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

from db.database import DatabaseManager

logger = logging.getLogger(__name__)


async def create_pdf_extraction_task(
    task_id: str,
    pdf_url: str,
    pdf_object_key: str,
    user_id: str,
    project_id: str,
    source_filename: str,
    oss_object_prefix: str,
    page_count: Optional[int] = None,
    model: str = "qwen3-vl-flash",
    file_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    创建 PDF 提取任务记录
    
    Args:
        task_id: 任务 ID
        pdf_url: PDF 文件 URL
        pdf_object_key: OSS 对象键
        user_id: 用户 ID
        project_id: 项目 ID
        source_filename: 原始文件名
        oss_object_prefix: OSS 对象前缀
        page_count: 页数
        model: 使用的模型
        file_id: 文件 ID（用于关联上传系统，暂未使用）
        
    Returns:
        创建的任务记录
    """
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO pdf_extraction_tasks (
                    task_id, task_status, model, pdf_url, pdf_object_key,
                    page_count, user_id, project_id, source_filename,
                    oss_object_prefix, submitted_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *
                """,
                (
                    task_id,
                    "PENDING",
                    model,
                    pdf_url,
                    pdf_object_key,
                    page_count,
                    user_id,
                    project_id,
                    source_filename,
                    oss_object_prefix,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        logger.info(f"Created PDF extraction task: {task_id}")
        return row if row else {}


async def get_pdf_extraction_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 task_id 查询 PDF 提取任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务记录,不存在则返回 None
    """
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT * FROM pdf_extraction_tasks WHERE task_id = %s
                """,
                (task_id,),
            )
            row = await cur.fetchone()
            return row


async def update_task_status(
    task_id: str,
    status: str,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    error: Optional[Dict] = None,
) -> None:
    """
    更新任务状态
    
    Args:
        task_id: 任务 ID
        status: 新状态
        started_at: 开始时间
        completed_at: 完成时间
        error: 错误信息
    """
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # 构建动态 SQL
            set_fields = ["task_status = %s", "updated_at = NOW()"]
            params = [status]
            
            if started_at:
                set_fields.append("started_at = %s")
                params.append(started_at)
            if completed_at:
                set_fields.append("completed_at = %s")
                params.append(completed_at)
            if error:
                set_fields.append("error = %s")
                params.append(Jsonb(error))
                
            params.append(task_id)
            
            sql = f"""
                UPDATE pdf_extraction_tasks 
                SET {', '.join(set_fields)}
                WHERE task_id = %s
            """
            
            await cur.execute(sql, params)
        await conn.commit()
        logger.info(f"Updated task {task_id} status to {status}")


async def update_extraction_result(
    task_id: str,
    extracted_info: Dict[str, Any],
    extracted_info_url: str,
    extracted_info_object_key: str,
    page_image_urls: Optional[List[str]] = None,
) -> None:
    """
    更新提取结果
    
    Args:
        task_id: 任务 ID
        extracted_info: 提取的完整信息
        extracted_info_url: OSS JSON 文件 URL
        extracted_info_object_key: OSS object key
        page_image_urls: 页面图片 URL 列表
    """
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                UPDATE pdf_extraction_tasks 
                SET 
                    task_status = 'SUCCEEDED',
                    extracted_info = %s,
                    extracted_info_url = %s,
                    extracted_info_object_key = %s,
                    page_image_urls = %s,
                    -- 提取核心字段
                    project_source = %s,
                    project_name = %s,
                    project_contact = %s,
                    contact_info = %s,
                    project_leader = %s,
                    company_name = %s,
                    company_address = %s,
                    industry = %s,
                    core_team = %s,
                    core_product = %s,
                    core_technology = %s,
                    competition_analysis = %s,
                    market_size = %s,
                    financial_status = %s,
                    financing_history = %s,
                    keywords = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE task_id = %s
                """,
                (
                    Jsonb(extracted_info),
                    extracted_info_url,
                    extracted_info_object_key,
                    page_image_urls,
                    # 核心字段
                    extracted_info.get("project_source"),
                    extracted_info.get("project_name"),
                    extracted_info.get("project_contact"),
                    extracted_info.get("contact_info"),
                    extracted_info.get("project_leader"),
                    extracted_info.get("company_name"),
                    extracted_info.get("company_address"),
                    extracted_info.get("industry"),
                    Jsonb(extracted_info.get("core_team", [])),
                    extracted_info.get("core_product"),
                    extracted_info.get("core_technology"),
                    extracted_info.get("competition_analysis"),
                    extracted_info.get("market_size"),
                    Jsonb(extracted_info.get("financial_status", {})),
                    Jsonb(extracted_info.get("financing_history", {})),
                    extracted_info.get("keywords", []),
                    task_id,
                ),
            )
        await conn.commit()
        logger.info(f"Updated extraction result for task {task_id}")


async def list_pdf_extraction_tasks(
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Dict[str, Any]], int]:
    """
    列出 PDF 提取任务 (带分页和筛选)
    
    Args:
        user_id: 用户 ID 筛选
        project_id: 项目 ID 筛选
        status: 状态筛选
        industry: 行业筛选
        page: 页码 (从 1 开始)
        page_size: 每页大小
        
    Returns:
        (任务列表, 总数)
    """
    pool = await DatabaseManager.get_pool()
    
    # 构建筛选条件
    where_clauses = []
    params = []
    
    if user_id:
        where_clauses.append("user_id = %s")
        params.append(user_id)
    if project_id:
        where_clauses.append("project_id = %s")
        params.append(project_id)
    if status:
        status_map = {
            "pending": "PENDING",
            "processing": "PROCESSING",
            "completed": "SUCCEEDED",
            "failed": "FAILED",
        }
        normalized_status = status_map.get(status.lower(), status.upper())
        where_clauses.append("task_status = %s")
        params.append(normalized_status)
    if industry:
        where_clauses.append("industry = %s")
        params.append(industry)
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # 查询总数
            await cur.execute(
                f"SELECT COUNT(*) AS total FROM pdf_extraction_tasks {where_sql}",
                params,
            )
            count_row = await cur.fetchone()
            total = count_row["total"] if count_row else 0
            
            # 查询数据
            offset = (page - 1) * page_size
            query_params = params + [page_size, offset]
            
            await cur.execute(
                f"""
                SELECT * FROM pdf_extraction_tasks 
                {where_sql}
                ORDER BY submitted_at DESC
                LIMIT %s OFFSET %s
                """,
                query_params,
            )
            
            rows = await cur.fetchall()
            tasks = list(rows)
            
            return tasks, total


async def count_tasks_by_status(status: str) -> int:
    """统计指定状态的 PDF 任务数量"""
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pdf_extraction_tasks WHERE task_status = %s",
                (status,)
            )
            row = await cur.fetchone()
            return row[0] if row else 0


async def delete_pdf_extraction_task(task_id: str) -> bool:
    """
    删除 PDF 提取任务记录
    
    Args:
        task_id: 任务 ID
        
    Returns:
        是否删除成功
    """
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM pdf_extraction_tasks WHERE task_id = %s",
                (task_id,)
            )
            return cur.rowcount > 0
