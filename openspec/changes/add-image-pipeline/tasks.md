# 实现任务清单

## 1. 数据模型设计

- [x] 1.1 创建 `image_models.py` ✅ 2025-11-11
  - [x] 1.1.1 定义 `ImageDescription` 模型（entity_name, type, **description**） 
    - **修改**: `detailed_description` → `description` (简化命名)
  - [x] 1.1.2 定义 `ImageEntity` 模型（含 source_image 字段）
  - [x] 1.1.3 定义 `ImageKGOutput` 模型
  - [x] 1.1.4 定义 `ImagePipelineConfig` 配置类
  - [x] 1.1.5 添加类型注解和文档字符串
  - [x] 1.1.6 **新增**: `ImageRawData`, `ImageRawOutput` (两文件输出架构)

## 2. 图片过滤模块

- [x] 2.1 重构 `EnhancedImageFilter` 类 ✅ 2025-11-11
  - [x] 2.1.1 整合 `image_filter.py` 功能到 `image_pipeline.py`
    - 移除外部依赖，自包含OCR初始化
    - 支持 easyocr 引擎（可扩展其他引擎）
  - [x] 2.1.2 实现三级过滤逻辑
    - 表格图片排除（type="table"）
    - 分辨率过滤（RES_PRESETS: s/m/l/off）
    - OCR文本长度过滤（可配置阈值）
  - [x] 2.1.3 优化日志输出
    - 简洁的汇总日志（与text_pipeline风格一致）
    - verbose模式显示详细过滤列表
    - 修复表格图片统计显示错误

## 3. 上下文提取模块

- [x] 3.1 实现 `ContextExtractor` 类 ✅ 2025-11-10
  - [x] 3.1.1 实现 `extract_nearby_text()` 方法
    - 定位当前图片在 content_list 中的索引
    - 向前查找最近的标题（text_level=1 或 text_level=2）
    - 向前后查找指定窗口内的文本段落
    - 组合为上下文字符串
  - [x] 3.1.2 实现 `extract_caption()` 方法
    - 获取 image_caption 列表
    - 获取 image_footnote 列表
    - 合并为完整的图片标题文本
  - [x] 3.1.3 实现 `combine_context()` 方法
    - 组合标题、caption、周围文本
    - 返回结构化的上下文对象
  - [x] 3.1.4 处理边界情况（首尾图片、缺失上下文）

## 4. 多模态描述生成模块

- [x] 4.1 创建 `prompts/image_description.txt` 提示词模板 ✅ 2025-11-11
  - [x] 4.1.1 编写优化版提示词（聚焦核心商业价值）
    - **重点**: 提取公司、产品、技术、数据指标
    - **禁止**: 反斜杠`\`、换行符、控制字符等特殊字符
    - **精炼**: 100字以内描述，3-5个关键要素
  - [x] 4.1.2 添加 JSON 输出格式要求（严格规范）
  - [x] 4.1.3 更新示例（钛禾智库资源能力结构图）
  
- [x] 4.2 实现 `MultimodalDescriptor` 类 ✅ 2025-11-10
  - [x] 4.2.1 初始化多模态 LLM 客户端（qwen3-vl-flash）
  - [x] 4.2.2 实现 `generate_description()` 方法
    - Base64 编码图片（跨平台兼容）
    - 渲染提示词模板
    - 调用 LLM API
    - 鲁棒 JSON 解析（4种策略容错）
  - [x] 4.2.3 添加重试机制和错误处理（指数退避）
  - [x] 4.2.4 **修复**: JSON解析失败问题（2025-11-11）
    - 提示词中明确禁止反斜杠等特殊字符
    - 增强容错：自动检测并修复非法转义序列
    - 正则替换：`\(?!["\\/bfnrtu])` → `/`
    - 测试结果：11/11 图片成功解析（100%成功率）

## 5. 图片实体提取模块 

- [x] 5.1 创建 `prompts/image_entity_extraction.txt` 提示词模板 ✅ 2025-11-11
  - [x] 5.1.1 参考 `text_pipeline` 的严格规范
    - **核心实体类型**: Company, Person, Product, Technology, TagConcept, Metric
    - **严格属性**: industry/stage/role/version/value等
    - **禁止提取**: 通用概念、流程术语、图表元素
  - [x] 5.1.2 添加数量控制（3-8个实体，2-6个关系）
  - [x] 5.1.3 更新示例（象量投研大数据能力闭环图）

- [x] 5.2 实现 `ImageEntityExtractor` 类 ✅ 2025-11-11
  - [x] 5.2.1 实现 `extract_entities_from_description()` 方法
    - 使用 qwen-plus 提取实体和关系
    - 鲁棒 JSON 解析（复用多策略容错）
    - 为每个实体添加 source_image 和 page_idx
  - [x] 5.2.2 实现 `align_entities()` 方法（**重构** 2025-11-11）
    - 加载 `text_pipeline.OntologyAligner`
    - 转换为 Entity 对象格式
    - 调用对齐逻辑，映射到核心类型
    - 保留 source_image 和 page_idx 元信息
    - **返回格式**: Dict[str, Dict] (与text_pipeline一致)
  - [x] 5.2.3 **修复**: OntologyAligner 初始化错误（2025-11-11）
    - 改为无参数构造：`OntologyAligner()`
    - 测试结果：80个实体成功对齐
  - [x] 5.2.4 实体对齐统计（2025-11-11）
    - Company: 21, Technology: 20, Signal: 21
    - Product: 9, TagConcept: 9

## 6. 主 Pipeline 实现

- [x] 6.1 创建 `image_pipeline.py` ✅ 2025-11-10 (更新 2025-11-12)
  - [x] 6.1.1 定义 `ImageKnowledgeGraphPipeline` 类
  - [x] 6.1.2 实现 `__init__()` 方法（初始化配置和组件）
  - [x] 6.1.3 实现 `load_content_list()` 方法
  - [x] 6.1.4 实现 `collect_table_images()` 和 `filter_images()` 方法
    - 收集 type="table" 作为黑名单
    - 过滤低质量图片（分辨率、OCR文本长度）
  - [x] 6.1.5 实现 `process_single_image()` 方法（**重构** 2025-11-11）
    - 提取上下文
    - 生成描述
    - **新增**: LLM提取实体和关系
    - 返回 {raw_data, raw_entities, raw_relations}
  - [x] 6.1.6 实现 `run()` 主方法（**重构** 2025-11-11）
    - 收集所有 raw_data / raw_entities / raw_relations
    - 调用实体对齐
    - 生成两个文件输出
  - [x] 6.1.7 实现 `save_outputs()` 方法（**重构** 2025-11-11, **修复** 2025-11-12）
    - **文件1**: `*_image_kg_raw.json`
      - metadata: total_images, total_entities, entity_types
      - images: 图片描述列表
      - entities: Dict[name, entity] (字典格式)
      - relations: 关系列表
    - **文件2**: `*_image_kg_aligned.json`
      - metadata: ontology_version="v1.2.1", data_source="image_pipeline"
      - aligned_entities: Dict[name, aligned_entity] (字典格式)
      - aligned_relations: 对齐后的关系
    - **格式统一**: 与text_pipeline输出完全一致，可直接合并
    - **修复** (2025-11-12): 输出文件命名错误（`_image_kg_aligned.json` 而非混淆的`_content_list_text_kg_aligned.json`.replace版本）
  - [x] 6.1.8 添加命令行参数支持
  - [x] 6.1.9 **优化**: 日志系统全面改进（2025-11-12）
    - 参考text_pipeline/table_pipeline风格，保持简洁清晰
    - verbose/non-verbose双模式（tqdm进度条 vs 详细日志）
    - 添加start_time跟踪和耗时统计
    - 实体类型分布统计
    - 统一分隔符（`=` * 60）
    - save_outputs()返回文件路径用于最终汇总

## 7. 集成与优化

- [x] 7.1 日志系统 ✅ 2025-11-12 (全面改进)
  - [x] 7.1.1 配置 logging（统一日志格式）
  - [x] 7.1.2 在关键步骤添加日志（过滤、描述生成、实体提取）
  - [x] 7.1.3 添加进度条（tqdm，支持verbose控制）
  - [x] 7.1.4 **新增** (2025-11-12): 日志风格同步
    - 与table_pipeline保持一致的简洁风格
    - verbose模式详细日志：`[1/11] 处理图片: images/xxx.jpg (页码: 4)`
    - non-verbose模式进度条
    - 实体类型分布统计
    - 耗时统计和文件路径汇总

- [x] 7.2 错误处理 ✅ 2025-11-11
  - [x] 7.2.1 处理图片文件不存在（跳过并记录）
  - [x] 7.2.2 处理 LLM API 调用失败（异常捕获）
  - [x] 7.2.3 处理 JSON 解析错误（多策略容错+自动修复）
  - [x] 7.2.4 添加降级策略（失败时跳过，记录日志）

- [x] 7.3 配置管理 ✅ 2025-11-10
  - [x] 7.3.1 支持从环境变量读取配置（通过dotenv）
  - [x] 7.3.2 使用dataclass配置（ImagePipelineConfig）
  - [x] 7.3.3 提供默认配置（res_preset="s", min_text_len=10等）

## 8. 测试与验证

- [x] 8.1 MVP测试 ✅ 2025-11-10
  - [x] 8.1.1 测试多模态描述生成（100%成功率）
  - [x] 8.1.2 验证 Base64 编码和JSON解析

- [x] 8.2 集成测试 ✅ 2025-11-11
  - [x] 8.2.1 使用 `象量科技项目介绍20250825_content_list.json` 测试
  - [x] 8.2.2 发现并修复问题（2025-11-11 完成）：
    - **问题1**: JSON解析失败（特殊字符）→ 已修复（容错+自动修复）
    - **问题2**: OntologyAligner初始化错误 → 已修复（无参构造）
    - **问题3**: 实体提取过于冗余 → 已优化prompt
    - **问题4**: image_filter依赖缺失 → 已整合到pipeline
    - **问题5**: 输出格式不一致 → 已统一为字典格式
    - **问题6**: 日志过于冗长 → 已简化为text_pipeline风格
  - [x] 8.2.3 验证两文件输出格式（完全符合设计）
  - [x] 8.2.4 验证实体对齐功能（80个实体成功对齐）
  - [x] 8.2.5 **最终测试结果** (2025-11-11 17:20):
    - ✅ 图片处理成功率: 11/11 (100%)
    - ✅ JSON解析成功率: 11/11 (100%，含1次自动修复)
    - ✅ 表格图片识别: 5张正确排除
    - ✅ 过滤统计: 24张原始 → 11张有效
    - ✅ 实体提取: 80个对齐实体，67个关系
    - ✅ 输出格式: 与text_pipeline完全一致

- [ ] 8.3 性能优化（待完成）
  - [ ] 8.3.1 测量单张图片处理耗时
  - [ ] 8.3.2 统计 token 消耗
  - [ ] 8.3.3 优化批处理策略

## 9. 文档与示例

- [ ] 9.1 更新 README_PIPELINE.md
  - [ ] 9.1.1 添加图片处理流程说明
  - [ ] 9.1.2 添加配置参数文档
  - [ ] 9.1.3 添加使用示例

- [ ] 9.2 代码示例
  - [ ] 9.2.1 在 `examples/` 添加 `image_pipeline_example.py`
  - [ ] 9.2.2 演示基本用法
  - [ ] 9.2.3 演示自定义配置

- [ ] 9.3 代码文档
  - [ ] 9.3.1 为所有类添加 docstring
  - [ ] 9.3.2 为关键方法添加注释
  - [ ] 9.3.3 添加类型注解

## 10. 依赖与环境

- [ ] 10.1 更新 requirements.txt
  - [ ] 10.1.1 添加多模态依赖（如需新包）
  - [ ] 10.1.2 固定版本号

- [ ] 10.2 环境变量
  - [ ] 10.2.1 在 `.env.example` 添加图片处理相关配置
  - [ ] 10.2.2 文档化新增的环境变量

## 任务优先级

**MVP（最小可用版本）** ✅ 已完成 2025-11-11：
- ✅ 任务 1（数据模型）
- ✅ 任务 2（图片过滤）
- ✅ 任务 3（上下文提取）
- ✅ 任务 4（多模态描述生成）
- ✅ 任务 5（实体提取与对齐）
- ✅ 任务 6（主 Pipeline）
- ✅ 任务 7（集成优化）
- ✅ 任务 8.2（集成测试）

**待完成**：
- [ ] 任务 8.3（性能优化）- 可选
- [ ] 任务 9（文档更新）
- [ ] 任务 10（依赖管理）

**已完成核心功能**：
- ✅ 三级图片过滤（表格/分辨率/文本）
- ✅ 多模态描述生成（qwen3-vl-flash）
- ✅ 实体提取与对齐（80个实体，5种核心类型）
- ✅ 输出格式统一（与text_pipeline一致）
- ✅ 容错机制（JSON自动修复）
- ✅ 简洁日志（参考text_pipeline风格）
