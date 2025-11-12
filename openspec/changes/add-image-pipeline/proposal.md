# 添加图片处理 Pipeline

## 为什么 (Why)

当前系统只能处理文本内容（通过 `text_pipeline.py`），但 MinerU 解析的文档中包含大量有价值的图片信息（流程图、数据图表、技术示意图等），这些视觉信息无法被现有的文本 pipeline 处理。

**核心问题**：
- MinerU 输出的 `content_list.json` 中包含 `type: "image"` 的条目，但只有路径和 bbox，没有语义信息
- 图片中蕴含的实体、关系无法提取到知识图谱中
- 表格图片与表格文本重复，浪费 token
- 低质量/装饰性图片混杂，增加处理成本

**解决方案**：
在现有 `image_pipline.py`（已实现部分过滤）基础上，完善为完整的三阶段处理流程：
1. **预处理与过滤**：移除表格图片、低质量图片（已有基础实现）
2. **上下文感知描述生成**：使用 Qwen3-VL-Flash 生成结构化图片描述
3. **知识实体提取**：从描述中提取实体和关系，融合到知识图谱

## 是什么 (What)

### 核心变更

**新增文件**：
- `pipelines/image_pipeline.py` - 图片处理主流程（重构现有 image_pipline.py）
- `pipelines/text_pipeline.py` - 文本处理流程（移动自根目录）
- `pipelines/image_models.py` - 图片相关的 Pydantic 数据模型
- `pipelines/prompts/image_description.txt` - 多模态 LLM 提示词模板
- `pipelines/__init__.py` - 包初始化文件

**修改文件**：
- 移动 `text_pipline.py` → `pipelines/text_pipeline.py`
- README_PIPELINE.md - 补充图片处理流程文档和新目录结构

### 功能特性

1. **智能过滤**
   - 识别并跳过已有文本表示的表格图片
   - 基于规则过滤低质量图片（像素、宽高比、OCR 文字数量）

2. **上下文感知描述**
   - 从 Markdown 结构提取图片周围的标题和上下文
   - 组合图片 + caption + context 送入多模态 LLM
   - 生成结构化描述（entity_name, type, detailed_description）

3. **知识提取与融合**
   - 从详细描述中提取细粒度实体和关系
   - 与文本 pipeline 提取的实体对齐融合
   - 输出两个文件：
     - `*_content_list.json` - 原文件补充描述
     - `*_content_list_kg_aligned.json` - 对齐后的知识图谱

### 处理流程

```
输入: *_content_list.json (MinerU 输出)
  ↓
阶段一: 预处理与过滤
  - 识别 type="table" 的 img_path，标记为跳过
  - 对剩余 type="image" 的条目应用规则过滤
  ↓
阶段二: 上下文感知描述生成
  - 提取图片周围的文本上下文（标题、前后段落）
  - 调用多模态 LLM 生成结构化描述
  - 将描述补充到原 JSON 的 image 条目中
  ↓
阶段三: 知识实体提取
  - 使用类似 text_pipeline 的方法从描述中提取实体
  - 记录实体来源（source_image: img_path）
  - 与文本实体对齐融合
  ↓
输出: 
  - *_content_list.json (补充描述)
  - *_content_list_kg_aligned.json (对齐后知识图谱)
```

## 如何做 (How)

### 技术方案

**架构设计**：
- 仿照 `text_pipeline.py` 的风格，使用类封装
- 主类：`ImageKnowledgeGraphPipeline`
- 配置类：`ImagePipelineConfig`

**关键组件**：

1. **ImageFilter** - 图片过滤器
   - `filter_table_images()` - 基于 content_list 中的 table 条目过滤
   - `filter_low_quality()` - 基于规则过滤（最小像素、宽高比范围等）

2. **ContextExtractor** - 上下文提取器
   - `extract_nearby_text()` - 从 content_list 提取图片前后的文本
   - `extract_caption()` - 获取 image_caption 和 image_footnote

3. **MultimodalDescriptor** - 多模态描述生成器
   - `generate_description()` - 调用 LLM 生成图片描述
   - 使用 Qwen-VL 或 GPT-4V 等多模态模型

4. **ImageEntityExtractor** - 图片实体提取器
   - `extract_entities_from_description()` - 从描述提取实体
   - `align_with_text_entities()` - 与文本实体融合

**数据模型** (image_models.py)：

```python
class ImageDescription(BaseModel):
    entity_name: str
    type: str  # 流程图/数据图表/技术示意图等
    detailed_description: str

class ImageEntity(BaseModel):
    entity_name: str
    entity_type: str
    attributes: Dict[str, Any]
    source_image: str  # 来源图片路径
    description: str

class ImageKGOutput(BaseModel):
    entities: List[ImageEntity]
    relations: List[Dict[str, Any]]
```

**提示词设计**：
参考用户提供的模板，适配为实际任务（聚焦详细描述生成）

### 依赖关系

- 复用 `text_pipeline.py` 中的实体提取逻辑
- 使用相同的 LLM 客户端（DashScope）
- 依赖 `content_list.json` 格式（MinerU 输出）

### 配置参数

```python
class ImagePipelineConfig:
    min_pixel_count: int = 10000  # 最小像素数
    min_aspect_ratio: float = 0.3  # 最小宽高比
    max_aspect_ratio: float = 3.0  # 最大宽高比
    min_ocr_text_length: int = 5   # 最小 OCR 文字数
    context_window: int = 2        # 上下文窗口（前后 N 个元素）
    multimodal_model: str = "qwen-vl-max"  # 多模态模型
```

## 验收标准 (Acceptance Criteria)

1. **功能完整性** ✅ 已完成 (2025-11-11)
   - [x] 能正确过滤表格图片（5张表格图片正确识别并排除）
   - [x] 能基于规则过滤低质量图片（分辨率+OCR文本长度）
   - [x] 能提取图片周围的上下文（标题+前后文本）
   - [x] 能调用多模态 LLM 生成描述（11/11 成功，100%）
   - [x] 能将描述补充回原 JSON（两个独立文件输出）
   - [x] 能从描述中提取实体和关系（80个实体，67个关系）
   - [x] 输出两个 JSON 文件（raw + aligned，格式统一）

2. **代码质量** ✅ 已完成 (2025-11-11)
   - [x] 代码风格与 `text_pipeline.py` 一致（简洁日志风格）
   - [x] 有类型注解和文档字符串
   - [x] 异常处理完善（多层容错机制）
   - [x] 日志记录清晰（简洁汇总+verbose详情）

3. **测试验证** ✅ 已完成 (2025-11-11)
   - [x] 能处理示例文件 `象量科技项目介绍20250825_content_list.json`
   - [x] 输出的描述结构正确（entity_name, type, description）
   - [x] 提取的实体包含 source_image 和 page_idx 字段
   - [x] 对齐后的知识图谱格式正确（Dict格式，可直接合并）

4. **文档完善** ⏳ 待完成
   - [ ] README_PIPELINE.md 包含图片处理说明
   - [ ] 代码中有使用示例
   - [ ] 配置参数有说明文档

## 实施总结 (2025-11-11)

### 核心成果
- ✅ **100%处理成功率**: 11/11图片全部成功处理
- ✅ **鲁棒JSON解析**: 自动检测并修复反斜杠等非法字符
- ✅ **实体对齐成功**: 80个实体映射到5种核心类型（Company/Technology/Signal/Product/TagConcept）
- ✅ **格式完全统一**: 输出与text_pipeline一致，支持直接合并

### 关键优化
1. **移除外部依赖**: 将`image_filter.py`整合到`image_pipeline.py`，自包含OCR初始化
2. **增强容错机制**: 
   - 提示词明确禁止特殊字符
   - 正则自动修复非法转义：`\(?!["\\/bfnrtu])` → `/`
3. **修复对齐功能**: OntologyAligner改为无参构造，实体成功映射
4. **统一输出格式**: entities从List改为Dict[name, entity]，与text_pipeline一致
5. **优化日志风格**: 参考text_pipeline，保持简洁清晰

### 测试数据
- **输入**: 24张type=image + 5张type=table
- **过滤**: 9张分辨率 + 4张文本长度
- **输出**: 11张有效图片
- **实体分布**: Company(21) + Technology(20) + Signal(21) + Product(9) + TagConcept(9) = 80
- **关系数量**: 67个

## 影响范围 (Impact)

**新增功能**：
- 图片内容的语义理解能力
- 视觉信息到知识图谱的转化能力

**不影响**：
- 现有 `text_pipeline.py` 功能
- API 接口（`api.py`）保持不变
- 已有的文本处理流程

**可选扩展**：
- 未来可支持图片实体与文本实体的交叉验证
- 支持图片相似度去重
- 支持图片质量评分

## 风险与限制 (Risks)

1. **多模态 LLM 成本**：图片处理比文本更贵，需考虑 token 消耗
2. **描述质量依赖模型**：Qwen-VL 的理解能力影响实体提取准确性
3. **上下文提取准确性**：Markdown 结构不完整时可能提取不到有效上下文
4. **处理速度**：多模态推理较慢，大批量图片耗时较长

**缓解措施**：
- 严格过滤低质量图片，减少不必要的 LLM 调用
- 支持批处理和进度保存
- 提供详细的日志用于调试和优化
