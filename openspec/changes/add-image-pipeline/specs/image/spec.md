# Delta for Image Pipeline

## ADDED Requirements

### Requirement: 图片内容过滤
系统 MUST 过滤不需要处理的图片，包括表格图片和低质量图片。

#### Scenario: 过滤表格图片
- GIVEN content_list 中存在 type="table" 的条目
- WHEN 该条目包含 img_path 字段
- THEN 系统 SHALL 收集该图片路径到表格图片集合
- AND 当处理到该路径的 type="image" 条目时
- THEN 系统 SHALL 跳过该图片，不进行描述生成

#### Scenario: 过滤低质量图片
- GIVEN 一个 type="image" 的条目
- WHEN 根据 bbox 计算的像素数小于配置的最小像素数（默认10000）
- OR 宽高比小于最小值（默认0.3）或大于最大值（默认3.0）
- THEN 系统 SHALL 跳过该图片
- AND 记录过滤原因到日志

### Requirement: 上下文感知描述生成
系统 MUST 结合图片内容和周围文本上下文生成结构化描述。

#### Scenario: 提取图片上下文
- GIVEN 一个 type="image" 的条目在 content_list 中的索引
- WHEN 系统提取上下文时
- THEN 系统 SHALL 向前查找最近的标题（text_level=1 或 text_level=2）
- AND 提取该图片前后指定窗口内（默认前后各2个）的文本段落
- AND 提取该图片的 image_caption 和 image_footnote
- AND 组合为完整的上下文对象

#### Scenario: 生成图片描述
- GIVEN 图片文件路径和上下文对象
- WHEN 调用多模态 LLM 时
- THEN 系统 SHALL 将图片编码为 base64
- AND 使用提示词模板渲染完整提示词（包含 caption 和 context）
- AND 调用配置的多模态模型（默认 qwen-vl-max）
- AND 解析 JSON 响应为 ImageDescription 对象
- AND ImageDescription MUST 包含字段：entity_name, type, detailed_description

#### Scenario: 描述生成失败重试
- GIVEN LLM API 调用失败
- WHEN 失败次数小于最大重试次数（默认3次）
- THEN 系统 SHALL 使用指数退避策略重试
- AND 当达到最大重试次数后
- THEN 系统 SHALL 记录错误日志并跳过该图片

### Requirement: 描述补充到原始数据
系统 MUST 将生成的描述补充到输入的 content_list.json 中。

#### Scenario: 更新 JSON 条目
- GIVEN 成功生成的 ImageDescription 对象
- WHEN 更新原始 content_list 中的对应条目时
- THEN 系统 SHALL 添加以下字段：
  - entity_name: 图片的核心实体名称
  - type: 图片类型（更新原 type 字段为具体类型）
  - detailed_description: 详细描述文本
- AND 保留原有的 img_path, bbox, page_idx 等字段

#### Scenario: 保存更新后的文件
- GIVEN 所有图片处理完成
- WHEN 保存输出文件时
- THEN 系统 SHALL 将更新后的 content_list 保存为原文件名
- AND 文件格式 MUST 保持有效的 JSON 格式
- AND 使用 UTF-8 编码，ensure_ascii=False

### Requirement: 知识实体提取
系统 MUST 从图片描述中提取结构化的实体和关系。

#### Scenario: 提取图片实体
- GIVEN 成功生成的 ImageDescription
- WHEN 进行实体提取时
- THEN 系统 SHALL 至少创建一个主实体（代表图片本身）
- AND 主实体 MUST 包含字段：
  - entity_name: 来自 ImageDescription.entity_name
  - entity_type: 来自 ImageDescription.type
  - source_image: 图片路径（用于追溯）
  - description: 详细描述
- AND 系统 MAY 从 detailed_description 中提取细粒度子实体

#### Scenario: 输出知识图谱
- GIVEN 从所有图片提取的实体集合
- WHEN 输出知识图谱时
- THEN 系统 SHALL 保存为 *_content_list_kg_aligned.json
- AND 文件格式 MUST 包含实体列表和关系列表
- AND 每个实体 MUST 包含 source_image 字段

### Requirement: 配置管理
系统 MUST 支持灵活的配置参数。

#### Scenario: 使用默认配置
- GIVEN 用户未提供自定义配置
- WHEN 初始化 ImageKnowledgeGraphPipeline 时
- THEN 系统 SHALL 使用 ImagePipelineConfig 的默认值：
  - min_pixel_count: 10000
  - min_aspect_ratio: 0.3
  - max_aspect_ratio: 3.0
  - context_window: 2
  - multimodal_model: "qwen-vl-max"

#### Scenario: 自定义配置
- GIVEN 用户提供自定义配置对象
- WHEN 初始化 ImageKnowledgeGraphPipeline 时
- THEN 系统 SHALL 使用用户提供的配置覆盖默认值

### Requirement: 错误处理与日志
系统 MUST 提供完善的错误处理和日志记录。

#### Scenario: 图片文件不存在
- GIVEN 某个图片的 img_path 指向不存在的文件
- WHEN 尝试读取该图片时
- THEN 系统 SHALL 记录警告日志
- AND 跳过该图片，继续处理下一个

#### Scenario: JSON 解析失败
- GIVEN LLM 返回的内容不是有效的 JSON
- WHEN 解析响应时
- THEN 系统 SHALL 捕获异常
- AND 记录错误日志（包含原始响应内容）
- AND 跳过该图片

#### Scenario: 记录处理进度
- GIVEN 处理多张图片时
- WHEN 每完成一张图片的处理
- THEN 系统 SHALL 记录 INFO 级别日志
- AND 日志 MUST 包含：图片路径、处理状态、entity_name

### Requirement: 代码质量标准
代码 MUST 遵循项目规范和最佳实践。

#### Scenario: 代码风格一致性
- GIVEN 项目已有 text_pipeline.py
- WHEN 编写 image_pipeline.py 时
- THEN 代码风格 MUST 与 text_pipeline.py 保持一致
- AND 使用相同的命名约定（类名、方法名、变量名）
- AND 使用相同的日志格式和错误处理模式

#### Scenario: 类型注解完整性
- GIVEN 所有公共方法和关键私有方法
- WHEN 编写代码时
- THEN 每个方法 MUST 包含完整的类型注解（参数和返回值）
- AND 复杂类型 SHOULD 使用 typing 模块的类型别名

#### Scenario: 文档字符串
- GIVEN 所有类和公共方法
- WHEN 编写代码时
- THEN 每个类 MUST 包含 docstring（描述职责和用途）
- AND 每个公共方法 MUST 包含 docstring（描述参数、返回值、异常）
- AND 使用 Google 风格或 NumPy 风格的 docstring 格式
