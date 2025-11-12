"""
表格处理 Pipeline 数据模型

定义表格处理过程中使用的数据结构和配置类。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import dotenv


dotenv.load_dotenv()


@dataclass
class TablePipelineConfig:
    """表格Pipeline配置"""
    
    # LLM 配置
    model_name: str = "qwen-plus-latest"
    temperature: float = 0.1
    api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    
    # 表格处理配置
    min_table_length: int = 50  # 最小表格长度（字符数）
    description_max_length: int = 200  # 描述最大长度
    
    # 系统配置
    verbose: bool = False
    output_dir: str = "./parsed"
    
    def __post_init__(self):
        """验证配置"""
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")


@dataclass
class TableDescription:
    """表格描述"""
    entity_name: str
    type: str
    description: str
    img_path: str = ""
    page_idx: int = 0
    table_caption: List[str] = field(default_factory=list)
    table_body: str = ""
    table_structure: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableEntity:
    """表格实体"""
    name: str
    type: str
    description: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_table: str = ""
    page_idx: int = 0


@dataclass
class TableRelation:
    """表格关系"""
    source_entity: str
    target_entity: str
    relation_type: str
    description: str = ""
    confidence: float = 0.9


@dataclass
class TableRawData:
    """单个表格的原始数据"""
    img_path: str
    page_idx: int
    entity_name: str
    type: str
    description: str
    table_caption: List[str]
    table_body: str
    table_structure: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableRawOutput:
    """表格处理原始输出"""
    metadata: Dict[str, Any]
    tables: List[Dict[str, Any]]
    entities: Dict[str, Dict[str, Any]]  # Dict格式，key为实体名
    relations: List[Dict[str, Any]]


@dataclass
class TableKGOutput:
    """表格知识图谱对齐输出"""
    metadata: Dict[str, Any]
    aligned_entities: Dict[str, Dict[str, Any]]  # Dict格式
    aligned_relations: List[Dict[str, Any]]


@dataclass
class TableProcessingStats:
    """表格处理统计信息"""
    total_tables: int = 0
    filtered_tables: int = 0
    valid_tables: int = 0
    total_entities: int = 0
    total_relations: int = 0
    entity_types: List[str] = field(default_factory=list)
    relation_types: List[str] = field(default_factory=list)
    processing_time: float = 0.0
