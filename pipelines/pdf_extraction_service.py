"""
PDF Extraction Service

Author: AI Assistant
Date: 2025-11-18
"""

import os
import json
import uuid
import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from openai import OpenAI

from pipelines.pdf_pipeline import PDFPipeline, PDFValidator
from pipelines.storage import OSSStorageClient
from db.pdf_operations import (
    create_pdf_extraction_task,
    get_pdf_extraction_task,
    update_task_status,
    update_extraction_result,
    list_pdf_extraction_tasks,
    # 新的 pdf_queue_tasks 表操作
    create_pdf_queue_task,
    get_pdf_queue_task,
    update_pdf_queue_task,
    update_pdf_queue_task_result,
    update_project_fields,
)

logger = logging.getLogger(__name__)


class PDFExtractionService:
    """PDF 提取服务"""
    
    def __init__(self):
        self.pdf_pipeline = PDFPipeline()
        self.storage = OSSStorageClient()
        
        # Qwen VL 客户端配置通过环境变量控制,便于在不同部署之间切换
        vl_base_url = os.getenv(
            "VL_BASE_URL",
            os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        vl_model_name = os.getenv("VL_MODEL_NAME", os.getenv("MODEL_NAME", "qwen3-vl-flash"))
        self.vl_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=vl_base_url,
        )
        self.vl_model = vl_model_name
        
        # 加载提取 Prompt (允许通过环境变量覆盖默认模板)
        prompt_file = os.getenv("PDF_EXTRACTION_PROMPT_FILE")
        if prompt_file:
            prompt_path = Path(prompt_file)
            if not prompt_path.is_file():
                logger.warning("Custom prompt file not found: %s, fallback to default", prompt_path)
                prompt_path = None
        else:
            prompt_filename = os.getenv("PDF_PROMPT_FILENAME", "bp_extraction.txt")
            prompt_path = Path(__file__).parent / "prompts" / prompt_filename
        if prompt_path is None:
            prompt_path = Path(__file__).parent / "prompts" / "bp_extraction.txt"
        self.extraction_prompt = prompt_path.read_text(encoding="utf-8")
    
    async def submit_extraction(
        self,
        pdf_file_path: Path,
        user_id: str,
        project_id: str,
        source_filename: str,
        high_resolution: bool = False,
    ) -> str:
        """
        提交 PDF 提取任务
        
        Args:
            pdf_file_path: PDF 文件路径
            user_id: 用户 ID
            project_id: 项目 ID
            source_filename: 原始文件名
            high_resolution: 是否启用高分辨率模式
            
        Returns:
            task_id: 任务 ID
        """
        # 1. 验证 PDF
        is_valid, error_msg, page_count = self.pdf_pipeline.validate_pdf(pdf_file_path)
        if not is_valid:
            raise ValueError(f"PDF 验证失败: {error_msg}")
        
        logger.info(f"[PDF Extract] PDF validated: {source_filename}, {page_count} pages")
        
        # 2. 生成任务 ID
        task_id = str(uuid.uuid4())
        
        # 3. 上传 PDF 到 OSS（保持原始文件名）
        oss_prefix = self._build_pdf_prefix(project_id, task_id)
        pdf_object_key = f"{oss_prefix}/{source_filename}"
        
        self.storage.upload_file(
            pdf_file_path,
            pdf_object_key,
            content_type="application/pdf"
        )
        
        pdf_url = self.storage.build_public_url(pdf_object_key)
        logger.info(f"[PDF Extract] PDF uploaded to OSS: {pdf_url}")
        
        # 4. 创建数据库记录（使用新的 pdf_queue_tasks 表）
        await create_pdf_queue_task(
            task_id=task_id,
            project_id=project_id,
            pdf_url=pdf_url,
            pdf_object_key=pdf_object_key,
            source_filename=source_filename,
            oss_object_prefix=oss_prefix,
            page_count=page_count,
            user_id=user_id,
            high_resolution=high_resolution,
        )
        
        logger.info(f"[PDF Extract] Created task record in DB: {task_id}")
        
        # 5. 提交到 Huey 任务队列处理
        from pipelines.queue_tasks import pdf_extract_process_task
        pdf_extract_process_task(task_id, high_resolution)
        logger.info(f"[PDF Extract] Task submitted to Huey queue: {task_id} (high_resolution={high_resolution})")
        
        return task_id
    
    async def submit_extraction_from_oss(
        self,
        oss_key_list: List[str],
        project_id: str,
        user_id: str,
        file_id_list: Optional[List[str]] = None,
        high_resolution: bool = False,
        retry_count: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        从 OSS 提交 PDF 提取任务（用于外部系统集成）
        
        Args:
            oss_key_list: OSS 文件路径列表
            project_id: 项目 ID
            user_id: 用户 ID
            file_id_list: 文件 ID 列表（可选，用于关联上传系统）
            high_resolution: 是否启用高分辨率模式
            retry_count: 失败重试次数
            
        Returns:
            List[Dict]: 任务信息列表，每个包含 task_id, oss_key, file_id, status
        """
        tasks = []
        
        for idx, oss_key in enumerate(oss_key_list):
            try:
                # 生成任务 ID
                task_id = str(uuid.uuid4())
                
                # 获取文件 ID（如果提供）
                file_id = file_id_list[idx] if file_id_list else None
                
                # 从 OSS key 提取文件名
                source_filename = oss_key.split('/')[-1]
                
                # 创建数据库记录（使用新的 pdf_queue_tasks 表）
                await create_pdf_queue_task(
                    task_id=task_id,
                    project_id=project_id,
                    pdf_url=self.storage.build_public_url(oss_key),
                    pdf_object_key=oss_key,
                    user_id=user_id,
                    source_filename=source_filename,
                    oss_object_prefix=oss_key.rsplit('/', 1)[0],  # 提取目录前缀
                    page_count=None,  # 稍后在处理时获取
                    file_id=file_id,  # 关联上传系统的文件 ID
                    high_resolution=high_resolution,
                )
                
                logger.info(f"[PDF Extract] Created queue task record: {task_id} (oss_key={oss_key})")
                
                # 提交到 Huey 队列
                from pipelines.queue_tasks import pdf_extract_process_task
                pdf_extract_process_task(task_id, high_resolution)
                logger.info(f"[PDF Extract] Task submitted to queue: {task_id}")
                
                # 添加到返回列表
                tasks.append({
                    "task_id": task_id,
                    "oss_key": oss_key,
                    "file_id": file_id,
                    "status": "pending"
                })
                
            except Exception as e:
                logger.error(f"[PDF Extract] Failed to submit task for {oss_key}: {e}", exc_info=True)
                # 继续处理其他文件，不中断
                raise
        
        return tasks
    
    async def process_pdf(self, task_id: str, high_resolution: bool = False):
        """
        处理 PDF 文件 (由 Huey worker 调用的异步任务)
        
        Args:
            task_id: 任务 ID
            high_resolution: 是否启用高分辨率模式
        """
        logger.info(f"[PDF Extract] Processing started: {task_id}")
        
        # 本地临时目录
        temp_dir = Path("uploads/pdf") / task_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. 获取任务信息（从新的 pdf_queue_tasks 表）
            task = await get_pdf_queue_task(task_id)
            logger.info(f"[PDF Extract] Retrieved queue task from DB: {task}")
            if not task:
                logger.error(f"[PDF Extract] Task {task_id} not found in database")
                raise RuntimeError(f"Task {task_id} not found")
            
            # 2. 更新状态为 processing
            await update_pdf_queue_task(
                task_id,
                "processing",
                started_at=datetime.now()
            )
            
            # 3. 下载 PDF 到本地临时目录（保持原始文件名）
            pdf_path = self._download_pdf_to_local(
                task["pdf_object_key"], 
                temp_dir,
                task["source_filename"]
            )
            
            # 4. 转换为图片（保存到本地）
            image_paths = self._convert_pdf_to_images_local(pdf_path, temp_dir)
            
            # 5. 调用 Qwen VL 提取信息（使用本地图片路径）
            extracted_info = await self._extract_from_local_images(image_paths, high_resolution)
            
            # 6. 验证和清洗数据
            extracted_info = self._clean_data(extracted_info)
            
            # 7. 保存 JSON 到本地（两个位置）
            parsed_json_path, pdf_json_path = self._save_json_locally(
                extracted_info,
                task["source_filename"],
                task_id
            )
            
            # 8. 保存结果到 OSS（仅保存 JSON）
            result_url, result_key = self._save_result_to_oss(
                extracted_info,
                task["oss_object_prefix"],
                task["source_filename"]
            )
            
            # 9. 更新数据库
            # 9.1 更新 pdf_queue_tasks 表（任务结果）
            await update_pdf_queue_task_result(
                task_id=task_id,
                extracted_info=extracted_info,
                extracted_info_url=result_url,
                extracted_info_object_key=result_key,
            )
            
            # 9.2 更新 projects 表（项目字段）
            if task.get("project_id"):
                await update_project_fields(
                    project_id=task["project_id"],
                    extracted_info=extracted_info,
                )
                logger.info(f"[PDF Extract] Updated project fields for project {task['project_id']}")
            
            logger.info(f"[PDF Extract] Processing completed: {task_id}")
            logger.info(f"[PDF Extract] JSON saved: {parsed_json_path} & {pdf_json_path}")
            
        except Exception as e:
            logger.error(f"[PDF Extract] Processing failed: {task_id}", exc_info=True)
            
            # 更新状态为 failed（使用新表）
            await update_pdf_queue_task(
                task_id,
                "failed",
                completed_at=datetime.now(),
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            raise
        finally:
            # 10. 清理本地临时文件（仅删除图片，保留 PDF 和 JSON）
            if temp_dir.exists():
                import shutil
                # 只删除图片文件，保留 PDF 和 JSON
                for item in temp_dir.iterdir():
                    if item.is_file() and item.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                logger.info(f"[PDF Extract] Cleaned up temporary files: {task_id}")
    
    def _download_pdf_to_local(self, object_key: str, temp_dir: Path, source_filename: str = None) -> Path:
        """下载 PDF 文件到本地临时目录
        
        Args:
            object_key: OSS 对象键
            temp_dir: 临时目录
            source_filename: 原始文件名（可选，用于保持文件名）
        """
        # 使用原始文件名或默认名称
        filename = source_filename if source_filename else "original.pdf"
        pdf_path = temp_dir / filename
        
        # 下载文件
        self.storage.bucket.get_object_to_file(object_key, str(pdf_path))
        
        logger.info(f"[PDF Extract] Downloaded PDF to {pdf_path}")
        return pdf_path
    
    def _convert_pdf_to_images_local(self, pdf_path: Path, temp_dir: Path) -> List[Path]:
        """转换 PDF 为图片（保存到本地）"""
        output_dir = temp_dir / "pages"
        output_dir.mkdir(exist_ok=True)
        
        image_paths = self.pdf_pipeline.convert_to_images(pdf_path, output_dir)
        logger.info(f"[PDF Extract] Converted PDF to {len(image_paths)} images")
        return image_paths
    
    async def _extract_from_local_images(self, image_paths: List[Path], high_resolution: bool = False) -> Dict[str, Any]:
        """
        从本地图片提取信息（使用 Qwen VL 多图输入）
        
        Args:
            image_paths: 本地图片路径列表
            high_resolution: 是否启用高分辨率模式
            
        Returns:
            提取的结构化信息
        """
        # 构建多图输入 content
        content = []
        
        # 将本地图片转为 base64 编码
        import base64
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
                # 检测图片格式
                ext = img_path.suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{img_data}"}
                })
        
        # 添加提示词
        content.append({"type": "text", "text": self.extraction_prompt})
        
        messages = [{"role": "user", "content": content}]
        
        try:
            extra_body = {"enable_thinking": False}
            # 优先使用参数，其次使用环境变量
            if high_resolution or os.getenv("VL_HIGH_RESOLUTION_MODE", "false").lower() == "true":
                extra_body["vl_high_resolution_images"] = True
            
            logger.info(f"[PDF Extract] Calling Qwen VL with {len(image_paths)} images")
            
            completion = self.vl_client.chat.completions.create(
                model=self.vl_model,
                messages=messages,
                extra_body=extra_body,
                temperature=float(os.getenv("VL_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("VL_MAX_TOKENS", "4096")),
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            logger.info("[PDF Extract] VL extraction successful")
            return result
        except Exception as e:
            logger.error(f"[PDF Extract] VL API failed: {e}", exc_info=True)
            raise
    
    def _build_pdf_prefix(self, project_id: str, task_id: str) -> str:
        """构建 PDF OSS 前缀"""
        return self.storage.build_object_key(
            "bronze", "userUploads", project_id, "pdf", task_id
        )
    
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗和标准化数据"""
        cleaned = data.copy()
        
        # 字符串字段去空格
        string_fields = ["company_name", "industry", "core_product", "core_technology"]
        for field in string_fields:
            if field in cleaned and isinstance(cleaned[field], str):
                cleaned[field] = cleaned[field].strip()
        
        # 确保 core_team 是列表
        if "core_team" not in cleaned or not isinstance(cleaned["core_team"], list):
            cleaned["core_team"] = []
        
        # 确保关键词去重
        if "keywords" in cleaned and isinstance(cleaned["keywords"], list):
            cleaned["keywords"] = list(set(cleaned["keywords"]))[:15]
        
        return cleaned
    
    def _save_json_locally(
        self,
        extracted_info: dict,
        source_filename: str,
        task_id: str
    ) -> tuple[Path, Path]:
        """保存 JSON 到本地（两个位置）
        
        Args:
            extracted_info: 提取的数据
            source_filename: 原始文件名
            task_id: 任务 ID
            
        Returns:
            (parsed 目录路径, uploads/pdf 目录路径)
        """
        import json
        pdf_name = Path(source_filename).stem  # 去除 .pdf 后缀
        json_filename = f"{pdf_name}_extracted_info.json"
        
        # 1. 保存到 parsed/{pdf_name}/auto/ 目录
        parsed_dir = Path("parsed") / pdf_name / "auto"
        parsed_dir.mkdir(parents=True, exist_ok=True)
        parsed_json_path = parsed_dir / json_filename
        
        with open(parsed_json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[PDF Extract] Saved JSON to parsed: {parsed_json_path}")
        
        # 2. 保存到 uploads/pdf/{task_id}/ 目录（与 PDF 同目录）
        pdf_temp_dir = Path("uploads") / "pdf" / task_id
        pdf_temp_dir.mkdir(parents=True, exist_ok=True)
        pdf_json_path = pdf_temp_dir / json_filename
        
        with open(pdf_json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[PDF Extract] Saved JSON to PDF dir: {pdf_json_path}")
        
        return parsed_json_path, pdf_json_path
    
    def _save_result_to_oss(
        self,
        extracted_info: dict,
        oss_prefix: str,
        source_filename: str
    ) -> tuple[str, str]:
        """保存提取结果到 OSS"""
        # 生成文件名: {源文件名}_extracted_info.json
        filename = Path(source_filename).stem + "_extracted_info.json"
        object_key = f"{oss_prefix}/{filename}"
        
        # 上传 JSON
        json_content = json.dumps(extracted_info, ensure_ascii=False, indent=2)
        self.storage.upload_text(
            json_content,
            object_key,
            content_type="application/json"
        )
        
        # 生成 URL
        url = self.storage.build_public_url(object_key)
        
        logger.info(f"[PDF Extract] Saved extraction result to OSS: {url}")
        return url, object_key
