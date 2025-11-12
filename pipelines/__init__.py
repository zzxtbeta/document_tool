"""
Pipelines 包 - 文本和图片处理流程

模块：
- text_pipeline: 文本知识图谱提取
- image_pipeline: 图片知识图谱提取
- image_models: 图片相关数据模型
"""

__version__ = "1.0.0"

from .text_pipeline import TextKnowledgeGraphPipeline
from .image_pipeline import ImageKnowledgeGraphPipeline, ImagePipelineConfig
from .image_models import ImageDescription, ImageEntity, ImageKGOutput

__all__ = [
    "TextKnowledgeGraphPipeline",
    "ImageKnowledgeGraphPipeline",
    "ImagePipelineConfig",
    "ImageDescription",
    "ImageEntity",
    "ImageKGOutput",
]
