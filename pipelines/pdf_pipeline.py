"""
PDF Pipeline

Author: AI Assistant
Date: 2025-11-18
"""

import os
import logging
from pathlib import Path
from typing import Tuple, List
from PIL import Image
import pypdf

logger = logging.getLogger(__name__)


class PDFPipeline:
    """PDF 处理管道"""
    
    def __init__(self):
        self.max_size_mb = int(os.getenv("PDF_MAX_SIZE_MB", "50"))
        self.max_pages = int(os.getenv("PDF_MAX_PAGES", "100"))
        self.dpi = int(os.getenv("PDF_CONVERSION_DPI", "300"))
        self.image_max_size_mb = int(os.getenv("PDF_IMAGE_MAX_SIZE_MB", "10"))
        
    def validate_pdf(self, file_path: Path) -> Tuple[bool, str, int]:
        """验证 PDF 文件"""
        if not file_path.exists():
            return False, "文件不存在", 0
            
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            return False, f"PDF 文件过大 ({file_size_mb:.1f}MB > {self.max_size_mb}MB)", 0
            
        try:
            with open(file_path, "rb") as f:
                pdf = pypdf.PdfReader(f)
                page_count = len(pdf.pages)
                
                if page_count > self.max_pages:
                    return False, f"PDF 页数过多 ({page_count} > {self.max_pages})", page_count
                    
                if pdf.is_encrypted:
                    return False, "不支持加密的 PDF 文件", page_count
                    
                return True, "", page_count
                
        except Exception as e:
            return False, f"PDF 读取失败: {str(e)}", 0
    
    def convert_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """转换 PDF 为图片"""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError("pdf2image not installed. Run: pip install pdf2image")
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查 poppler 路径
        poppler_path = os.getenv("POPPLER_PATH")
        
        images = convert_from_path(
            str(pdf_path),
            dpi=self.dpi,
            fmt="jpeg",
            poppler_path=poppler_path if poppler_path else None
        )
        
        image_paths = []
        for i, image in enumerate(images, 1):
            image_path = output_dir / f"page_{i:03d}.jpg"
            
            if self._needs_compression(image):
                image = self._compress_image(image)
            
            image.save(image_path, "JPEG", quality=85, optimize=True)
            image_paths.append(image_path)
            
        logger.info(f"Converted {len(image_paths)} pages")
        return image_paths
    
    def _needs_compression(self, image: Image.Image) -> bool:
        """检查图片是否需要压缩"""
        width, height = image.size
        estimated_size_mb = (width * height * 3) / (1024 * 1024)
        return estimated_size_mb > self.image_max_size_mb
    
    def _compress_image(self, image: Image.Image) -> Image.Image:
        """压缩图片"""
        max_dimension = int(os.getenv("VL_IMAGE_RESIZE_MAX_DIMENSION", "2048"))
        width, height = image.size
        
        if max(width, height) > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * max_dimension / width)
            else:
                new_height = max_dimension
                new_width = int(width * max_dimension / height)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image: {width}x{height} -> {new_width}x{new_height}")
        
        return image


class PDFValidator:
    """PDF 文件类型验证器"""
    
    @staticmethod
    def validate(file_content: bytes) -> Tuple[bool, str]:
        """验证文件是否为 PDF"""
        if not file_content:
            return False, "文件内容为空"
            
        if not file_content.startswith(b'%PDF'):
            return False, "不是有效的 PDF 文件"
            
        return True, ""
