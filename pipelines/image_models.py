"""
图片处理相关的数据模型（修订版 - 2025-11-11）
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ImageDescription(BaseModel):
    """图片描述模型（LLM 输出）"""
    entity_name: str = Field(description="图片的核心实体名称")
    type: str = Field(description="图片类型")
    description: str = Field(description="详细描述")  # ⭐改名: detailed_description → description


class ImageRawData(BaseModel):
    """图片 Raw 数据（单张图片的完整信息）"""
    img_path: str = Field(description="图片路径")
    page_idx: Optional[int] = Field(default=None, description="所在页码")
    entity_name: str = Field(description="图片核心实体名称")
    type: str = Field(description="图片类型")
    description: str = Field(description="详细描述")
    context: Dict[str, str] = Field(default_factory=dict, description="上下文信息")


class ImageRawOutput(BaseModel):
    """图片 Raw 输出（*_content_list_image_raw.json）"""
    images: List[ImageRawData] = Field(default_factory=list, description="图片列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ImageEntity(BaseModel):
    """图片实体模型（提取后的实体）"""
    name: str = Field(description="实体名称")
    type: str = Field(description="实体类型")
    description: Optional[str] = Field(default=None, description="实体描述")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    source_image: str = Field(description="来源图片路径")
    page_idx: Optional[int] = Field(default=None, description="所在页码")


class ImageRelation(BaseModel):
    """图片关系模型"""
    source_entity: str = Field(description="源实体")
    target_entity: str = Field(description="目标实体")
    relation_type: str = Field(description="关系类型")
    description: Optional[str] = Field(default=None, description="关系描述")
    confidence: float = Field(default=1.0, description="置信度")
    source_image: str = Field(description="来源图片路径")


class ImageKGOutput(BaseModel):
    """图片知识图谱输出（*_content_list_image_kg_aligned.json）"""
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="对齐后的实体列表")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="关系列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
