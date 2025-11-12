# 实现任务清单

## 1. 数据模型设计

- [x] 1.1 创建 `table_models.py` ✅ 2025-11-12
  - [x] 1.1.1 定义 `TableDescription` 模型（entity_name, type, description）
  - [x] 1.1.2 定义 `TableEntity` 模型（含 source_table 和 page_idx 字段）
  - [x] 1.1.3 定义 `TableKGOutput` 模型
  - [x] 1.1.4 定义 `TablePipelineConfig` 配置类
  - [x] 1.1.5 添加类型注解和文档字符串
  - [x] 1.1.6 定义 `TableRawData`, `TableRawOutput` (两文件输出架构)

## 2. 表格解析模块

- [x] 2.1 实现 `TableContentParser` 类 ✅ 2025-11-12
  - [x] 2.1.1 实现 `parse_html_table()` 方法
    - 使用 beautifulsoup4 解析 HTML
    - 提取行列结构
    - 处理 rowspan 和 colspan
    - 容错处理（不规范的 HTML）
  - [x] 2.1.2 实现 `extract_table_summary()` 方法
    - 生成表格结构摘要（行数、列数、数据类型）
    - 识别表头和数据行
    - 提取关键单元格内容
  - [x] 2.1.3 实现 `clean_table_content()` 方法
    - 清理 HTML 标签和多余空格
    - 标准化表格文本
    - 处理特殊字符

## 3. 表格收集与过滤模块

- [x] 3.1 实现 `TableCollector` 类 ✅ 2025-11-12
  - [x] 3.1.1 实现 `collect_tables()` 方法
    - 从 content_list 中收集所有 type="table" 的条目
    - 统计表格数量和分布
    - 记录每个表格的页码信息
  - [x] 3.1.2 实现 `filter_tables()` 方法
    - 过滤空表格（table_body 为空或过短）
    - 过滤无意义表格（只有表头）
    - 配置最小表格长度阈值（默认50字符）
  - [x] 3.1.3 添加日志输出
    - 简洁的汇总日志（与 text/image pipeline 风格一致）
    - verbose 模式显示详细表格列表

## 4. 表格描述生成模块

- [x] 4.1 创建 `prompts/table_description.txt` 提示词模板 ✅ 2025-11-12
  - [x] 4.1.1 编写表格分析提示词
    - **重点**: 理解表格主题、类型、关键数据
    - **禁止**: 反斜杠`\`、特殊字符
    - **精炼**: 100字以内描述
  - [x] 4.1.2 添加 JSON 输出格式要求
  - [x] 4.1.3 添加示例（核心指标预测表）
  
- [x] 4.2 实现 `TableDescriptor` 类 ✅ 2025-11-12
  - [x] 4.2.1 初始化文本 LLM 客户端（qwen-plus-latest）
  - [x] 4.2.2 实现 `generate_description()` 方法
    - 组合 table_caption + table_body + table_footnote
    - 渲染提示词模板
    - 调用 LLM API
    - 鲁棒 JSON 解析（复用 image_pipeline 的机制）
  - [x] 4.2.3 添加重试机制和错误处理
  - [x] 4.2.4 实现 JSON 解析容错
    - 自动检测并修复非法转义序列
    - 正则替换：`\(?!["\\/bfnrtu])` → `/`
    - 多策略解析（去除代码块标记、去除前后文本）

## 5. 表格实体提取模块

- [x] 5.1 创建 `prompts/table_entity_extraction.txt` 提示词模板 ✅ 2025-11-12
  - [x] 5.1.1 参考 `text_pipeline` 和 `image_pipeline` 的规范
    - **核心实体类型**: Signal（重点）, Company, Product, Technology, TagConcept
    - **严格属性**: Signal 类必须包含数据值、单位、时间范围等
    - **禁止提取**: 表格结构元素（如"第一列"、"表头"、"行数"）
  - [x] 5.1.2 添加数量控制（3-10个实体，2-8个关系）
  - [x] 5.1.3 更新示例（核心指标预测表的实体提取）

- [x] 5.2 实现 `TableEntityExtractor` 类 ✅ 2025-11-12 (含关键bug修复)
  - [x] 5.2.1 实现 `extract_entities_from_description()` 方法
    - 使用 qwen-plus 提取实体和关系
    - 重点关注 Signal 类实体（数据指标）
    - 鲁棒 JSON 解析
    - 为每个实体添加 source_table 和 page_idx
  - [x] 5.2.2 实现 `align_entities()` 方法 (**关键bug修复** 2025-11-12)
    - 加载 `text_pipeline.OntologyAligner`
    - 转换为 Entity 对象格式
    - 调用对齐逻辑，映射到核心类型
    - 保留 source_table 和 page_idx 元信息
    - **返回格式**: Dict[str, Dict] (与 text/image pipeline 一致)
    - **Bug修复**: 改为使用 `entities_dict = {}` 而非 `entities_obj = []`
      - 问题：OntologyAligner.align_entities() 期望 `Dict[str, Entity]`，但传入了 `List[Entity]`
      - 修复：使用 `entities_dict[entity.name] = entity` 构建字典
      - 修复：迭代改为 `for name, aligned_entity in aligned_entities.items()`
      - 修复：实体查找改为基于name的查找而非索引
  - [x] 5.2.3 实体对齐验证
    - 确保 Signal 类实体正确对齐
    - 测试 Company/Product/Technology 的对齐
  - [x] 5.2.4 添加实体统计日志

## 6. 主 Pipeline 实现

- [x] 6.1 创建 `table_pipeline.py` ✅ 2025-11-12
  - [x] 6.1.1 定义 `TableKnowledgeGraphPipeline` 类
  - [x] 6.1.2 实现 `__init__()` 方法（初始化配置和组件）
  - [x] 6.1.3 实现 `load_content_list()` 方法
  - [x] 6.1.4 实现 `collect_and_filter_tables()` 方法
    - 收集所有 type="table" 的条目
    - 过滤空表格和无效表格
    - 返回有效表格列表和统计信息
  - [x] 6.1.5 实现 `process_single_table()` 方法
    - 解析表格内容
    - 生成描述
    - 提取实体和关系
    - 返回 {raw_data, raw_entities, raw_relations}
  - [x] 6.1.6 实现 `run()` 主方法
    - 收集所有 raw_data / raw_entities / raw_relations
    - 调用实体对齐
    - 生成两个文件输出
    - 添加进度条（tqdm）
  - [x] 6.1.7 实现 `save_outputs()` 方法
    - **文件1**: `*_table_raw.json`
      - metadata: total_tables, total_entities, entity_types
      - tables: 表格描述列表
      - entities: Dict[name, entity] (字典格式)
      - relations: 关系列表
    - **文件2**: `*_table_kg_aligned.json`
      - metadata: ontology_version, data_source="table_pipeline"
      - aligned_entities: Dict[name, aligned_entity] (字典格式)
      - aligned_relations: 对齐后的关系
    - **格式统一**: 与 text/image pipeline 输出完全一致
  - [x] 6.1.8 添加命令行参数支持
  - [x] 6.1.9 优化日志输出 ✅ 2025-11-12
    - 简洁汇总风格（与 text/image pipeline 一致）
    - verbose/non-verbose双模式（tqdm进度条 vs 详细日志）
    - 进度跟踪：`[1/5] 处理表格: images/xxx.jpg (页码: 5)`
    - 实体类型分布统计
    - 耗时统计和文件路径汇总
    - 统一分隔符（`=` * 60）

## 7. 集成与优化

- [x] 7.1 日志系统 ✅ 2025-11-12
  - [x] 7.1.1 配置 logging（统一日志格式）
  - [x] 7.1.2 在关键步骤添加日志（收集、过滤、描述生成、实体提取）
  - [x] 7.1.3 添加进度条（tqdm，支持 verbose 控制）

- [x] 7.2 错误处理 ✅ 2025-11-12
  - [x] 7.2.1 处理表格解析失败（跳过并记录）
  - [x] 7.2.2 处理 LLM API 调用失败（异常捕获）
  - [x] 7.2.3 处理 JSON 解析错误（多策略容错+自动修复）
  - [x] 7.2.4 添加降级策略（失败时跳过，记录日志）

- [x] 7.3 配置管理 ✅ 2025-11-12
  - [x] 7.3.1 支持从环境变量读取配置（通过 dotenv）
  - [x] 7.3.2 使用 dataclass 配置（TablePipelineConfig）
  - [x] 7.3.3 提供默认配置（min_length=50 等）

## 8. 测试与验证

- [ ] 8.1 单元测试
  - [ ] 8.1.1 测试 HTML 表格解析（各种格式）
  - [ ] 8.1.2 测试表格过滤逻辑
  - [ ] 8.1.3 测试 JSON 解析容错

- [ ] 8.2 集成测试
  - [ ] 8.2.1 使用示例文件测试（包含表格的 content_list.json）
  - [ ] 8.2.2 验证表格描述生成质量
  - [ ] 8.2.3 验证 Signal 类实体提取
  - [ ] 8.2.4 验证两文件输出格式
  - [ ] 8.2.5 验证实体对齐功能
  - [ ] 8.2.6 测试与其他 Pipeline 输出的合并兼容性

- [ ] 8.3 性能测试
  - [ ] 8.3.1 测量单个表格处理耗时
  - [ ] 8.3.2 统计 token 消耗
  - [ ] 8.3.3 测试批量表格处理性能

## 9. 文档与示例

- [ ] 9.1 更新 README.md
  - [ ] 9.1.1 添加表格 Pipeline 介绍
  - [ ] 9.1.2 更新系统架构图（三 Pipeline）
  - [ ] 9.1.3 更新核心特性列表

- [ ] 9.2 更新 README_PIPELINE.md
  - [ ] 9.2.1 添加表格处理流程说明
  - [ ] 9.2.2 添加配置参数文档
  - [ ] 9.2.3 添加使用示例（命令行 + Python 代码）
  - [ ] 9.2.4 添加输出格式示例

- [ ] 9.3 代码示例
  - [ ] 9.3.1 在 `examples/` 添加 `table_pipeline_example.py`
  - [ ] 9.3.2 演示基本用法
  - [ ] 9.3.3 演示自定义配置

- [ ] 9.4 代码文档
  - [ ] 9.4.1 为所有类添加 docstring
  - [ ] 9.4.2 为关键方法添加注释
  - [ ] 9.4.3 添加类型注解

## 10. 依赖与环境

- [ ] 10.1 更新 requirements.txt
  - [ ] 10.1.1 添加 beautifulsoup4 或 lxml（HTML 解析）
  - [ ] 10.1.2 添加 html2text（可选）
  - [ ] 10.1.3 固定版本号

- [ ] 10.2 环境变量
  - [ ] 10.2.1 在 `.env.example` 添加表格处理相关配置
  - [ ] 10.2.2 文档化新增的环境变量

## 11. OpenSpec 更新

- [ ] 11.1 更新 `openspec/project.md`
  - [ ] 11.1.1 更新 Purpose 部分（三模态系统）
  - [ ] 11.1.2 更新 Pipeline 架构图（添加 table pipeline）
  - [ ] 11.1.3 更新数据处理流程
  - [ ] 11.1.4 更新项目结构

- [ ] 11.2 标记提案完成状态
  - [ ] 11.2.1 更新 proposal.md 状态为 Implemented
  - [ ] 11.2.2 添加实施总结和测试数据

## 任务优先级

**MVP（最小可用版本）** ✅ **已完成** 2025-11-12：
- [x] 任务 1（数据模型）✅
- [x] 任务 2（表格解析）✅
- [x] 任务 3（表格收集与过滤）✅
- [x] 任务 4（表格描述生成）✅
- [x] 任务 5（实体提取与对齐）✅ **含关键bug修复**
- [x] 任务 6（主 Pipeline）✅
- [x] 任务 7（集成优化）✅
- [ ] 任务 8.2（集成测试）⏳ 部分完成（基本功能已验证）

**后续完善**：
- [ ] 任务 8.1（单元测试）
- [ ] 任务 8.3（性能测试）
- [ ] 任务 9（文档更新）
- [ ] 任务 10（依赖管理）
- [ ] 任务 11（OpenSpec 更新）

**核心功能清单** ✅ **全部完成**：
- [x] 表格收集与过滤（type="table"）
- [x] HTML 表格解析（BeautifulSoup4）
- [x] 表格描述生成（qwen-plus-latest）
- [x] Signal 类实体提取（数据指标）
- [x] 实体对齐（共享 OntologyAligner）**Bug已修复**
- [x] 输出格式统一（与 text/image pipeline 一致）
- [x] 容错机制（JSON 自动修复）
- [x] 简洁日志（参考现有 pipeline 风格）

**关键Bug修复记录** (2025-11-12):
- **问题**: `AttributeError: 'list' object has no attribute 'items'`
- **根因**: `TableEntityExtractor.align_entities()` 传递 `List[Entity]` 给 `OntologyAligner.align_entities()`，但后者期望 `Dict[str, Entity]`
- **修复**: 
  - 改用 `entities_dict = {}` 构建字典（Line 294）
  - 使用 `entities_dict[entity.name] = entity` 填充（Line 307）
  - 迭代改为 `for name, aligned_entity in aligned_entities.items()`（Line 313）
  - 实体查找改为基于name的查找（Line 314-316）
- **状态**: ✅ 已修复并验证

## 预估工作量

- **Day 1**: 任务 1-3（数据模型、表格解析、收集过滤）
- **Day 2**: 任务 4（描述生成 + 提示词优化）
- **Day 3**: 任务 5-6（实体提取 + 主 Pipeline）
- **Day 4**: 任务 7-8.2（集成测试 + Bug 修复）
- **Day 5**: 任务 9-11（文档更新 + OpenSpec 更新）

**总计**: 约 5 个工作日

## 参考资料

- **Image Pipeline 实现**: `pipelines/image_pipeline.py`
- **Text Pipeline 实现**: `pipelines/text_pipeline.py`
- **OntologyAligner**: `text_pipeline.OntologyAligner`
- **RAGAnything 源码**: `raganything/modalprocessors.py` - `TableModalProcessor`
- **提示词模板**: `pipelines/prompts/image_description.txt`
