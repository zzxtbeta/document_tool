# Project Context

## Purpose
文档知识图谱提取工具 - 基于 RAG-Anything 论文思路,提供**双模态知识图谱提取系统**。通过**文本 Pipeline** 和 **图片 Pipeline** 两条并行处理流程,从非结构化文档中自动构建结构化知识图谱,服务于投资研究、智能分析等场景。

**核心能力**:
- 📄 **文本处理 Pipeline**: 文档解析、文本提取、实体关系抽取(并行化处理)
- 🎨 **图片处理 Pipeline**: 多模态理解、上下文感知描述生成、视觉实体提取
- 🧠 基于 LLM 的智能实体关系抽取(文本模型 + 多模态模型)
- 🎯 本体对齐与知识标准化(Company/Person/Technology/Signal/Product/TagConcept 等6+1核心类型)
- 📊 双版本知识图谱输出(细粒度原始数据 + 标准化对齐数据)
- 🔗 格式统一输出(文本和图片知识图谱可直接合并)
- 🗄️ 知识图谱持久化(PostgreSQL + Neo4j)

## Tech Stack

### 开发环境
- **操作系统**: Windows
- **Python环境管理**: Conda
- **虚拟环境**: `conda activate document`
- **Python版本**: Python 3.11.11 (严格版本锁定)

### 核心技术栈
- **Language**: Python 3.11.11 (严格版本锁定)
- **Web Framework**: FastAPI (RESTful API 服务)
- **OCR引擎**: EasyOCR (图片文本识别，用于图片质量过滤)
- **图像处理**: Pillow (PIL) + OpenCV (可选)
- **Databases**: 
  - PostgreSQL 17 (关系型数据存储、实体属性管理)
  - Neo4j (图数据库、关系网络查询)
- **Agent Framework**: LangGraph (AI Agent 编排)
- **LLM Integration**: 
  - LangChain OpenAI (LLM 调用封装)
  - 通义千问 Qwen (默认模型: qwen-plus-latest)
  - 通义千问 Qwen3-VL-Flash (多模态模型，图片描述生成)
- **Static Type Checking**: mypy (类型安全保证)
- **Testing**: pytest (单元测试与集成测试)

### 依赖库
- **Pydantic**: 数据验证与 Schema 定义
- **dotenv**: 环境变量管理
- **asyncio**: 异步编程支持
- **concurrent.futures**: 并行处理与多线程
- **EasyOCR**: OCR文本识别（图片质量过滤）
- **tqdm**: 进度条显示
- **Pillow (PIL)**: 图像处理基础库
- **base64**: 图片编码（跨平台兼容性）

### 环境安装

**Windows + Conda 环境配置**:
```bash
# 1. 激活虚拟环境
conda activate document

# 2. 安装 OCR 依赖（用于图片文本过滤）
pip install easyocr

# 3. 验证安装
python -c "import easyocr; print('EasyOCR installed successfully')"
```

**注意事项**:
- EasyOCR 首次运行会下载模型文件（~500MB），需要稳定网络
- 如果下载失败，可手动下载模型到 `~/.EasyOCR/model/`
- 低配电脑建议使用 `--ocr-engine none` 跳过文本过滤

## Project Conventions

### Code Style
- **类型注解**: 强制使用 Python type hints,所有函数参数和返回值必须标注类型
- **编码规范**: 严格遵循 PEP 8
- **静态检查**: 使用 mypy 进行静态类型检查,通过后才能合并
- **命名规范**:
  - 函数/变量: `snake_case`
  - 类名: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
  - 私有成员: 前缀 `_`
- **Docstring**: 使用 Google Style docstring,包含参数说明、返回值和示例
- **日志记录**: 使用标准 logging 模块,格式: `时间 - 模块 - 级别 - 消息`

### Architecture Patterns

#### 双 Pipeline 架构

**文本 Pipeline** (`pipelines/text_pipeline.py`):
```
DocumentLoader → ChunkGrouper → EntityExtractor (并行) 
  → EntityDeduplicator → OntologyAligner → KnowledgeGraphBuilder
  → 输出: *_text_kg_raw.json + *_text_kg_aligned.json
```

**图片 Pipeline** (`pipelines/image_pipeline.py`):
```
ContentLoader → TableImageCollector → ImageFilter (三级过滤)
  → ContextExtractor → MultimodalDescriptor (Qwen3-VL-Flash)
  → ImageEntityExtractor → OntologyAligner
  → 输出: *_image_kg_raw.json + *_image_kg_aligned.json
```

**架构原则**:
- **单一职责**: 每个组件只负责一个明确的任务
- **Pipeline 模式**: 数据流式处理,组件可插拔
- **并行优化**: 文本Pipeline使用 ThreadPoolExecutor 并行处理,显著提升速度
- **格式统一**: 两条Pipeline输出格式完全一致(entities为Dict结构),可直接合并
- **独立运行**: 两条Pipeline可独立运行或组合使用

#### 数据模型设计
- **Pydantic BaseModel**: 所有数据结构继承 BaseModel,确保类型安全
- **Schema 驱动**: LLM 结构化输出基于 Pydantic Schema
- **双版本输出**: 保留原始细粒度数据(raw) + 标准化对齐数据(aligned)

#### API 设计
- **RESTful 风格**: 资源导向的 URL 设计
- **异步优先**: FastAPI 端点使用 async/await
- **分层架构**:
  - **Controller 层**: API 路由与请求验证
  - **Service 层**: 业务逻辑编排
  - **Repository 层**: 数据访问与持久化

### Testing Strategy
- **测试框架**: pytest + pytest-asyncio
- **测试分层**:
  - **单元测试**: 覆盖核心业务逻辑(实体提取、去重、对齐等)
  - **集成测试**: API 端点测试、数据库交互测试
  - **E2E 测试**: 完整 Pipeline 流程测试
- **测试文件**: `test_*.py` 或 `*_test.py`
- **Mock 策略**: 使用 pytest-mock 模拟 LLM 调用,避免测试依赖外部 API
- **覆盖率目标**: 核心逻辑 >80%

### Git Workflow
- **分支策略**: 
  - `main`: 生产稳定版本
  - `develop`: 开发主分支
  - `feature/*`: 功能开发分支
  - `fix/*`: Bug 修复分支
- **提交规范**: 
  - 使用语义化提交信息(可选 Conventional Commits)
  - 格式: `类型(范围): 简短描述`
  - 示例: `feat(pipeline): 添加本体对齐功能`, `fix(extractor): 修复实体去重bug`
- **Code Review**: 所有代码合并前必须经过 review
- **CI/CD**: (规划中)自动化测试、类型检查、代码质量检测

## Domain Context

### 知识图谱本体
基于投资研究领域的核心本体设计:

#### 核心实体类型(6+1)
1. **Company** - 公司/组织(投资标的、可比公司)
2. **Person** - 人物(创始人、高管、研究者)
3. **Technology** - 技术/概念(技术路线、算法、专利)
4. **TagConcept** - 赛道/标签(细分领域、行业分类)
5. **Event** - 事件(融资、新闻、政策)
6. **Signal** - 信号(指标、趋势、风险点)
7. **Other** - 其他(Fallback 类型)

#### 核心关系类型(15+)
- `founded_by` - 创立关系
- `invested_by` - 投资关系
- `works_at` - 任职关系
- `uses_technology` - 技术使用
- `in_segment` - 赛道归属
- `competes_with` - 竞争关系
- `supplies_to` - 供应关系
- 等(详见 `docs/ontology构建.md`)

### 数据处理流程

#### 文本 Pipeline 流程
1. **文档加载**: 从 JSON 格式解析文档(支持文本、表格)
2. **动态分组**: 按字符长度智能分组,支持跨页合并(可配置 chunk_size)
3. **并行提取**: 多线程并发调用 LLM 提取实体关系(可配置 max_workers)
4. **实体去重**: 基于相似度的智能去重与合并(threshold: 0.85)
5. **本体对齐**: 将细粒度实体映射到核心本体类型
6. **图谱构建**: 生成双版本知识图谱(raw + aligned)

#### 图片 Pipeline 流程
1. **表格识别**: 收集所有 type="table" 的图片路径,标记为黑名单
2. **三级过滤**: 
   - 表格过滤: 排除黑名单图片
   - 分辨率过滤: 过滤低分辨率图片(s=28万/m=60万/l=120万像素)
   - OCR文本过滤: 过滤文字量过少的图片(默认<10字符)
3. **上下文提取**: 提取图片标题、章节标题、前后文本段落
4. **多模态描述**: 使用 Qwen3-VL-Flash 生成图片结构化描述
5. **实体提取**: 从图片描述中提取实体和关系
6. **本体对齐**: 映射到核心本体类型(与文本Pipeline共享OntologyAligner)
7. **图谱构建**: 生成双版本知识图谱(raw + aligned,格式与文本Pipeline一致)

## Important Constraints

### 技术约束
- **Python 版本**: 严格锁定 3.11.11,不兼容 3.12+(避免依赖兼容性问题)
- **LLM 调用**: 
  - 使用通义千问 API,需配置 `DASHSCOPE_API_KEY`
  - 注意 API 调用成本控制(大文档会触发多次调用)
  - 重试机制: 默认 2 次,避免过度重试
- **内存管理**: 大文档处理时注意内存占用,必要时分批处理
- **并发限制**: 
  - 低配电脑建议 `max_workers=1-2`
  - 高配电脑可设置 `max_workers=8+`
  - 避免超出 API 并发限制

### 数据约束
- **输入格式**: 要求 JSON 格式,必须包含 `type` 和 `page_idx` 字段
- **实体去重**: 相似度阈值 0.85,可调整但不建议低于 0.8
- **本体映射**: 未匹配到核心类型的实体归入 `Other`,需人工审核

### 业务约束
- **数据溯源**: 所有抽取结果必须包含 `provenance` 证据链(来源、时间、置信度)
- **审计要求**: 知识图谱需支持回溯与版本管理
- **隐私合规**: 敏感信息(如人物详情)需脱敏处理

## External Dependencies

### 数据库服务
- **PostgreSQL 17**: 
  - 连接池管理(使用 asyncpg 或 psycopg3)
  - 实体表、关系表、事件表的设计
  - 全文搜索索引(用于实体检索)
- **Neo4j**: 
  - 图查询语言 Cypher
  - 关系网络分析与路径发现
  - 与 PostgreSQL 的数据同步机制

### LLM 服务
- **通义千问(Qwen)**:
  - API 端点: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 默认模型: `qwen-plus-latest`
  - 需配置 API Key: `DASHSCOPE_API_KEY`

### AI Agent 框架
- **LangGraph**: 
  - Agent 状态管理
  - 复杂工作流编排
  - 与 LangChain 的集成

### 开发工具
- **dotenv**: 环境变量加载(`.env` 文件管理)
- **logging**: 标准日志模块
- **concurrent.futures**: Python 标准库并发处理

## Configuration Management

### 环境变量(必需)
```bash
DASHSCOPE_API_KEY=your_api_key_here          # 必需: LLM API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus-latest                   # 默认文本模型
MULTIMODAL_MODEL=qwen3-vl-flash               # 多模态图片模型
KG_CHUNK_SIZE=512                             # chunk 分组大小(字符数)
KG_MAX_WORKERS=3                              # 并行线程数
KG_PARALLEL=true                              # 是否启用并行

# 图片处理配置
IMAGE_OCR_ENGINE=auto                         # OCR引擎: auto|easyocr|pytesseract|paddleocr|none
IMAGE_RES_PRESET=s                            # 分辨率预设: s(28万)|m(60万)|l(120万)|off
IMAGE_MIN_TEXT_LEN=10                         # OCR文本最小长度
```

### 命令行参数(可选)

**文本处理 Pipeline**:
- `-m, --model`: 指定 LLM 模型
- `-t, --temperature`: 生成温度(0.0-1.0,默认 0.3)
- `-s, --similarity`: 实体去重相似度阈值(默认 0.85)
- `-c, --chunk-size`: Chunk 大小(默认 512)
- `-w, --workers`: 并行线程数(默认 3)
- `--no-parallel`: 禁用并行处理

**图片处理 Pipeline**:
- `--ocr-engine`: OCR引擎选择 (auto|easyocr|pytesseract|paddleocr|none, 默认auto)
- `--res-preset`: 分辨率过滤预设 (s|m|l|off, 默认s=28万像素)
- `--min-text-len`: OCR文本最小长度 (默认10字符)
- `--multimodal-model`: 多模态模型 (默认qwen3-vl-flash)
- `--context-window`: 上下文窗口大小 (默认2)
- `--verbose`: 显示详细日志

## Project Structure
```
document_tool/
├── pipelines/              # 处理流程模块 (v1.4+)
│   ├── text_pipeline.py    # 文本处理 Pipeline
│   ├── image_pipeline.py   # 图片处理 Pipeline (v1.4.1)
│   ├── image_models.py     # 图片数据模型
│   ├── __init__.py         # 包初始化
│   └── prompts/            # 提示词模板
│       ├── image_description.txt        # 多模态描述生成提示词
│       └── image_entity_extraction.txt  # 图片实体提取提示词
├── api.py                  # FastAPI 服务 (v1.3+)
├── api_models.py           # API 数据模型
├── pipline.py              # 旧版文本 Pipeline (保留兼容)
├── README.md               # 项目总览
├── README_PIPELINE.md      # Pipeline 详细文档
├── .env                    # 环境变量配置(不提交)
├── examples/               # 使用示例
│   ├── api_usage.py
│   └── curl_examples.sh
├── parsed/                 # 解析输出目录
│   └── [document_name]/
│       └── auto/
│           ├── *_content_list.json           # MinerU 输出
│           ├── *_text_kg_raw.json           # 文本 Pipeline 原始输出
│           ├── *_text_kg_aligned.json       # 文本 Pipeline 对齐输出
│           ├── *_image_kg_raw.json          # 图片 Pipeline 原始输出
│           └── *_image_kg_aligned.json      # 图片 Pipeline 对齐输出
├── docs/                   # 详细文档
│   ├── CHANGELOG_*.md      # 版本变更日志
│   ├── ontology构建.md     # 本体设计文档
│   └── RAGAnything.md      # RAG 架构文档
└── openspec/               # OpenSpec 规范管理
    ├── project.md          # 本文件
    ├── AGENTS.md           # AI Agent 工作流指南
    ├── specs/              # 功能规范
    └── changes/            # 变更提案
        └── add-image-pipeline/  # 图片Pipeline变更 (v1.4)
```
