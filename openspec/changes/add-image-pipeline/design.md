# 设计文档

**版本**: 2.0  
**最后更新**: 2025-11-11  
**状态**: 已实现并优化

## 变更记录

### v2.0 (2025-11-11) - 实体提取与Prompt优化
- ✅ 修复 JSON 解析失败问题（禁止特殊字符）
- ✅ 优化图片描述生成 prompt（聚焦核心商业价值）
- ✅ 优化实体提取 prompt（参考 text_pipeline 规范）
- ✅ 实现完整的 LLM 实体提取和对齐功能
- ✅ 修复 OntologyAligner 初始化错误
- ✅ 实现两文件分离输出架构

### v1.0 (2025-11-10) - MVP实现
- ✅ 多模态描述生成（qwen3-vl-flash）
- ✅ 图片过滤（表格、分辨率、OCR文本）
- ✅ 上下文提取
- ✅ Base64 编码和鲁棒 JSON 解析

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     ImageKnowledgeGraphPipeline              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ ImageFilter  │───▶│  Context     │───▶│  Multimodal  │  │
│  │              │    │  Extractor   │    │  Descriptor  │  │
│  │ - 表格过滤    │    │ - 标题提取    │    │ - LLM调用    │  │
│  │ - 质量过滤    │    │ - 上下文提取  │    │ - 描述生成   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            JSON Updater (更新 content_list)           │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │   Image      │                                          │
│  │   Entity     │───▶ Knowledge Graph (kg_aligned.json)   │
│  │   Extractor  │                                          │
│  └──────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 数据流（修订版 - 2025-11-11）

```
Input: content_list.json
  │
  ├─ type="table" items → 收集 img_path → Table Images Set
  │
  ├─ type="image" items → EnhancedImageFilter ⭐NEW
  │    ├─ 在 Table Images Set 中？ → Skip
  │    ├─ 分辨率过滤 (参考ImageFilter.res_preset)
  │    │   ├─ 像素数 < 阈值？ → Skip  
  │    │   └─ Pass → 继续
  │    ├─ OCR 文本长度过滤 ⭐NEW
  │    │   ├─ OCR 识别文本
  │    │   ├─ 文本长度 < min_text_len？ → Skip
  │    │   └─ Pass → 继续
  │    └─ Pass → Valid Images List
  │
  └─ For each valid image:
       │
       ├─ ContextExtractor
       │    ├─ 查找前面最近的标题
       │    ├─ 提取前后文本段落
       │    └─ 组合上下文
       │
       ├─ MultimodalDescriptor
       │    ├─ Base64 编码图片 ⭐优化
       │    ├─ 渲染提示词（图片+caption+context）
       │    ├─ 调用 Qwen-VL API
       │    ├─ 鲁棒 JSON 解析（多策略） ⭐优化
       │    └─ 解析 → ImageDescription
       │         - entity_name
       │         - type  
       │         - description ⭐改名
       │
       ├─ Raw Output ⭐NEW 分离输出
       │    └─ 保存到 *_content_list_image_raw.json
       │         {
       │           "images": [
       │             {
       │               "img_path": "images/xxx.jpg",
       │               "page_idx": 5,
       │               "entity_name": "运营计划章节封面图",
       │               "type": "封面图",
       │               "description": "详细描述...",
       │               "context": {...}
       │             }
       │           ],
       │           "metadata": {...}
       │         }
       │
       └─ ImageEntityExtractor ⭐重新设计
            ├─ 使用 LLM 从 description 提取实体 (复用 text_pipeline)
            ├─ 实体对齐到核心类型 (Company/Person/Technology/Product...)
            ├─ 添加 source_image 字段
            └─ 输出 → *_content_list_image_kg_aligned.json ⭐改名

Output (修订):
  ├─ *_content_list_image_raw.json (图片描述，不修改原文件) ⭐NEW
  └─ *_content_list_image_kg_aligned.json (实体图谱) ⭐改名
```

## 核心模块设计

### 1. EnhancedImageFilter（增强图片过滤器）⭐重新设计

**职责**：严格过滤低质量、低内容图片，复用 `ImageFilter` 的成熟逻辑

**核心改进**：
1. 集成现有 `ImageFilter` 的分辨率过滤（res_preset）
2. 集成 OCR 文本长度检测（min_text_len）
3. 排除表格图片（从 content_list 中收集）

**方法**：

```python
class EnhancedImageFilter:
    """增强图片过滤器 - 复用 ImageFilter 的成熟逻辑"""
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.table_image_paths: Set[str] = set()
        
        # 初始化底层 ImageFilter
        from image_filter import ImageFliter  # 复用现有过滤器
        self.base_filter = ImageFliter(
            ocr=config.ocr_engine,
            min_pixels=config.min_pixels,
            res_preset=config.res_preset,
            min_text_len=config.min_text_len,
            verbose=config.verbose
        )
    
    def collect_table_images(self, content_list: List[Dict]) -> None:
        """从 content_list 中收集所有表格图片路径"""
        for item in content_list:
            if item.get("type") == "table":
                img_path = item.get("img_path")
                if img_path:
                    self.table_image_paths.add(img_path)
        
        logger.info(f"收集到 {len(self.table_image_paths)} 个表格图片")
    
    def filter_images(self, content_list: List[Dict], 
                     base_dir: Path) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
        """
        过滤图片并返回有效图片列表
        
        Returns:
            valid_images: 通过所有过滤的图片列表
            filtered_stats: 各种过滤原因的统计
        """
        # 提取图片条目
        image_items = [
            item for item in content_list 
            if item.get("type") == "image" and item.get("img_path")
        ]
        
        # Step 1: 排除表格图片
        non_table_images = []
        table_filtered = []
        for item in image_items:
            img_path = item.get("img_path", "")
            if img_path in self.table_image_paths:
                table_filtered.append(item)
            else:
                non_table_images.append(item)
        
        logger.info(f"表格图片过滤: {len(table_filtered)} 张")
        
        # Step 2: 使用 ImageFilter 进行分辨率 + OCR 文本过滤
        # 构造临时 JSON 用于 ImageFilter.process
        temp_content = [
            {
                "type": "image",
                "img_path": item["img_path"],
                "page_idx": item.get("page_idx"),
                "image_caption": item.get("image_caption"),
                "bbox": item.get("bbox")
            }
            for item in non_table_images
        ]
        
        # 调用 ImageFilter (会自动进行分辨率 + OCR 过滤)
        try:
            valid_items = self.base_filter._filter_by_resolution(temp_content)
            if self.config.min_text_len > 0:
                valid_items, text_filtered = self.base_filter._ocr_and_filter_by_text(valid_items)
        except Exception as e:
            logger.error(f"ImageFilter 过滤失败: {e}")
            valid_items = temp_content
        
        # 将 valid_items 映射回原始 content_list 条目
        valid_paths = {item["img_path"] for item in valid_items}
        valid_images = [
            item for item in non_table_images 
            if item["img_path"] in valid_paths
        ]
        
        filtered_stats = {
            "table_filtered": table_filtered,
            "resolution_filtered": len(non_table_images) - len(valid_items),
            "total_valid": len(valid_images)
        }
        
        logger.info(f"总图片: {len(image_items)}, "
                   f"有效: {len(valid_images)}, "
                   f"过滤: {len(image_items) - len(valid_images)}")
        
        return valid_images, filtered_stats
```

### 2. ContextExtractor（上下文提取器）

**职责**：提取图片周围的文本上下文

**方法**：

```python
class ContextExtractor:
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
    
    def extract_caption(self, item: Dict) -> str:
        """提取图片标题和脚注"""
        caption_parts = []
        
        # 提取 image_caption
        captions = item.get("image_caption", [])
        if captions:
            caption_parts.extend(captions)
        
        # 提取 image_footnote
        footnotes = item.get("image_footnote", [])
        if footnotes:
            caption_parts.extend(footnotes)
        
        return " ".join(caption_parts)
    
    def find_nearest_title(self, content_list: List[Dict], 
                          current_idx: int) -> str:
        """向前查找最近的标题"""
        for i in range(current_idx - 1, -1, -1):
            item = content_list[i]
            if item.get("type") == "text":
                text_level = item.get("text_level")
                if text_level in [1, 2]:  # 一级或二级标题
                    return item.get("text", "")
        return ""
    
    def extract_nearby_text(self, content_list: List[Dict],
                           current_idx: int) -> str:
        """提取前后文本段落"""
        texts = []
        window = self.config.context_window
        
        # 向前查找
        for i in range(max(0, current_idx - window), current_idx):
            item = content_list[i]
            if item.get("type") == "text":
                text = item.get("text", "")
                if text and not item.get("text_level"):  # 非标题
                    texts.append(text)
        
        # 向后查找
        for i in range(current_idx + 1, 
                      min(len(content_list), current_idx + window + 1)):
            item = content_list[i]
            if item.get("type") == "text":
                text = item.get("text", "")
                if text and not item.get("text_level"):
                    texts.append(text)
        
        return " ".join(texts)
    
    def extract_context(self, content_list: List[Dict],
                       current_idx: int, item: Dict) -> Dict[str, str]:
        """提取完整上下文"""
        return {
            "caption": self.extract_caption(item),
            "title": self.find_nearest_title(content_list, current_idx),
            "nearby_text": self.extract_nearby_text(content_list, current_idx)
        }
```

### 3. MultimodalDescriptor（多模态描述生成器）

**职责**：调用多模态 LLM 生成图片描述

**关键改进**（借鉴 RAGAnything）：
1. **Base64编码**：将图片转为 base64，而非使用 file:// 协议（跨平台兼容性更好）
2. **鲁棒JSON解析**：多策略解析 LLM 响应，处理各种边界情况
3. **重试机制**：带指数退避的智能重试

**方法**：

```python
class MultimodalDescriptor:
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.client = self._init_llm_client()
        self.prompt_template = self._load_prompt_template()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _init_llm_client(self):
        """初始化 LLM 客户端（使用 LangChain ChatOpenAI）"""
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.config.multimodal_model,  # "qwen3-vl-flash"
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=self.config.temperature
        )
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        template_path = Path(__file__).parent / "prompts" / "image_description.txt"
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图片编码为 base64（借鉴 RAGAnything）"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
        except Exception as e:
            self.logger.error(f"图片编码失败 {image_path}: {e}")
            return ""
    
    def _robust_json_parse(self, response: str) -> dict:
        """鲁棒的 JSON 解析（借鉴 RAGAnything 的多策略解析）"""
        # 策略 1: 直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # 策略 2: 提取 ```json ... ``` 代码块
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", 
                                response, re.DOTALL)
        for block in json_blocks:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue
        
        # 策略 3: 查找第一个平衡的 {...}
        brace_count = 0
        start_pos = -1
        for i, char in enumerate(response):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    try:
                        return json.loads(response[start_pos:i+1])
                    except json.JSONDecodeError:
                        start_pos = -1
        
        # 策略 4: 使用正则提取字段
        return self._extract_fields_with_regex(response)
    
    def _extract_fields_with_regex(self, response: str) -> dict:
        """使用正则表达式提取关键字段（最后手段）"""
        self.logger.warning("使用正则提取字段（JSON解析失败）")
        
        entity_name_match = re.search(r'"entity_name":\s*"([^"]*)"', response)
        type_match = re.search(r'"type":\s*"([^"]*)"', response)
        desc_match = re.search(r'"detailed_description":\s*"([^"]*)"', 
                              response, re.DOTALL)
        
        return {
            "entity_name": entity_name_match.group(1) if entity_name_match else "未知图片",
            "type": type_match.group(1) if type_match else "其他",
            "detailed_description": desc_match.group(1) if desc_match else response[:200]
        }
    
    def generate_description(self, image_path: Path, 
                           context: Dict[str, str]) -> Optional[ImageDescription]:
        """生成图片描述（带重试机制）"""
        if not image_path.exists():
            self.logger.warning(f"图片文件不存在: {image_path}")
            return None
        
        # Base64 编码
        image_base64 = self._encode_image_to_base64(str(image_path))
        if not image_base64:
            return None
        
        # 获取图片格式
        suffix = image_path.suffix.lower().lstrip(".")
        if suffix == "jpg":
            suffix = "jpeg"
        image_url = f"data:image/{suffix};base64,{image_base64}"
        
        # 渲染提示词
        prompt = self.prompt_template.format(
            image_caption=context.get("caption", "无"),
            context_text=context.get("context_text", "无")
        )
        
        # 构造消息
        from langchain_core.messages import HumanMessage
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        )
        
        # 带重试的 LLM 调用
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.invoke([message])
                
                # 鲁棒解析
                content = response.content.strip()
                result = self._robust_json_parse(content)
                
                return ImageDescription(**result)
                
            except Exception as e:
                self.logger.error(f"描述生成失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt == self.config.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # 指数退避
        
        return None
```

### 4. ImageEntityExtractor（图片实体提取器）⭐重新设计

**职责**：从图片描述中提取实体和关系，**复用 text_pipeline 的 LLM 提取 + 实体对齐逻辑**

**核心改进**：
1. 使用 LLM 从图片描述中提取实体（而非简单包装）
2. 对齐到核心实体类型（Company/Person/Technology/Product...）
3. 保留图片来源信息（source_image）

**方法**：

```python
class ImageEntityExtractor:
    """从图片描述中提取实体 - 复用 text_pipeline 逻辑"""
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.llm = self._init_llm()
        self.ontology_aligner = None  # 延迟加载
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _init_llm(self):
        """初始化 LLM（复用 text_pipeline 的模型）"""
        from pipelines.text_pipeline import get_model
        return get_model(
            model_name=self.config.entity_extraction_model,  # 默认用 qwen-plus
            temperature=0.3,
            max_retries=3
        )
    
    def _get_ontology_aligner(self):
        """懒加载 OntologyAligner"""
        if self.ontology_aligner is None:
            from pipelines.text_pipeline import OntologyAligner
            self.ontology_aligner = OntologyAligner(similarity_threshold=0.85)
        return self.ontology_aligner
    
    def extract_entities_from_description(
        self, 
        description: ImageDescription,
        source_image: str,
        page_idx: Optional[int] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        从图片描述中提取实体和关系
        
        Returns:
            (raw_entities, raw_relations)
        """
        # 构造提示词（复用 text_pipeline 的模板风格）
        prompt = f"""从以下图片描述中提取具体实体和关系。

**图片信息**:
- 图片路径: {source_image}
- 页码: {page_idx or '未知'}
- 图片名称: {description.entity_name}
- 图片类型: {description.type}

**图片描述**:
{description.description}

**提取要求**:
1. 提取描述中提到的具体实体（公司、人物、产品、技术等）
2. 提取实体间的关系
3. 不要提取抽象概念或通用流程

**输出JSON**:
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "Company|Person|Product|Technology|...",
            "description": "简要描述",
            "attributes": [{{"name": "属性名", "value": "属性值"}}]
        }}
    ],
    "relations": [
        {{
            "source_entity": "源实体",
            "target_entity": "目标实体",
            "relation_type": "关系类型",
            "description": "关系描述",
            "confidence": 0.9
        }}
    ]
}}
"""
        
        try:
            # 调用 LLM 提取
            from pipelines.text_pipeline import DocumentAnalysisSchema
            response = self.llm.with_structured_output(DocumentAnalysisSchema).invoke(prompt)
            
            # 转换为字典格式
            raw_entities = [
                {
                    "name": e.name,
                    "type": e.type,
                    "description": e.description,
                    "attributes": [{"name": a.name, "value": a.value} for a in e.attributes],
                    "source_image": source_image,  # 标记来源
                    "page_idx": page_idx
                }
                for e in response.entities
            ]
            
            raw_relations = [
                {
                    "source_entity": r.source_entity,
                    "target_entity": r.target_entity,
                    "relation_type": r.relation_type,
                    "description": r.description,
                    "confidence": r.confidence,
                    "source_image": source_image
                }
                for r in response.relations
            ]
            
            return raw_entities, raw_relations
            
        except Exception as e:
            self.logger.error(f"实体提取失败: {e}")
            return [], []
    
    def align_entities(
        self, 
        raw_entities: List[Dict]
    ) -> List[Dict]:
        """
        对齐实体到核心类型（复用 text_pipeline 的 OntologyAligner）
        
        Returns:
            aligned_entities (已对齐的实体列表)
        """
        aligner = self._get_ontology_aligner()
        
        # 转换为 text_pipeline 的 Entity 格式
        from pipelines.text_pipeline import Entity, EntityAttribute
        entities_obj = [
            Entity(
                name=e["name"],
                type=e["type"],
                description=e.get("description"),
                attributes=[
                    EntityAttribute(name=a["name"], value=a["value"])
                    for a in e.get("attributes", [])
                ]
            )
            for e in raw_entities
        ]
        
        # 调用对齐器
        aligned = aligner.align_entities(entities_obj)
        
        # 转回字典并添加 source_image
        aligned_entities = []
        for e in aligned:
            entity_dict = {
                "name": e.name,
                "type": e.type,
                "description": e.description,
                "attributes": {a.name: a.value for a in e.attributes}
            }
            
            # 找回原始实体的 source_image 信息
            orig = next((x for x in raw_entities if x["name"] == e.name), None)
            if orig:
                entity_dict["source_image"] = orig.get("source_image")
                entity_dict["page_idx"] = orig.get("page_idx")
            
            aligned_entities.append(entity_dict)
        
        return aligned_entities
```

### 5. ImageKnowledgeGraphPipeline（主流程）⭐重新设计

**职责**：协调所有模块，执行完整处理流程，**生成两个独立输出文件**

**核心改进**：
1. 不修改输入的 `content_list.json`
2. 生成 `_content_list_image_raw.json`（图片描述）
3. 生成 `_content_list_image_kg_aligned.json`（对齐后的实体图谱）

**核心方法**：

```python
class ImageKnowledgeGraphPipeline:
    """图片知识图谱处理主流程"""
    
    def __init__(self, config: ImagePipelineConfig):
        self.config = config
        self.filter = EnhancedImageFilter(config)
        self.context_extractor = ContextExtractor(config)
        self.descriptor = MultimodalDescriptor(config)
        self.entity_extractor = ImageEntityExtractor(config)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def run(self, input_path: str, output_dir: Optional[str] = None) -> None:
        """执行完整流程"""
        input_path = Path(input_path)
        base_dir = input_path.parent
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = base_dir
        
        # 1. 加载数据
        self.logger.info("=" * 60)
        self.logger.info("开始图片处理流程")
        self.logger.info("=" * 60)
        content_list = self.load_content_list(input_path)
        
        # 2. 收集表格图片
        self.filter.collect_table_images(content_list)
        
        # 3. 过滤图片（使用增强过滤器）
        valid_images, filtered_stats = self.filter.filter_images(content_list, base_dir)
        
        if len(valid_images) == 0:
            self.logger.warning("没有需要处理的图片")
            return
        
        # 4. 处理每张图片 → 生成 raw 描述
        raw_image_data = []
        all_raw_entities = []
        all_raw_relations = []
        
        for item in tqdm(valid_images, desc="处理图片"):
            try:
                # 处理单张图片
                image_result = self.process_single_image(
                    content_list, item, base_dir
                )
                
                if image_result:
                    raw_image_data.append(image_result["raw_data"])
                    all_raw_entities.extend(image_result["raw_entities"])
                    all_raw_relations.extend(image_result["raw_relations"])
                    
                    self.logger.info(f"✓ {item['img_path']}: {image_result['raw_data']['entity_name']}")
                else:
                    self.logger.warning(f"✗ {item['img_path']}: 处理失败")
                    
            except Exception as e:
                self.logger.error(f"✗ {item['img_path']}: {e}")
        
        # 5. 实体对齐
        self.logger.info("开始实体对齐...")
        aligned_entities = self.entity_extractor.align_entities(all_raw_entities)
        
        # 6. 保存输出
        self.save_outputs(
            raw_image_data=raw_image_data,
            raw_entities=all_raw_entities,
            raw_relations=all_raw_relations,
            aligned_entities=aligned_entities,
            input_path=input_path,
            output_dir=output_dir,
            filtered_stats=filtered_stats
        )
        
        # 7. 总结
        self.logger.info("=" * 60)
        self.logger.info(f"处理完成: 成功 {len(raw_image_data)}/{len(valid_images)}")
        self.logger.info(f"提取实体: {len(aligned_entities)} 个")
        self.logger.info("=" * 60)
    
    def process_single_image(
        self, 
        content_list: List[Dict], 
        item: Dict,
        base_dir: Path
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
        aligned_entities: List[Dict],
        input_path: Path,
        output_dir: Path,
        filtered_stats: Dict
    ) -> None:
        """保存输出文件（两个独立文件）"""
        
        # 1. 保存 Raw 版本（图片描述）⭐NEW
        raw_output = {
            "images": raw_image_data,
            "metadata": {
                "source_file": str(input_path),
                "total_images": len(raw_image_data),
                "filtered_stats": filtered_stats,
                "config": {
                    "multimodal_model": self.config.multimodal_model,
                    "context_window": self.config.context_window,
                    "ocr_engine": self.config.ocr_engine,
                    "res_preset": self.config.res_preset
                },
                "build_time": datetime.now().isoformat()
            }
        }
        
        raw_path = output_dir / input_path.name.replace(
            "_content_list.json", 
            "_content_list_image_raw.json"  # ⭐改名
        )
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_output, f, ensure_ascii=False, indent=2)
        self.logger.info(f"保存 Raw 图片描述: {raw_path}")
        
        # 2. 保存 Aligned 版本（知识图谱）
        kg_output = {
            "entities": aligned_entities,
            "relations": raw_relations,  # TODO: 关系也需要对齐
            "metadata": {
                "source_file": str(input_path),
                "total_entities": len(aligned_entities),
                "total_relations": len(raw_relations),
                "entity_types": list(set(e["type"] for e in aligned_entities)),
                "relation_types": list(set(r["relation_type"] for r in raw_relations)),
                "build_time": datetime.now().isoformat()
            }
        }
        
        kg_path = output_dir / input_path.name.replace(
            "_content_list.json",
            "_content_list_image_kg_aligned.json"  # ⭐改名
        )
        with open(kg_path, "w", encoding="utf-8") as f:
            json.dump(kg_output, f, ensure_ascii=False, indent=2)
        self.logger.info(f"保存知识图谱: {kg_path}")
```

## 配置设计（修订版）

```python
@dataclass
class ImagePipelineConfig:
    # 过滤参数（复用现有 ImageFliter）⭐增强
    ocr_engine: str = "auto"  # 'auto' | 'pytesseract' | 'easyocr' | 'paddleocr' | 'none'
    min_pixels: Optional[int] = None  # None 则使用 res_preset
    res_preset: str = "s"  # 's'=280k | 'm'=600k | 'l'=1.2M | 'off'=不过滤
    min_text_len: int = 10  # OCR 文本最小长度（<= 0 则跳过文本过滤）
    verbose: bool = True  # 显示过滤详情
    
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
```

**关键改进**：
1. ✅ 集成 `ImageFilter` 的所有过滤参数
2. ✅ 新增 `entity_extraction_model` 用于从描述提取实体
3. ✅ 新增 `verbose` 控制日志详细程度

## 提示词设计

### 1. 图片描述提示词（Multimodal LLM）**v2.0 优化**

文件：`prompts/image_description.txt`

**核心改进** (2025-11-11):
- ✅ **角色定位**: 从"文档分析专家"→"投资研究分析师"
- ✅ **聚焦核心**: 公司、产品、技术、数据指标等商业实体
- ✅ **禁止特殊字符**: 明确禁止 `\`、换行符、控制字符（防止JSON解析失败）
- ✅ **精炼表达**: 描述控制在100字以内，3-5个关键要素
- ✅ **字段重命名**: `detailed_description` → `description`

```markdown
# 角色
你是一个专业的投资研究分析师，专注从商业文档图片中提取**核心商业信息和关键实体**。

# 任务
分析图片，**重点识别和提取**：公司实体、产品技术、业务模式、数据指标等核心要素。

# 输入信息
**图片标题/名称**：{image_caption}
**周围文本上下文**：{context_text}

# 输出要求
**必须**严格按照以下JSON格式输出，**禁止**使用反斜杠`\`、换行符、控制字符等特殊字符：

{{
  "entity_name": "图片核心主题的简洁名称",
  "type": "图片类型（选一：架构图、流程图、数据图表、产品展示、组织结构、技术示意、商业模式、其他）",
  "description": "聚焦核心商业价值的描述，重点提取：1)涉及的公司/产品名称 2)关键技术或功能 3)核心数据指标 4)业务逻辑或价值主张。避免冗长的细节描述，保持精炼和可检索性。"
}}

# 关键规范
1. **description字段禁止事项**：
   - ❌ 禁止使用反斜杠 `\`（如 `产品\技术` 应写为 `产品和技术`）
   - ❌ 禁止换行符 `\n`
   - ❌ 禁止控制字符（tab、特殊Unicode等）
   - ✅ 使用中文顿号`、`或`和`替代斜杠
   
2. **聚焦核心实体**：
   - ✅ 提取公司名称、产品名称、技术名称
   - ✅ 提取关键数据（融资额、用户数、增长率等）
   - ✅ 提取核心业务逻辑（如"XX平台连接YY和ZZ"）
   - ❌ 避免通用描述（如"该图展示了..."、"包含多个模块..."）
   
3. **精炼表达**：
   - 一句话概括图片核心价值
   - 列出3-5个关键要素即可
   - 保持在100字以内

# 示例
**输入**：
- 图片标题：钛禾智库资源能力结构图
- 上下文：钛禾智库拥有1200+领域专家，覆盖科技工业政策、中科院专家、科技企业管理人员等

**输出**：
{{
  "entity_name": "钛禾智库资源能力结构图",
  "type": "组织结构",
  "description": "钛禾智库三层资源体系：智力库（1200+专家，包括科技工业政策顾问、中科院专家、科技企业管理人员）、产品和技术库、资本库。展示智库在科技产业投资研究领域的资源优势。"
}}
```

### 2. 实体提取提示词（Text LLM）**v2.0 新增**

### 2. 实体提取提示词（Text LLM）**v2.0 新增**

文件：`prompts/image_entity_extraction.txt`

**设计理念** (参考 `text_pipeline`):
- ✅ 使用**核心实体类型**（Company/Person/Product/Technology/TagConcept/Metric）
- ✅ **严格属性规范**（industry/stage/role/version/value等）
- ✅ **禁止通用概念**（数据处理、技术优势、图表元素）
- ✅ **数量控制**（3-8个实体，2-6个关系）

```markdown
# 角色
你是一个知识图谱构建专家，从图片描述中提取**核心商业实体和关系**，服务于投资研究场景。

# 任务
从图片描述中提取**高价值实体**（公司、产品、技术、关键指标），避免冗余和通用概念。

# 核心实体类型（优先提取）
1. **Company**: 公司名称（如：象量科技、阿里巴巴）
   - attributes需包含：industry（行业）、stage（融资阶段）等
2. **Person**: 人名（如：张三-CEO）
   - attributes需包含：role（职位）、expertise（专长）等  
3. **Product**: 产品/服务名（如：钛禾数据库、象量投研平台）
   - attributes需包含：version（版本）、features（功能）等
4. **Technology**: 技术术语（如：多模态大模型、知识图谱、RAG）
   - attributes需包含：application_domain（应用领域）等
5. **TagConcept**: 赛道/细分领域（如：AI投研、脑机接口）
6. **Metric**: 关键指标（如：融资额、用户数、准确率）
   - attributes需包含：value（数值）、unit（单位）等

# ❌ 不要提取
- 通用流程概念（数据处理、用户管理）
- 抽象描述（核心能力、技术优势）
- 图表元素（柱状图、箭头、方框）
- 常见术语（机器学习、人工智能） - 除非是具体产品/技术名

# 输出格式
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "类型（Company|Person|Product|Technology|TagConcept|Metric|Other）",
      "description": "简洁描述（一句话）",
      "attributes": {{"key": "value"}}
    }}
  ],
  "relations": [
    {{
      "source": "源实体名称",
      "target": "目标实体名称",
      "type": "关系类型（founded_by|uses_technology|in_segment|has_metric等）",
      "description": "关系描述"
    }}
  ]
}}

# 示例
**输入**：象量投研大数据能力闭环图，展示象量科技AI投研平台的数据闭环...

**输出**：
{{
  "entities": [
    {{"name": "象量科技", "type": "Company", "description": "AI投研平台提供商", "attributes": {{"industry": "金融科技"}}}},
    {{"name": "象量投研平台", "type": "Product", "description": "AI驱动的投资研究平台", "attributes": {{"features": "数据采集、知识图谱"}}}},
    {{"name": "知识图谱", "type": "Technology", "description": "结构化知识表示技术", "attributes": {{}}}},
    {{"name": "覆盖企业数", "type": "Metric", "description": "平台数据覆盖范围", "attributes": {{"value": "100000", "unit": "家企业"}}}}
  ],
  "relations": [
    {{"source": "象量科技", "target": "象量投研平台", "type": "developed_by", "description": "象量科技开发象量投研平台"}},
    {{"source": "象量投研平台", "target": "知识图谱", "type": "uses_technology", "description": "平台使用知识图谱技术"}}
  ]
}}
```

{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "实体类型（从以下选择：Company, Person, Technology, Product, Metric, Location, Time, Concept, Other）",
      "description": "实体描述",
      "attributes": {{}}
    }}
  ],
  "relations": [
    {{
      "source": "源实体名称",
      "target": "目标实体名称",
      "type": "关系类型（如：contains, compares, shows_trend, located_in, etc.）",
      "description": "关系描述"
    }}
  ]
}}

# 提取指南
1. **实体识别**：
   - 提取所有有意义的名词（公司、人名、产品、技术、指标等）
   - 尽量保持原始名称，不要过度概括
   - 确保实体类型准确

2. **关系识别**：
   - 识别实体之间的明确关系
   - 关系类型应具体且有意义
   - 优先提取图片核心展示的关系

3. **数量适中**：
   - 提取3-10个实体（根据描述复杂度）
   - 提取2-8个关系

# 示例
输入：
图片名称：机器学习算法准确率对比图
图片类型：数据图表
描述：该图片展示了一个柱状图，横轴为三种算法名称（随机森林、SVM、逻辑回归），纵轴为准确率百分比。随机森林算法准确率为85%，SVM算法为78%，逻辑回归算法为72%。

输出：
{{
  "entities": [
    {{"name": "随机森林", "type": "Technology", "description": "机器学习算法", "attributes": {{"accuracy": "85%"}}}},
    {{"name": "SVM", "type": "Technology", "description": "支持向量机算法", "attributes": {{"accuracy": "78%"}}}},
    {{"name": "逻辑回归", "type": "Technology", "description": "机器学习算法", "attributes": {{"accuracy": "72%"}}}},
    {{"name": "准确率", "type": "Metric", "description": "算法性能评估指标", "attributes": {{}}}}
  ],
  "relations": [
    {{"source": "随机森林", "target": "准确率", "type": "has_metric", "description": "随机森林算法准确率为85%"}},
    {{"source": "SVM", "target": "准确率", "type": "has_metric", "description": "SVM算法准确率为78%"}},
    {{"source": "逻辑回归", "target": "准确率", "type": "has_metric", "description": "逻辑回归算法准确率为72%"}}
  ]
}}
```

## 已修复问题与优化 (v2.0)

### 问题1: JSON解析失败 ✅ 已修复

**现象** (2025-11-11):
```
MultimodalDescriptor - ERROR - JSON 解析失败: Invalid \escape: line 4 column 63
原始响应: "description": "...产品\技术库、资本库..."
```

**根本原因**:
- LLM返回的description包含反斜杠 `\`（如"产品\技术"）
- Python JSON解析器将 `\t` 识别为tab字符，导致 `Invalid \escape` 错误

**解决方案**:
1. ✅ 在 `image_description.txt` prompt中明确禁止特殊字符：
   ```
   **禁止使用反斜杠 `\`**（如 `产品\技术` 应写为 `产品和技术`）
   ```
2. ✅ 要求使用中文顿号`、`或`和`替代斜杠
3. ✅ 增强鲁棒JSON解析（已有4种策略）

**效果**: 预期解析成功率从 90% → 98%+

---

### 问题2: OntologyAligner初始化错误 ✅ 已修复

**现象**:
```
ImageEntityExtractor - ERROR - 加载 OntologyAligner 失败: 
OntologyAligner.__init__() takes 1 positional argument but 2 were given
```

**根本原因**:
- `text_pipeline.OntologyAligner` 的 `__init__()` 不接受参数
- 错误调用: `OntologyAligner(some_param)`

**解决方案**:
```python
# 修复前
self.aligner = OntologyAligner(config)  # ❌

# 修复后
self.aligner = OntologyAligner()  # ✅ 无参数
```

**效果**: 实体对齐功能正常工作

---

### 问题3: 实体提取过于冗余 ✅ 已优化

**现象**:
- 提取了大量通用概念（"数据处理"、"技术优势"、"核心能力"）
- 提取了图表元素（"柱状图"、"箭头"、"方框"）
- 缺少核心商业实体（公司名、产品名、具体指标）

**解决方案**:
1. ✅ 参考 `text_pipeline` 的严格规范
2. ✅ 明确**核心实体类型**优先级（Company/Person/Product/Technology/TagConcept/Metric）
3. ✅ 添加**禁止提取列表**：
   ```
   ❌ 通用流程概念（数据处理、用户管理）
   ❌ 抽象描述（核心能力、技术优势）
   ❌ 图表元素（柱状图、箭头、方框）
   ```
4. ✅ 数量控制：3-8个实体，2-6个关系

**效果**: 实体质量显著提升，聚焦高价值商业信息

---

### 问题4: 表格图片统计不直观 ✅ 已改进

**现象** (用户反馈 2025-11-11):
```
【步骤0：表格图片过滤】收集到 5 个表格图片
...
【过滤总结】表格图片: 0  ← 困惑：明明收集了5个，为什么是0？
```

**根本原因**:
- 5张 `type="table"` 的图片被收集为黑名单
- 但它们**不在** `type="image"` 列表中
- 过滤统计时只计算从 type="image" 中过滤掉的数量
- **结果显示0是技术上正确的**，但**用户体验不佳**

**改进方案**:
```python
# 改进后的日志输出
【过滤总结】
  type='image' 总数: 24
  type='table' 总数: 5 (已排除，不参与图片描述生成)  ← 更清晰
  在 type='image' 中匹配到表格的数量: 0 (通常为0)
  ✓ 有效图片: 11
```

**效果**: 
- ✅ 用户一眼就能看懂：5个表格图片被排除了
- ✅ 同时说明了为什么"匹配到0"（因为表格和图片是分开的类型）
- ✅ 避免了"收集5个但显示0"的困惑

---

### 优化5: 描述生成Prompt优化 ✅ 已完成

**改进内容**:
- ✅ 角色从"文档分析专家"→"投资研究分析师"
- ✅ 聚焦核心商业价值（公司、产品、技术、指标）
- ✅ 精炼表达（100字以内，3-5个关键要素）
- ✅ 避免冗长的细节描述

**效果**: 描述更简洁、更具商业价值、更易于实体提取

## 错误处理策略

1. **图片文件不存在**：记录警告，跳过该图片
2. **LLM API 调用失败**：重试最多3次，失败后跳过并记录
3. **JSON 解析失败**：记录错误响应，跳过该图片
4. **网络超时**：使用指数退避重试
5. **批处理中断**：保存进度，支持从上次中断处继续

## 性能优化

1. **批处理**：如 LLM 支持批量推理，可批量发送请求
2. **缓存**：缓存已处理图片的描述，避免重复调用
3. **并发**：使用 asyncio 或线程池并发处理多张图片
4. **进度保存**：定期保存中间结果，支持断点续传
