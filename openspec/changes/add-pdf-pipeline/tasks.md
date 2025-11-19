# 任务清单: PDF 商业计划书智能解析管道

本文档列出实现 PDF 商业计划书智能解析功能的所有任务,按优先级和依赖关系组织。

## 阶段 1: MVP 后端核心功能 (2.5 周)

### 1.1 数据库设计 (1 天)

- [x] **创建数据库迁移文件** _(已完成: `db/migrations/create_pdf_extraction_tasks.sql`)_
  - 文件: `db/migrations/create_pdf_extraction_tasks.sql`
  - 创建 `pdf_extraction_tasks` 表
  - 添加索引: task_id, user_id, industry, task_status
  - 添加外键约束

- [x] **编写数据库操作函数** _(已完成: `db/pdf_operations.py`)_
  - 文件: `db/pdf_operations.py`
  - `create_pdf_extraction_task()` - 创建任务
  - `get_pdf_extraction_task()` - 查询单个任务
  - `list_pdf_extraction_tasks()` - 列表查询
  - `update_extraction_result()` - 更新结果
  - `update_task_status()` - 更新状态

- [ ] **测试数据库操作** _(未开始)_
  - 文件: `tests/test_pdf_db.py`
  - 测试 CRUD 操作
  - 测试查询过滤
  - 测试并发写入

### 1.2 PDF 处理管道 (3 天)

- [x] **安装和配置依赖** _(已在 `requirements.txt` 中加入 pdf2image/pillow/pypdf)_
  - 更新 `requirements.txt`:
    - `pdf2image>=1.17.0`
    - `pillow>=10.0.0`
    - `pypdf>=4.0.0`
  - Linux/Docker: 安装 `poppler-utils`
  - Windows: 配置 poppler 路径

- [x] **实现 PDF 转图片功能** _(已在 `pipelines/pdf_pipeline.py` 中实现)_
  - 文件: `pipelines/pdf_pipeline.py`
  - `PDFProcessor` 类
  - `convert_to_images()` 方法
    - 设置 DPI=300
    - 输出格式 JPEG
    - 错误处理(加密PDF、损坏文件)
  - `compress_image()` 方法
    - 目标大小 < 5MB
    - 保持可读性

- [x] **实现文件验证** _(已由 `PDFPipeline.validate_pdf`/`PDFValidator` 提供)_
  - 文件: `pipelines/pdf_validator.py`
  - `validate_pdf()` 函数
    - 检查文件大小 (< 50MB)
    - 验证 MIME 类型
    - 检查页数 (< 100)
    - 检查是否加密

- [ ] **测试 PDF 处理** _(未创建 `tests/test_pdf_processor.py`)_
  - 文件: `tests/test_pdf_processor.py`
  - 测试正常 PDF 转换
  - 测试大文件处理
  - 测试加密 PDF
  - 测试损坏文件

### 1.3 Qwen VL 集成 (3 天)

- [x] **创建 VL 客户端** _(逻辑已直接集成在 `pipelines/pdf_extraction_service.py` 中，使用 OpenAI 兼容接口)_
  - 文件: `pipelines/qwen_vl_client.py`
  - `QwenVLClient` 类
  - 配置 OpenAI 兼容模式
  - 实现 `extract_from_images()` 方法
    - 构建 multi-image messages
    - 启用高分辨率模式
    - 设置合理的 temperature
  - 实现 `_parse_json_response()` 方法
    - 正则提取 JSON
    - 容错处理

- [x] **设计提取 Prompt** _(已完成: `pipelines/prompts/bp_extraction.txt`)_
  - 文件: `pipelines/prompts/bp_extraction.txt`
  - 编写详细的字段说明
  - 添加输出格式示例
  - 强调 JSON 格式要求
  - 包含 15 个字段的详细定义

- [ ] **实现数据验证器** _(尚未实现 `pipelines/extraction_validator.py`, 目前仅 `_clean_data` 做最小清洗)_
  - 文件: `pipelines/extraction_validator.py`
  - `ExtractionValidator` 类
  - `validate()` 方法 - 检查必填字段
  - `clean()` 方法 - 标准化数据
  - 行业分类验证
  - 团队成员格式验证
  - 关键词数量验证

- [ ] **测试 VL 提取** _(测试用例待编写)_
  - 文件: `tests/test_qwen_vl.py`
  - Mock API 测试
  - 真实 API 集成测试
  - 测试不同类型的 BP
  - 测试错误响应处理

### 1.4 OSS 存储集成 (1 天)

- [x] **扩展 OSS 存储客户端** _(通用上传/文本写入已在 `pipelines/storage.py` 中实现，供 PDF/图片/结果复用)_
  - 文件: `pipelines/storage.py`
  - 添加 PDF 上传方法
  - 添加页面图片上传方法
  - 添加提取结果上传方法
  - 路径规范: `bronze/userUploads/{projectId}/pdf/{taskId}/`
  - 结果文件命名: `{source_filename}_extracted_info.json`

- [x] **实现 URL 签名** _(已提供 `generate_signed_url`)_
  - `get_signed_url()` 方法
  - 设置合理的过期时间(24小时)
  - 批量 URL 生成

- [ ] **测试 OSS 操作** _(测试用例未创建)_
  - 文件: `tests/test_pdf_storage.py`
  - 测试文件上传
  - 测试 URL 生成
  - 测试权限控制

### 1.5 Huey 任务队列实现 (2 天)

- [ ] **配置 Huey 任务队列** _(新增: `pipelines/tasks.py`)_
  - 文件: `pipelines/tasks.py`
  - 初始化 RedisHuey 实例
  - 配置 Redis 连接（含密码）
  - 配置 worker 参数（线程/进程数）
  - 配置重试策略（3 次重试）

- [ ] **实现 PDF 处理任务** _(新增: `pipelines/tasks.py`)_
  - `@huey.task()` 装饰器
  - `process_pdf_task(task_id)` - 异步处理 PDF
  - 错误处理和日志记录
  - 支持任务优先级

- [ ] **更新 PDFExtractionService** _(修改: `pipelines/pdf_extraction_service.py`)_
  - 移除 `submit_extraction()` 中的异步队列逻辑
  - 改为调用 `process_pdf_task.delay(task_id)`
  - 保持 `process_pdf()` 同步执行（由 Huey worker 调用）

- [ ] **更新 API 路由** _(修改: `api/pdf/routes.py`)_
  - 导入 `process_pdf_task` 从 `pipelines.tasks`
  - 在 `submit_extraction()` 后调用 `process_pdf_task(task_id)`
  - 移除 asyncio 队列相关代码

- [ ] **启动脚本** _(新增: `scripts/start_huey_worker.sh`)_
  - 启动 Huey worker 进程
  - 配置 worker 数量和类型
  - 日志输出配置

- [ ] **测试 Huey 集成** _(测试用例缺失)_
  - 文件: `tests/test_huey_tasks.py`
  - 测试任务提交
  - 测试任务执行
  - 测试重试机制
  - 测试错误处理

### 1.6 核心服务实现 (3 天)

- [x] **实现 PDFExtractionService** _(已完成: `pipelines/pdf_extraction_service.py`)_
  - `submit_extraction()` - 提交任务
    - 上传 PDF 到 OSS
    - 创建数据库记录
    - 启动异步处理
  - `process_pdf()` - 处理流程
    - 下载 PDF
    - 转换图片
    - 上传图片
    - 调用 VL 提取
    - 验证结果
    - 保存到 OSS 和数据库
  - `get_extraction_result()` - 查询结果（目前通过 DB/路由返回）

- [ ] **实现错误处理和重试** _(基础异常捕获已就绪，但尚未接入 `tenacity` 重试)_
  - 使用 `tenacity` 库
  - VL API 调用重试(3次)
  - 记录详细错误信息
  - 状态更新为 FAILED

- [x] **添加日志和监控** _(关键步骤已有结构化日志，性能指标待补)_
  - 关键步骤日志记录
  - 性能指标收集
  - Token 使用量统计

- [ ] **测试核心服务** _(测试用例未实现)_
  - 文件: `tests/test_pdf_extraction_service.py`
  - 端到端测试
  - 异常场景测试
  - 性能测试

### 1.7 API 路由实现 (2 天)

- [x] **创建 API 路由文件** _(已完成: `api/pdf/routes.py`)_
  - 文件: `api/routes/pdf_routes.py`
  - 定义路由组: `/api/v1/pdf`

- [x] **实现 POST /api/v1/pdf/extract** _(已在 `api/pdf/routes.py` 中提供单文件上传)_
  - 接收 multipart/form-data
  - **支持批量上传** (files: List[UploadFile])
  - 验证 PDF 文件 (大小、页数、格式)
  - 批量调用 `submit_extraction()`
  - 返回 task_id 列表

- [x] **实现 GET /api/v1/pdf/extract/{task_id}** _(已完成)_
  - 查询任务详情
  - 返回提取结果
  - 生成临时签名 URL

- [x] **实现 GET /api/v1/pdf/extract** _(已完成，含分页/筛选)_
  - 列表查询
  - 支持分页
  - 支持过滤(industry, status)
  - 支持排序(submitted_at)

- [x] **实现 GET /api/v1/pdf/queue/status** _(已完成，包含 DB 完成数统计)_
  - 返回队列大小
  - 返回活跃任务数
  - 返回待处理任务数

- [x] **创建 Pydantic 模型** _(已完成: `api/pdf/models.py`)_
  - 文件: `api/models/pdf_models.py`
  - `PDFExtractionRequest`
  - `PDFExtractionResponse`
  - `PDFTaskDetail`
  - `ExtractedInfo`

- [ ] **添加 API 文档** _(OpenAPI 示例/README 待补充)_
  - OpenAPI schema
  - 请求示例
  - 响应示例

- [x] **集成到主 API** _(已在 `api/main.py` 中注册路由并启用 CORS)_
  - 文件: `api/main.py`
  - 注册 PDF 路由
  - 添加 CORS 配置

- [ ] **测试 API 端点** _(缺少 `tests/test_pdf_api.py`)_
  - 文件: `tests/test_pdf_api.py`
  - 测试上传接口
  - 测试查询接口
  - 测试列表接口
  - 测试错误处理

### 1.8 MVP 测试和优化 (1 天)

- [ ] **端到端测试**
  - 准备测试 BP 样本(至少 5 份)
  - 完整流程测试
  - 验证提取准确性

- [ ] **性能优化**
  - 图片压缩参数调优
  - Prompt 优化
  - 数据库索引优化

- [ ] **文档更新**
  - API 使用文档
  - 部署说明
  - 故障排查指南

---

## 阶段 2: 前端界面开发 (1 周)

### 2.1 前端组件开发 (3 天)

- [x] **创建 PDF 批量上传组件** _(已完成: `frontend/src/components/pdf/PdfUploader.tsx`, 支持拖拽/批量/进度)_
  - 文件: `frontend/src/components/PDFBatchUploader.tsx`
  - **批量拖拽上传功能** (multiple files)
  - 文件列表展示 (含预览)
  - 单个文件上传进度条
  - 批量上传总进度
  - 错误提示 (大小、页数超限)
  - 支持移除单个文件

- [x] **创建队列状态组件** _(已完成: `frontend/src/components/pdf/PdfQueueStatus.tsx`)_
  - 文件: `frontend/src/components/PDFQueueStatus.tsx`
  - 显示当前队列大小
  - 显示正在处理的任务数
  - 显示待处理任务数
  - 实时更新 (轮询 5s)

- [x] **创建提取结果展示组件** _(已完成: `frontend/src/components/pdf/PdfExtractionResult.tsx`)_
  - 文件: `frontend/src/components/ExtractionResult.tsx`
  - 字段分组展示
    - 基本信息(公司、行业、联系人)
    - 团队信息(核心成员表格)
    - 产品与市场(产品、技术、竞争)
    - 财务与融资
  - 关键词标签云
  - 原始 JSON 查看

- [x] **创建任务列表组件** _(已完成: `frontend/src/components/pdf/PdfTaskPanel.tsx`，含状态过滤+轮询)_
  - 文件: `frontend/src/components/PDFTaskList.tsx`
  - 任务卡片
    - 文件名、状态、时间
    - 公司名、行业
  - 状态过滤器
  - 行业过滤器
  - 分页

- [x] **创建任务详情抽屉** _(已完成: `frontend/src/components/pdf/PdfTaskDetailDrawer.tsx`)_
  - 文件: `frontend/src/components/PDFTaskDrawer.tsx`
  - 显示完整提取信息
  - 下载原始 PDF 按钮
  - 下载 JSON 结果按钮

### 2.2 API 集成 (1 天)

- [x] **创建 API 客户端** _(已完成: `frontend/src/services/pdfApi.ts`，axios 拦截器仍待补)_
  - 文件: `frontend/src/services/pdfApi.ts`
  - `uploadPDF()` - 上传 PDF
  - `getTask()` - 查询任务
  - `listTasks()` - 列表查询

- [x] **创建状态管理** _(已完成: `frontend/src/store/usePdfStore.ts`)_
  - 文件: `frontend/src/store/usePDFStore.ts`
  - Zustand store
  - 任务列表状态
  - 上传状态
  - 过滤条件

### 2.3 页面整合 (2 天)

- [x] **创建 PDF 解析页面** _(已在 `src/App.tsx` 中通过 Tab 切换集成)_
  - 文件: `frontend/src/pages/PDFExtraction.tsx`
  - 上传区域
  - 任务列表
  - 筛选和搜索

- [ ] **路由配置** _(尚未接入 React Router, `/pdf-extraction` 路由未创建)_
  - 添加 `/pdf-extraction` 路由
  - 导航菜单集成

- [x] **样式优化** _(Tailwind 适配已完成)_
  - Tailwind CSS
  - 响应式布局
  - 加载状态

### 2.4 前端测试 (1 天)

- [ ] **单元测试** _(未开始)_
  - 组件渲染测试
  - 交互测试

- [ ] **E2E 测试** _(未开始)_
  - 上传流程测试
  - 查询流程测试

---

## 阶段 3: 生产准备 (1 周)

### 3.1 性能优化 (2 天)

- [ ] **批量处理优化**
  - 实现批量提取
  - 队列管理
  - 并发控制

- [ ] **缓存策略**
  - OSS URL 缓存
  - 查询结果缓存

- [ ] **数据库优化**
  - 查询性能分析
  - 索引优化
  - 连接池配置

### 3.2 安全加固 (1 天)

- [ ] **文件安全**
  - 文件类型严格验证
  - 病毒扫描集成(可选)
  - 文件大小限制

- [ ] **数据安全**
  - 敏感信息脱敏
  - API 权限控制
  - 用户数据隔离

- [ ] **API 安全**
  - Rate limiting
  - JWT 认证
  - CORS 配置

### 3.3 监控和告警 (2 天)

- [ ] **Metrics 集成**
  - Prometheus metrics
  - 关键指标监控
    - 任务成功率
    - 处理时长
    - Token 使用量
    - 错误率

- [ ] **日志系统**
  - 结构化日志
  - 日志聚合
  - 错误追踪

- [ ] **告警配置**
  - 失败率告警
  - 延迟告警
  - Token 超限告警

### 3.4 部署准备 (2 天)

- [ ] **环境变量配置**
  - 创建 `.env.example` 模板
  - 文档化所有可配置参数:
    - PDF_MAX_SIZE_MB (默认 50)
    - PDF_MAX_PAGES (默认 100)
    - PDF_CONVERSION_DPI (默认 300)
    - PDF_IMAGE_MAX_SIZE_MB (默认 10)
    - VL_HIGH_RESOLUTION_MODE (默认 false)
    - PDF_MAX_CONCURRENT_TASKS (默认 5)
    - PDF_QUEUE_SIZE (默认 100)
  - 在 README 中说明各参数的官方限制

- [ ] **Docker 镜像**
  - Dockerfile 优化
  - 多阶段构建
  - 镜像体积优化

- [ ] **环境配置**
  - 开发环境
  - 测试环境
  - 生产环境
  - 环境变量管理

- [ ] **CI/CD 配置**
  - 自动化测试
  - 自动化部署
  - 回滚机制

- [ ] **部署文档**
  - 部署步骤
  - 配置说明
  - 故障排查

---

## 阶段 4: 扩展功能 (可选)

### 4.1 高级功能

- [ ] **批量上传**
  - 支持一次上传多个 PDF
  - 批量处理队列

- [ ] **导出功能**
  - 导出为 Excel
  - 导出为 CSV
  - 导出为 Word

- [ ] **模板管理**
  - 自定义提取字段
  - 保存提取模板
  - 行业专用模板

### 4.2 数据分析

- [ ] **统计报表**
  - 行业分布
  - 融资阶段统计
  - 时间趋势分析

- [ ] **数据可视化**
  - 关键词词云
  - 行业分布图
  - 融资阶段饼图

---

## 测试清单

### 功能测试

- [ ] PDF 上传功能
- [ ] 文件验证
- [ ] 图片转换
- [ ] VL 提取
- [ ] 数据验证
- [ ] 结果保存
- [ ] 查询接口
- [ ] 列表接口
- [ ] 前端上传
- [ ] 前端展示

### 性能测试

- [ ] 单个 PDF 处理时间 (< 60s)
- [ ] 并发处理能力 (5 个同时)
- [ ] 大文件处理 (50MB, 100 页)
- [ ] API 响应时间 (< 200ms)

### 安全测试

- [ ] 非法文件上传
- [ ] 超大文件
- [ ] 恶意 PDF
- [ ] API 权限
- [ ] 数据隔离

### 兼容性测试

- [ ] 不同版本 PDF
- [ ] 不同格式 BP(横版、竖版、双页)
- [ ] 不同浏览器
- [ ] 移动端

---

## 里程碑

| 里程碑 | 目标日期 | 关键交付 |
|-------|---------|---------|
| M1: MVP 后端完成 | 第 2 周 | API 可用,能成功提取 BP |
| M2: 前端完成 | 第 3 周 | 用户可通过 UI 上传和查看结果 |
| M3: 生产就绪 | 第 4 周 | 通过所有测试,可部署生产 |
| M4: 扩展功能 | 按需 | 批量处理、导出、统计等 |

---

## 依赖和风险

### 外部依赖

- [ ] Qwen VL API 可用性
- [ ] OSS 存储配额
- [ ] 数据库容量

### 技术风险

- [ ] PDF 转换失败(加密、损坏)
- [ ] VL 提取准确性不足
- [ ] 处理时间过长
- [ ] Token 成本超预算

### 缓解措施

- [ ] 提前测试各种 PDF 格式
- [ ] 准备 Prompt 调优方案
- [ ] 实施批量处理和队列
- [ ] 设置 Token 使用上限

---

**版本**: v1.0  
**最后更新**: 2025-11-18  
**预计总工时**: 4 周
