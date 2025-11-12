# 添加表格处理 Pipeline

## 元信息
- **变更ID**: `add-table-pipeline`
- **类型**: Feature - 新功能
- **优先级**: P1 - 高优先级
- **状态**: Draft - 草案
- **创建日期**: 2025-11-12
- **负责人**: [待指定]
- **预计工作量**: 3-5天

## 变更概述 (Change Summary)

为知识图谱提取系统添加**表格处理 Pipeline**，实现从 MinerU 解析的表格数据中自动提取知识实体。表格内容已由 MinerU 完成 OCR 识别并转为 HTML 格式，本 Pipeline 专注于：
1. 理解表格语义和结构
2. 生成表格的详细描述
3. 提取表格中的知识实体和关系
4. 对齐到核心本体类型

与图片 Pipeline 类似，但**不需要多模态模型**，直接使用文本 LLM（qwen-plus-latest）处理已识别的表格内容。

## 为什么需要这个变更 (Why)

### 问题背景
当前系统已支持**文本 Pipeline** 和 **图片 Pipeline**，但表格数据处理存在以下问题：
1. **表格被图片Pipeline错误处理**：表格图片（type="table"）被当作普通图片，需要 VL 模型识别，成本高且效果差
2. **结构化信息丢失**：表格包含丰富的结构化数据（行列关系、数据对比），现有方式无法充分提取
3. **数据指标未被利用**：表格中的关键指标（如营收预测、用户数、ARPU 等）是重要的 Signal 类实体，当前无法提取

### 业务价值
- ✅ **知识完整性**：补充表格数据源，形成文本+图片+表格的三模态知识图谱
- ✅ **数据指标提取**：自动提取营收、用户数、增长率等关键 Signal 实体
- ✅ **成本优化**：表格内容已识别，无需调用昂贵的 VL 模型
- ✅ **格式统一**：与 text/image pipeline 输出格式一致，可直接合并

## 核心变更 (What)

### 输入格式
```json
{
    "type": "table",
    "img_path": "images/fab6de03f78e60b27dba19539fda1e57fa2812af02d07aaf65a6413537fd0939.jpg",
    "table_caption": ["核心指标预测"],
    "table_footnote": [],
    "table_body": "<table><tr><td>指标</td><td>第一年 (2026)</td>...</tr>...</table>",
    "bbox": [479, 281, 926, 885],
    "page_idx": 19
}
```

### 输出格式
**文件1**: `*_table_raw.json`
```json
{
  "metadata": {
    "source_file": "path/to/content_list.json",
    "total_tables": 8,
    "total_entities": 45,
    "total_relations": 32
  },
  "tables": [
    {
      "img_path": "images/...",
      "page_idx": 19,
      "entity_name": "核心指标预测表",
      "type": "表格",
      "description": "该表格展示了2026-2028年的核心业务指标预测...",
      "table_caption": "核心指标预测",
      "table_body": "<table>...</table>"
    }
  ],
  "entities": {
    "订阅付费客户": {
      "name": "订阅付费客户",
      "type": "Signal",
      "description": "订阅付费的客户数量指标",
      "attributes": {
        "2026": "2000+种子用户",
        "2027": "15,000+个人用户",
        "2028": "30,000+个人用户"
      },
      "source_table": "images/...",
      "page_idx": 19
    }
  },
  "relations": [...]
}
```

**文件2**: `*_table_kg_aligned.json` - 对齐后的知识图谱

## 功能特性 (Features)

### 核心能力
1. **表格内容理解**
   - 解析 HTML 格式的表格内容（table_body）
   - 结合 table_caption 和 table_footnote 理解表格语义
   - 识别表格类型（数据对比、指标预测、性能评估等）

2. **智能描述生成**
   - 使用文本 LLM（qwen-plus-latest）生成结构化描述
   - 提取表格核心信息（标题、数据范围、关键发现）
   - 生成 100 字以内的精炼描述

3. **实体关系提取**
   - 从表格数据中提取 Signal 类实体（指标、数据）
   - 提取 Company/Product/Technology 等实体
   - 识别实体间的时间序列关系、对比关系

4. **本体对齐**
   - 与 text/image pipeline 共享 OntologyAligner
   - 映射到核心本体类型（重点是 Signal 类型）
   - 保留 source_table 和 page_idx 溯源信息

### 技术特点
- ✅ **无需 VL 模型**：直接处理已识别的 HTML 表格，成本低
- ✅ **结构感知**：理解表格的行列结构和数据关系
- ✅ **格式统一**：entities 为 Dict 结构，与其他 Pipeline 一致
- ✅ **独立运行**：可单独运行或与其他 Pipeline 组合

## 处理流程 (How)

```
输入: content_list.json (MinerU 输出)
  ↓
【阶段一】表格收集与过滤
  ├─ 收集所有 type="table" 的条目
  ├─ 过滤空表格（table_body 为空或过短）
  └─ 统计表格数量和分布
  ↓
【阶段二】表格描述生成
  ├─ 解析 HTML 表格结构
  ├─ 提取 table_caption 和 table_footnote
  ├─ 调用 qwen-plus-latest 生成描述
  ├─ 鲁棒 JSON 解析（复用 image_pipeline 机制）
  └─ 生成 entity_name, type, description
  ↓
【阶段三】实体提取与对齐
  ├─ 使用 qwen-plus 提取实体（重点关注 Signal 类）
  ├─ 添加 source_table 和 page_idx 字段
  ├─ 调用 OntologyAligner 对齐
  └─ 映射到核心类型（Signal/Company/Product/Technology）
  ↓
输出（两个独立文件）:
  ├─ *_table_raw.json (表格描述 + 原始实体)
  └─ *_table_kg_aligned.json (对齐后的知识图谱)
```

## 技术方案 (Technical Design)

### 1. 核心组件

#### TableContentParser
```python
class TableContentParser:
    """解析表格内容"""
    def parse_html_table(self, html: str) -> Dict:
        """解析 HTML 表格，提取行列结构"""
        
    def extract_table_summary(self, table_data: Dict) -> str:
        """生成表格结构摘要"""
```

#### TableDescriptor
```python
class TableDescriptor:
    """表格描述生成器"""
    def generate_description(
        self, 
        table_body: str,
        table_caption: List[str],
        table_footnote: List[str]
    ) -> Tuple[str, Dict]:
        """生成表格的详细描述和实体信息"""
```

#### TableEntityExtractor
```python
class TableEntityExtractor:
    """表格实体提取器"""
    def extract_entities(self, description: str, table_data: Dict) -> Tuple[List, List]:
        """从表格描述中提取实体和关系（重点关注 Signal 类）"""
        
    def align_entities(self, entities: List) -> Dict:
        """对齐到核心本体类型"""
```

#### TableKnowledgeGraphPipeline
```python
class TableKnowledgeGraphPipeline:
    """表格知识图谱提取主流程"""
    def __init__(self, config: TablePipelineConfig):
        self.parser = TableContentParser()
        self.descriptor = TableDescriptor(...)
        self.extractor = TableEntityExtractor(...)
        
    def run(self, input_path: str):
        """执行完整的表格处理流程"""
```

### 2. 数据模型

```python
@dataclass
class TablePipelineConfig:
    """表格Pipeline配置"""
    model_name: str = "qwen-plus-latest"
    temperature: float = 0.1
    min_table_length: int = 50  # 最小表格长度（字符数）
    verbose: bool = False
    
@dataclass
class TableDescription:
    """表格描述"""
    entity_name: str
    type: str
    description: str
    
@dataclass
class TableEntity:
    """表格实体"""
    name: str
    type: str
    description: str
    attributes: Dict
    source_table: str
    page_idx: int
```

### 3. 提示词设计

**表格描述生成提示词** (`prompts/table_description.txt`):
```
你是一个表格分析专家，需要理解并描述表格内容。

【表格信息】
- 标题: {table_caption}
- 内容: {table_body}
- 脚注: {table_footnote}

【任务】
1. 理解表格的主题和目的
2. 识别表格类型（数据对比/指标预测/性能评估/时间序列等）
3. 提取关键信息和趋势

【输出要求】
返回 JSON 格式：
{{
  "entity_name": "表格的描述性名称",
  "type": "表格类型（如：数据对比表、指标预测表）",
  "description": "100字以内的精炼描述，包含表格主题、关键数据、趋势或对比结果"
}}

【注意】
- 禁止使用反斜杠 \ 等特殊字符
- 描述要精炼，突出核心信息
- 关注数据指标和趋势
```

**表格实体提取提示词** (`prompts/table_entity_extraction.txt`):
```
从表格描述中提取知识实体，重点关注数据指标（Signal类）。

【核心实体类型】
- Signal: 指标、数据、趋势（如：营收、用户数、增长率）
- Company: 公司名称
- Product: 产品名称
- Technology: 技术名称
- TagConcept: 领域概念

【表格内容】
{description}

【输出格式】
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "Signal|Company|Product|Technology|TagConcept",
      "description": "实体描述",
      "attributes": {{"key": "value"}}  // Signal类型必填：数据值、单位、时间范围
    }}
  ],
  "relations": [...]
}}

【注意】
- 重点提取 Signal 类实体（数据指标）
- 数量控制：3-10个实体
- 禁止提取表格结构元素（如"第一列"、"表头"）
```

## 依赖关系 (Dependencies)

### 前置条件
- ✅ MinerU 已完成文档解析并生成 `*_content_list.json`
- ✅ 表格内容已被 OCR 识别并转为 HTML 格式
- ✅ OntologyAligner 已实现（复用自 text/image pipeline）

### 依赖的外部服务
- **通义千问 API**: qwen-plus-latest 模型（文本理解）
- **Python 库**: 
  - `beautifulsoup4` 或 `lxml`: HTML 表格解析
  - `html2text`: HTML 转文本（可选）

### 与其他 Pipeline 的关系
- **独立运行**: 可单独处理表格数据
- **格式统一**: 输出格式与 text/image pipeline 完全一致
- **共享组件**: 使用相同的 OntologyAligner
- **可组合**: 三个 Pipeline 的输出可直接合并

## 配置参数 (Configuration)

### 环境变量
```bash
# LLM 配置
DASHSCOPE_API_KEY=your_api_key
MODEL_NAME=qwen-plus-latest

# 表格处理配置
TABLE_MIN_LENGTH=50              # 最小表格长度（字符数）
TABLE_DESCRIPTION_MAX_LENGTH=100 # 描述最大长度
```

### 命令行参数
```bash
python pipelines/table_pipeline.py input.json \
  --output-dir output/ \
  --model qwen-plus-latest \
  --min-length 50 \
  --verbose
```

## 验收标准 (Acceptance Criteria)

### 1. 功能完整性
- [ ] 能正确收集所有 type="table" 的条目
- [ ] 能解析 HTML 表格并提取结构信息
- [ ] 能生成准确的表格描述（entity_name, type, description）
- [ ] 能从表格中提取 Signal 类实体（数据指标）
- [ ] 能对齐到核心本体类型
- [ ] 输出两个 JSON 文件（raw + aligned）

### 2. 代码质量
- [ ] 代码风格与 text/image pipeline 一致
- [ ] 有完整的类型注解和文档字符串
- [ ] 异常处理完善（容错机制）
- [ ] 日志记录清晰（简洁风格）

### 3. 测试验证
- [ ] 能处理示例文件（包含表格的 content_list.json）
- [ ] 输出的描述结构正确
- [ ] 提取的实体包含 source_table 和 page_idx 字段
- [ ] 对齐后的知识图谱格式正确（Dict 格式）

### 4. 文档完善
- [ ] README_PIPELINE.md 更新表格处理说明
- [ ] 代码中有使用示例
- [ ] 配置参数有说明文档

## 影响范围 (Impact)

### 新增文件
```
pipelines/
├── table_pipeline.py      # 表格处理主流程
├── table_models.py        # 表格数据模型
└── prompts/
    ├── table_description.txt         # 表格描述生成
    └── table_entity_extraction.txt   # 表格实体提取
```

### 修改文件
- `README.md`: 添加表格 Pipeline 介绍
- `README_PIPELINE.md`: 添加表格处理使用文档
- `openspec/project.md`: 更新项目架构（三 Pipeline）

### 不影响
- ✅ 不影响现有的 text_pipeline
- ✅ 不影响现有的 image_pipeline
- ✅ 不改变现有的输出格式

## 风险与限制 (Risks & Limitations)

### 技术风险
1. **HTML 解析复杂性**
   - 风险: MinerU 生成的 HTML 可能格式不规范
   - 缓解: 使用鲁棒的解析库（beautifulsoup4），增加容错
   
2. **表格理解准确性**
   - 风险: 复杂表格（嵌套、合并单元格）可能难以理解
   - 缓解: 提示词中明确要求关注核心数据，忽略复杂结构

3. **实体提取质量**
   - 风险: Signal 类实体可能过于宽泛或缺失
   - 缓解: 优化提示词，明确 Signal 类的定义和示例

### 业务限制
1. **依赖 MinerU 质量**: 表格内容质量取决于 MinerU 的 OCR 准确性
2. **成本控制**: 每个表格需调用 LLM，大量表格会增加成本
3. **结构限制**: 目前仅支持二维表格，不支持多级表头

## 后续优化 (Future Work)

### v1.1 (短期)
- [ ] 支持表格数据的结构化输出（JSON/CSV）
- [ ] 表格类型自动分类（指标预测/性能对比/时间序列）
- [ ] 表格合并（跨页表格的合并）

### v1.2 (中期)
- [ ] 表格数据可视化（生成图表）
- [ ] 表格与文本的关系链接（引用关系）
- [ ] 多语言表格支持

### v2.0 (长期)
- [ ] 表格问答功能（基于表格内容的问答）
- [ ] 表格数据的时间序列分析
- [ ] 与数据库集成（表格数据直接入库）

## 参考资料 (References)

- **RAGAnything 源码**: `raganything/modalprocessors.py` - TableModalProcessor
- **Image Pipeline 提案**: `openspec/changes/add-image-pipeline/proposal.md`
- **项目架构文档**: `openspec/project.md`
- **Prompt 设计参考**: `pipelines/prompts/image_description.txt`

---

**提案状态**: Draft  
**下一步**: 评审提案 → 创建 tasks.md → 开始实施
