"""
图片处理 Pipeline - 从 MinerU 输出的 content_list.json 中提取图片信息并生成知识图谱

修订版 (2025-11-11)
主要改进：
1. ✅ 使用 EnhancedImageFilter（集成 ImageFilter 的 OCR + 分辨率过滤）
2. ✅ 两阶段实体提取：LLM 提取 + Ontology 对齐
3. ✅ 两个独立输出文件：_image_raw.json + _image_kg_aligned.json
4. ✅ 不修改输入文件
5. ✅ 字段命名简化：description（不再是 detailed_description）
"""
import os
import sys
import json
import re
import base64
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from tqdm import tqdm
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 处理相对导入问题
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipelines.image_models import ImageDescription, ImageRawData, ImageRawOutput, ImageEntity, ImageRelation, ImageKGOutput
else:
    from .image_models import ImageDescription, ImageRawData, ImageRawOutput, ImageEntity, ImageRelation, ImageKGOutput

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ImagePipelineConfig:
    """图片处理配置"""
    # 过滤参数
    ocr_engine: str = "auto"  # 'auto' | 'pytesseract' | 'easyocr' | 'paddleocr' | 'none'
    min_pixels: Optional[int] = None  # None 则使用 res_preset
    res_preset: str = "s"  # 's'=280k | 'm'=600k | 'l'=1.2M | 'off'=不过滤
    min_text_len: int = 10  # OCR 文本最小长度（<= 0 则跳过文本过滤）
    verbose: bool = False  # 显示详细过滤信息
    
    # 上下文参数
    context_window: int = 2  # 前后各取2个元素
    
    # LLM 参数
    multimodal_model: str = "qwen3-vl-flash"  # 多模态模型
    entity_extraction_model: str = "qwen-plus"  # 实体提取模型（复用 text_pipeline）
    temperature: float = 0.1  # 生成描述时的温度
    max_retries: int = 3  # 重试次数
    
    # 输出参数
    save_intermediate: bool = True  # 保存中间结果
    output_dir: Optional[str] = None  # 输出目录（默认与输入文件同目录）


class EnhancedImageFilter:
    """
    图片过滤器 - 三级过滤策略
    
    过滤策略：
    1. 表格图片（在 table 中出现的图片）
    2. 分辨率过滤（使用 res_preset）
    3. OCR 文本长度过滤（低于 min_text_len）
    """
    
    RES_PRESETS = {
        "s": 280_000,     # 28万像素
        "m": 600_000,     # 60万
        "l": 1_200_000,   # 120万
        "off": 0          # 不过滤
    }
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.table_images: Set[str] = set()
        self.ocr_func = self._init_ocr()
    
    def collect_table_images(self, content_list: List[Dict]) -> None:
        """收集所有表格相关的图片路径"""
        self.table_images.clear()
        
        for item in content_list:
            if item.get("type") == "table":
                # 1. 表格自身的 img_path（主图）
                img_path = item.get("img_path", "")
                if img_path:
                    self.table_images.add(img_path)
                
                # 2. 表格内嵌的 imgs 列表（如果有）
                imgs = item.get("imgs", [])
                for img_info in imgs:
                    img_path = img_info.get("img_path", "")
                    if img_path:
                        self.table_images.add(img_path)
        
        if len(self.table_images) > 0:
            self.logger.info(f"Collected {len(self.table_images)} table images (will be excluded)")
            if self.config.verbose:
                for idx, img_path in enumerate(sorted(self.table_images), 1):
                    self.logger.info(f"  {idx}. {img_path}")
    
    def _init_ocr(self):
        """初始化OCR引擎"""
        if self.config.min_text_len <= 0 or self.config.ocr_engine == "none":
            return None
        
        try:
            if self.config.ocr_engine in ["auto", "easyocr"]:
                import easyocr
                reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                def ocr_func(img):
                    import numpy as np
                    from PIL import Image as PILImage
                    if isinstance(img, PILImage.Image):
                        arr = np.array(img)
                    else:
                        arr = np.array(PILImage.open(img))
                    lines = reader.readtext(arr, detail=0)
                    return "\n".join(lines)
                self.logger.info("OCR engine initialized: easyocr")
                return ocr_func
        except Exception as e:
            self.logger.warning(f"Failed to initialize OCR: {e}")
        
        return None
    
    def filter_images(
        self, 
        content_list: List[Dict], 
        base_dir: Path
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        三级过滤：表格图片 -> 分辨率 -> OCR文本长度
        
        Returns:
            (valid_images, filtered_stats)
        """
        from PIL import Image as PILImage
        
        # 收集所有 image 类型
        all_images = [item for item in content_list if item.get("type") == "image"]
        
        # 排除表格图片
        non_table_images = [
            item for item in all_images 
            if item.get("img_path", "") not in self.table_images
        ]
        table_filtered = len(all_images) - len(non_table_images)
        
        # 分辨率阈值
        min_pixels = self.config.min_pixels or self.RES_PRESETS.get(self.config.res_preset, 280_000)
        
        # 分辨率过滤
        valid_images = []
        filtered_by_resolution = []
        filtered_by_text = []
        
        for item in non_table_images:
            img_path = item.get("img_path", "")
            if not img_path:
                continue
            
            full_path = base_dir / img_path
            if not full_path.exists():
                continue
            
            # 检查分辨率
            try:
                img = PILImage.open(full_path)
                w, h = img.size
                pixels = w * h
                
                if pixels < min_pixels:
                    filtered_by_resolution.append(item)
                    continue
            except Exception:
                continue
            
            # OCR文本过滤
            if self.config.min_text_len > 0 and self.ocr_func:
                try:
                    text = self.ocr_func(img)
                    if len(text or "") < self.config.min_text_len:
                        filtered_by_text.append(item)
                        continue
                except Exception:
                    pass  # OCR失败则保留图片
            
            valid_images.append(item)
        
        # 统计
        filtered_stats = {
            "total_images": len(all_images),
            "collected_table_images": len(self.table_images),
            "table_images_filtered_from_images": table_filtered,
            "filtered_by_resolution": len(filtered_by_resolution),
            "filtered_by_text_length": len(filtered_by_text),
            "valid_images": len(valid_images)
        }
        
        # 日志输出
        self.logger.info(f"Image filtering: {len(all_images)} total -> {len(valid_images)} valid")
        self.logger.info(f"  Excluded: {len(self.table_images)} table images (type=table)")
        self.logger.info(f"  Filtered: {len(filtered_by_resolution)} resolution + {len(filtered_by_text)} text")
        
        # 详细过滤信息（verbose模式）
        if self.config.verbose:
            if filtered_by_resolution:
                self.logger.info(f"  Resolution filtered ({min_pixels} pixels):")
                for item in filtered_by_resolution[:5]:  # 最多显示5个
                    self.logger.info(f"    - {item.get('img_path', 'unknown')}")
                if len(filtered_by_resolution) > 5:
                    self.logger.info(f"    ... and {len(filtered_by_resolution) - 5} more")
            
            if filtered_by_text:
                self.logger.info(f"  Text length filtered (< {self.config.min_text_len} chars):")
                for item in filtered_by_text[:5]:
                    self.logger.info(f"    - {item.get('img_path', 'unknown')}")
                if len(filtered_by_text) > 5:
                    self.logger.info(f"    ... and {len(filtered_by_text) - 5} more")
        
        return valid_images, filtered_stats


class ContextExtractor:
    """上下文提取器 - 从 content_list 中提取图片周围的文本信息"""
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def extract_caption(self, item: Dict[str, Any]) -> str:
        """提取图片标题和脚注"""
        caption_parts = []
        
        captions = item.get("image_caption", [])
        if captions:
            caption_parts.extend(captions)
        
        footnotes = item.get("image_footnote", [])
        if footnotes:
            caption_parts.extend(footnotes)
        
        return " ".join(caption_parts) if caption_parts else "无"
    
    def find_nearest_title(self, content_list: List[Dict], current_idx: int) -> str:
        """向前查找最近的标题"""
        for i in range(current_idx - 1, -1, -1):
            item = content_list[i]
            if item.get("type") == "text":
                text_level = item.get("text_level")
                if text_level in [1, 2]:
                    return item.get("text", "")
        return ""
    
    def extract_nearby_text(self, content_list: List[Dict], current_idx: int) -> str:
        """提取前后文本段落"""
        texts = []
        window = self.config.context_window
        
        # 向前取
        for i in range(current_idx - 1, max(0, current_idx - window - 1), -1):
            item = content_list[i]
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    texts.insert(0, text)
        
        # 向后取
        for i in range(current_idx + 1, min(len(content_list), current_idx + window + 1)):
            item = content_list[i]
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    texts.append(text)
        
        return " ".join(texts) if texts else "无"
    
    def extract_context(
        self, 
        content_list: List[Dict], 
        current_idx: int,
        item: Dict[str, Any]
    ) -> Dict[str, str]:
        """提取完整上下文"""
        return {
            "image_caption": self.extract_caption(item),
            "nearest_title": self.find_nearest_title(content_list, current_idx),
            "nearby_text": self.extract_nearby_text(content_list, current_idx)
        }


class MultimodalDescriptor:
    """多模态描述生成器 - 使用 VL 模型生成图片描述"""
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = self._init_model()
        self.prompt_template = self._load_prompt()
    
    def _init_model(self) -> ChatOpenAI:
        """初始化多模态模型"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("缺少环境变量: DASHSCOPE_API_KEY")
        
        return ChatOpenAI(
            model=self.config.multimodal_model,
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=self.config.temperature
        )
    
    def _load_prompt(self) -> str:
        """加载提示词模板"""
        prompt_path = Path(__file__).parent / "prompts" / "image_description.txt"
        if not prompt_path.exists():
            self.logger.warning(f"提示词文件不存在: {prompt_path}，使用默认提示词")
            return self._get_default_prompt()
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _get_default_prompt(self) -> str:
        """默认提示词"""
        return """请分析图片并输出JSON格式的描述。

**重要**: 输出的JSON中不要使用反斜杠 \\ 字符，请用正斜杠 / 或顿号代替。

格式：
{{
  "entity_name": "图片核心实体名称",
  "type": "图片类型",
  "description": "详细描述（不超过100字，避免使用反斜杠）"
}}

上下文信息：
{context_text}
"""
    
    def _encode_image(self, image_path: Path) -> str:
        """将图片编码为 base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _parse_llm_response(self, response_text: str) -> Optional[ImageDescription]:
        """解析 LLM 返回的 JSON（鲁棒性处理 + 反斜杠修复）"""
        # 1. 尝试提取 JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 2. 尝试查找 {...} 结构
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                self.logger.error(f"无法从响应中提取 JSON: {response_text[:200]}")
                return None
        
        # 3. 解析 JSON（带反斜杠修复）
        try:
            data = json.loads(json_str)
            return ImageDescription(**data)
        except json.JSONDecodeError as e:
            # 尝试修复非法反斜杠（如 产品\技术 -> 产品/技术）
            self.logger.warning(f"JSON 解析失败，尝试修复反斜杠: {e}")
            try:
                # 替换非法转义序列（保留合法的 \n \t \" 等）
                fixed_json = re.sub(r'\\(?!["\\/bfnrtu])', '/', json_str)
                data = json.loads(fixed_json)
                self.logger.info("成功修复反斜杠问题")
                return ImageDescription(**data)
            except Exception as e2:
                self.logger.error(f"修复后仍失败: {e2}\n原始响应: {json_str[:200]}")
                return None
        except Exception as e:
            self.logger.error(f"构造 ImageDescription 失败: {e}\nJSON数据: {data}")
            return None
    
    def generate_description(
        self, 
        image_path: Path, 
        context: Dict[str, str]
    ) -> Optional[ImageDescription]:
        """生成图片描述"""
        # 构造上下文文本
        context_text = f"""
图片标题/名称：{context.get('image_caption', '无')}
所在章节：{context.get('nearest_title', '无')}
周围文本：{context.get('nearby_text', '无')}
"""
        
        # 填充提示词
        prompt = self.prompt_template.format(
            image_caption=context.get('image_caption', '无'),
            context_text=context_text
        )
        
        # 编码图片
        try:
            image_base64 = self._encode_image(image_path)
        except Exception as e:
            self.logger.error(f"图片编码失败 {image_path}: {e}")
            return None
        
        # 调用 LLM（带重试）
        for attempt in range(self.config.max_retries):
            try:
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                )
                
                response = self.model.invoke([message])
                response_text = response.content
                
                # 解析响应
                description = self._parse_llm_response(response_text)
                if description:
                    return description
                else:
                    self.logger.warning(f"第 {attempt + 1} 次尝试解析失败，重试...")
                    time.sleep(1)
            
            except Exception as e:
                self.logger.error(f"LLM 调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None


class ImageEntityExtractor:
    """
    图片实体提取器 - 使用 LLM 从描述中提取实体，并对齐到 Ontology
    
    两阶段处理：
    1. 使用 Text LLM 从图片描述中提取原始实体
    2. 使用 OntologyAligner 对齐到核心实体类型
    """
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = self._init_llm()
        self.prompt_template = self._load_entity_extraction_prompt()
        self._ontology_aligner = None  # 延迟加载
    
    def _init_llm(self) -> ChatOpenAI:
        """初始化实体提取 LLM"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("缺少环境变量: DASHSCOPE_API_KEY")
        
        return ChatOpenAI(
            model=self.config.entity_extraction_model,
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.1
        )
    
    def _load_entity_extraction_prompt(self) -> str:
        """加载实体提取提示词"""
        prompt_path = Path(__file__).parent / "prompts" / "image_entity_extraction.txt"
        if not prompt_path.exists():
            self.logger.warning(f"实体提取提示词不存在: {prompt_path}，使用默认提示词")
            return self._get_default_entity_prompt()
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _get_default_entity_prompt(self) -> str:
        """默认实体提取提示词"""
        return """请从以下图片描述中提取实体和关系，输出JSON格式。

图片名称：{entity_name}
图片类型：{type}
描述：{description}

输出格式：
{{
  "entities": [
    {{"name": "实体名", "type": "实体类型", "description": "描述", "attributes": {{}}}}
  ],
  "relations": [
    {{"source": "源", "target": "目标", "type": "关系类型", "description": "描述"}}
  ]
}}
"""
    
    def _get_ontology_aligner(self):
        """延迟加载 OntologyAligner（复用 text_pipeline）"""
        if self._ontology_aligner is None:
            try:
                from pipelines.text_pipeline import OntologyAligner
                # OntologyAligner() 无参数构造
                self._ontology_aligner = OntologyAligner()
                self.logger.info("成功加载 OntologyAligner from text_pipeline")
            except Exception as e:
                self.logger.error(f"加载 OntologyAligner 失败: {e}")
                self._ontology_aligner = None
        
        return self._ontology_aligner
    
    def extract_entities_from_description(
        self,
        description: ImageDescription,
        img_path: str,
        page_idx: Optional[int]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        从图片描述中提取实体和关系（原始版本，未对齐）
        
        Returns:
            (raw_entities, raw_relations)
        """
        # 构造提示词
        prompt = self.prompt_template.format(
            entity_name=description.entity_name,
            type=description.type,
            description=description.description
        )
        
        # 调用 LLM
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content
            
            # 解析 JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                self.logger.warning(f"无法从 LLM 响应中提取 JSON: {response_text[:200]}")
                return [], []
            
            data = json.loads(json_match.group(0))
            
            # 提取实体和关系
            raw_entities = []
            for ent in data.get("entities", []):
                raw_entities.append({
                    "name": ent.get("name", ""),
                    "type": ent.get("type", "Other"),
                    "description": ent.get("description", ""),
                    "attributes": ent.get("attributes", {}),
                    "source_image": img_path,
                    "page_idx": page_idx
                })
            
            raw_relations = []
            for rel in data.get("relations", []):
                raw_relations.append({
                    "source_entity": rel.get("source", ""),
                    "target_entity": rel.get("target", ""),
                    "relation_type": rel.get("type", "unknown"),
                    "description": rel.get("description", ""),
                    "confidence": 1.0,
                    "source_image": img_path
                })
            
            return raw_entities, raw_relations
        
        except Exception as e:
            self.logger.error(f"实体提取失败: {e}")
            return [], []
    
    def align_entities(self, raw_entities: List[Dict]) -> Dict[str, Dict]:
        """
        对齐实体到 Ontology 核心类型
        
        Args:
            raw_entities: 原始实体列表
            
        Returns:
            字典，key为实体名，value为对齐后的实体信息
        """
        aligner = self._get_ontology_aligner()
        if not aligner:
            self.logger.warning("OntologyAligner 未加载，返回原始实体")
            # 转换为字典格式
            return {entity["name"]: entity for entity in raw_entities}
        
        # 转换为text_pipeline的Entity格式
        from pipelines.text_pipeline import Entity, EntityAttribute
        
        entities_dict = {}
        for entity_data in raw_entities:
            # 构造Entity对象
            entity = Entity(
                name=entity_data["name"],
                type=entity_data["type"],
                description=entity_data.get("description", ""),
                attributes=[
                    EntityAttribute(name=k, value=v)
                    for k, v in entity_data.get("attributes", {}).items()
                ]
            )
            entities_dict[entity.name] = entity
        
        # 调用text_pipeline的align_entities方法
        try:
            aligned_entities = aligner.align_entities(entities_dict)
            self.logger.info(f"成功对齐 {len(aligned_entities)} 个实体")
            
            # 转换为字典格式，添加source_image信息
            result = {}
            for name, aligned_entity in aligned_entities.items():
                entity_dict = aligned_entity.model_dump(exclude_none=True)
                # 找回原始的source_image信息
                orig = next((e for e in raw_entities if e["name"] == name), None)
                if orig:
                    entity_dict["source_image"] = orig.get("source_image")
                    entity_dict["page_idx"] = orig.get("page_idx")
                result[name] = entity_dict
            
            return result
        except Exception as e:
            self.logger.error(f"对齐失败: {e}，返回原始实体")
            return {entity["name"]: entity for entity in raw_entities}


class ImageKnowledgeGraphPipeline:
    """
    图片知识图谱流水线（完整流程）
    
    流程：
    1. 加载 content_list.json
    2. EnhancedImageFilter 过滤图片
    3. 提取上下文 + 生成描述
    4. 保存 Raw 文件（图片描述）
    5. 提取实体 + 对齐
    6. 保存 Aligned 文件（知识图谱）
    """
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.filter = EnhancedImageFilter(config)
        self.context_extractor = ContextExtractor(config)
        self.descriptor = MultimodalDescriptor(config)
        self.entity_extractor = ImageEntityExtractor(config)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load_content_list(self, input_path: Path) -> List[Dict]:
        """加载 content_list.json"""
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def run(self, input_path: str, output_dir: Optional[str] = None) -> None:
        """执行完整流程"""
        start_time = time.time()
        
        input_path = Path(input_path)
        base_dir = input_path.parent
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = base_dir
        
        # 1. 加载数据
        self.logger.info("=" * 60)
        self.logger.info("开始图片知识图谱提取")
        self.logger.info("=" * 60)
        self.logger.info(f"加载文件: {input_path}")
        content_list = self.load_content_list(input_path)
        self.logger.info(f"总条目数: {len(content_list)}")
        
        # 2. 收集表格图片
        self.filter.collect_table_images(content_list)
        
        # 3. 过滤图片
        valid_images, filtered_stats = self.filter.filter_images(content_list, base_dir)
        
        if len(valid_images) == 0:
            self.logger.warning("没有有效的图片，退出处理")
            return
        
        # 4. 处理图片
        self.logger.info(f"开始处理 {len(valid_images)} 个有效图片...")
        self.logger.info("=" * 60)
        
        raw_image_data = []
        all_raw_entities = []
        all_raw_relations = []
        
        total_images = len(valid_images)
        
        # 使用 tqdm 进度条（非 verbose 模式）或详细日志（verbose 模式）
        iterator = enumerate(valid_images)
        if not self.config.verbose:
            iterator = tqdm(
                enumerate(valid_images),
                total=total_images,
                desc="处理图片",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )
        
        for idx, item in iterator:
            try:
                image_result = self.process_single_image(content_list, item, base_dir, idx, total_images)
                
                if image_result:
                    raw_image_data.append(image_result["raw_data"])
                    all_raw_entities.extend(image_result["raw_entities"])
                    all_raw_relations.extend(image_result["raw_relations"])
                    
            except Exception as e:
                img_path = item.get('img_path', 'unknown')
                self.logger.error(f"  ✗ 图片处理失败 ({img_path}): {e}")
        
        self.logger.info("=" * 60)
        self.logger.info(f"✓ 处理完成 | 成功: {len(raw_image_data)}/{total_images} | 实体: {len(all_raw_entities)} | 关系: {len(all_raw_relations)}")
        
        # 5. 实体对齐
        self.logger.info("=" * 60)
        self.logger.info(f"开始实体对齐 ({len(all_raw_entities)} 个原始实体)...")
        aligned_entities = self.entity_extractor.align_entities(all_raw_entities)
        
        # 统计对齐后的实体类型分布
        aligned_type_counts = {}
        for entity in aligned_entities.values():
            core_type = entity.get("core_type", "Other")
            aligned_type_counts[core_type] = aligned_type_counts.get(core_type, 0) + 1
        
        self.logger.info(f"✓ 对齐完成 | 对齐后实体: {len(aligned_entities)}")
        if aligned_type_counts:
            type_summary = ", ".join([f"{k}:{v}" for k, v in sorted(aligned_type_counts.items())])
            self.logger.info(f"  类型分布: {type_summary}")
        
        # 6. 保存输出
        self.logger.info("=" * 60)
        output_files = self.save_outputs(
            raw_image_data=raw_image_data,
            raw_entities=all_raw_entities,
            raw_relations=all_raw_relations,
            aligned_entities=aligned_entities,
            input_path=input_path,
            output_dir=output_dir,
            filtered_stats=filtered_stats
        )
        
        # 7. 总结
        elapsed_time = time.time() - start_time
        self.logger.info("=" * 60)
        self.logger.info(f"✓ 图片知识图谱提取完成")
        self.logger.info(f"  耗时: {elapsed_time:.2f}秒")
        self.logger.info(f"  输出文件:")
        self.logger.info(f"    - Raw: {output_files['raw']}")
        self.logger.info(f"    - Aligned: {output_files['aligned']}")
        self.logger.info("=" * 60)
    
    def process_single_image(
        self, 
        content_list: List[Dict], 
        item: Dict,
        base_dir: Path,
        img_idx: int = 0,
        total_images: int = 0
    ) -> Optional[Dict]:
        """
        处理单张图片
        
        Returns:
            {
                "raw_data": {...},  # 图片描述数据
                "raw_entities": [...],  # 原始实体
                "raw_relations": [...]  # 原始关系
            }
        """
        img_path = item.get("img_path", "")
        full_path = base_dir / img_path
        page_idx = item.get("page_idx")
        
        # 日志：处理开始
        if self.config.verbose:
            self.logger.info(f"[{img_idx+1}/{total_images}] 处理图片: {img_path} (页码: {page_idx})")
        
        # 找到图片在 content_list 中的索引
        idx = next(
            (i for i, x in enumerate(content_list) if x.get("img_path") == img_path),
            -1
        )
        if idx == -1:
            return None
        
        # 提取上下文
        context = self.context_extractor.extract_context(content_list, idx, item)
        
        # 生成描述
        description = self.descriptor.generate_description(full_path, context)
        if not description:
            if self.config.verbose:
                self.logger.warning(f"  ✗ 描述生成失败")
            return None
        
        # 构造 raw 数据
        raw_data = {
            "img_path": img_path,
            "page_idx": page_idx,
            "entity_name": description.entity_name,
            "type": description.type,
            "description": description.description,  # ⭐改名
            "context": context
        }
        
        # 提取实体和关系
        raw_entities, raw_relations = self.entity_extractor.extract_entities_from_description(
            description, img_path, page_idx
        )
        
        # 日志：提取结果
        if self.config.verbose:
            self.logger.info(f"  ✓ {description.entity_name} | "
                           f"实体: {len(raw_entities)} | 关系: {len(raw_relations)}")
        
        return {
            "raw_data": raw_data,
            "raw_entities": raw_entities,
            "raw_relations": raw_relations
        }
    
    def save_outputs(
        self,
        raw_image_data: List[Dict],
        raw_entities: List[Dict],
        raw_relations: List[Dict],
        aligned_entities: Dict[str, Dict],
        input_path: Path,
        output_dir: Path,
        filtered_stats: Dict
    ) -> Dict[str, str]:
        """保存输出文件（两个独立文件，格式与text_pipeline一致），返回文件路径"""
        
        # 1. 保存 Raw 版本（与text_pipeline一致）
        # 将raw_entities转换为字典格式
        entities_dict = {entity["name"]: entity for entity in raw_entities}
        
        # 统计实体类型
        entity_types = list(set(e["type"] for e in raw_entities))
        relation_types = list(set(r["relation_type"] for r in raw_relations))
        
        raw_output = {
            "metadata": {
                "source_file": str(input_path),
                "total_images": len(raw_image_data),
                "total_entities": len(raw_entities),
                "total_relations": len(raw_relations),
                "entity_types": entity_types,
                "relation_types": relation_types,
                "filtered_stats": filtered_stats,
                "config": {
                    "multimodal_model": self.config.multimodal_model,
                    "entity_extraction_model": self.config.entity_extraction_model,
                    "context_window": self.config.context_window,
                    "ocr_engine": self.config.ocr_engine,
                    "res_preset": self.config.res_preset
                },
                "build_time": datetime.now().isoformat()
            },
            "images": raw_image_data,  # 图片描述信息
            "entities": entities_dict,  # ⭐字典格式，与text_pipeline一致
            "relations": raw_relations
        }
        
        raw_path = output_dir / input_path.name.replace(
            "_content_list.json", 
            "_image_kg_raw.json"
        )
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_output, f, ensure_ascii=False, indent=2)
        self.logger.info(f"✓ 保存原始数据: {raw_path.name}")
        
        # 2. 保存 Aligned 版本（与text_pipeline一致）
        aligned_entity_types = list(set(
            e.get("core_type", e.get("type", "Other")) 
            for e in aligned_entities.values()
        ))
        
        kg_output = {
            "metadata": {
                "source_file": str(input_path),
                "total_aligned_entities": len(aligned_entities),
                "total_aligned_relations": len(raw_relations),
                "aligned_entity_types": aligned_entity_types,
                "aligned_relation_types": relation_types,
                "build_time": datetime.now().isoformat(),
                "ontology_version": "v1.2.1",
                "core_entity_types": [
                    "Company", "Person", "Technology", "Product", 
                    "TagConcept", "Event", "Signal", "Other"
                ],
                "data_source": "image_pipeline"
            },
            "aligned_entities": aligned_entities,  # ⭐字典格式
            "aligned_relations": raw_relations  # TODO: 关系也需要对齐
        }
        
        kg_path = output_dir / input_path.name.replace(
            "_content_list.json",
            "_image_kg_aligned.json"
        )
        with open(kg_path, "w", encoding="utf-8") as f:
            json.dump(kg_output, f, ensure_ascii=False, indent=2)
        self.logger.info(f"✓ 保存对齐数据: {kg_path.name}")
        
        # 返回文件名（不含路径，便于日志输出）
        return {
            "raw": raw_path.name,
            "aligned": kg_path.name
        }


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="图片知识图谱处理流水线")
    parser.add_argument(
        "input_file",
        help="输入的 content_list.json 文件路径"
    )
    parser.add_argument(
        "--output-dir",
        help="输出目录（默认与输入文件同目录）"
    )
    parser.add_argument(
        "--ocr-engine",
        default="auto",
        choices=["auto", "pytesseract", "easyocr", "paddleocr", "none"],
        help="OCR 引擎"
    )
    parser.add_argument(
        "--res-preset",
        default="s",
        choices=["s", "m", "l", "off"],
        help="分辨率预设"
    )
    parser.add_argument(
        "--min-text-len",
        type=int,
        default=10,
        help="最小 OCR 文本长度"
    )
    parser.add_argument(
        "--context-window",
        type=int,
        default=2,
        help="上下文窗口大小"
    )
    parser.add_argument(
        "--multimodal-model",
        default="qwen3-vl-flash",
        help="多模态模型"
    )
    parser.add_argument(
        "--entity-model",
        default="qwen-plus",
        help="实体提取模型"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    # 构造配置
    config = ImagePipelineConfig(
        ocr_engine=args.ocr_engine,
        res_preset=args.res_preset,
        min_text_len=args.min_text_len,
        context_window=args.context_window,
        multimodal_model=args.multimodal_model,
        entity_extraction_model=args.entity_model,
        verbose=args.verbose,
        output_dir=args.output_dir
    )
    
    # 执行流水线
    pipeline = ImageKnowledgeGraphPipeline(config)
    pipeline.run(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
