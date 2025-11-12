# 表格处理 Pipeline 设计文档

## 1. 架构设计

### 整体架构

```
TableKnowledgeGraphPipeline
├── TableCollector          # 表格收集与过滤
├── TableContentParser      # HTML 表格解析
├── TableDescriptor         # 表格描述生成
├── TableEntityExtractor    # 实体提取与对齐
└── OutputGenerator         # 输出文件生成
```

### 与现有 Pipeline 的关系

- ✅ **独立运行**：Table Pipeline 可单独运行
- ✅ **共享组件**：与 Text/Image Pipeline 共享 OntologyAligner
- ✅ **格式统一**：输出格式完全一致（entities 为 Dict 结构）
- ✅ **可组合**：三个 Pipeline 的输出可直接合并

## 2. 处理流程

```
输入：content_list.json
  ↓
阶段1：收集与过滤
  - 收集所有 type="table"
  - 过滤空表格
  ↓
阶段2：表格解析与描述生成
  - 解析 HTML 表格
  - 调用 LLM 生成描述
  ↓
阶段3：实体提取与对齐
  - 提取 Signal 类实体（重点）
  - 调用 OntologyAligner 对齐
  ↓
阶段4：输出生成
  - *_table_raw.json
  - *_table_kg_aligned.json
```

## 3. 核心组件

参考 `image_pipeline.py` 和 `text_pipeline.py` 的实现风格。

### TableCollector
- 收集 type="table" 条目
- 过滤空表格（min_length < 50）
- 统计日志

### TableDescriptor  
- 使用 qwen-plus-latest 生成描述
- 鲁棒 JSON 解析（复用 image_pipeline 机制）
- 返回 entity_name, type, description

### TableEntityExtractor
- 提取 Signal 类实体（数据指标）
- 共享 OntologyAligner
- 返回 Dict[str, entity]

## 4. 提示词设计

参考文件：
- `prompts/table_description.txt` - 表格描述生成
- `prompts/table_entity_extraction.txt` - 实体提取

重点关注：
- Signal 类实体（数据指标）
- 必填属性：metric_type, unit, values, trend
- 禁止提取表格结构元素

## 5. 输出格式

### *_table_raw.json
```json
{
  "metadata": {...},
  "tables": [{...}],
  "entities": {...},  // Dict格式
  "relations": [...]
}
```

### *_table_kg_aligned.json
```json
{
  "metadata": {...},
  "aligned_entities": {...},  // Dict格式
  "aligned_relations": [...]
}
```

## 6. 技术要点

1. **HTML 解析**：使用 beautifulsoup4
2. **JSON 解析容错**：复用 image_pipeline 机制
3. **实体对齐**：共享 OntologyAligner
4. **日志风格**：与 text/image pipeline 保持一致
5. **格式统一**：entities 为 Dict 结构

详细实现参考 `tasks.md`。
