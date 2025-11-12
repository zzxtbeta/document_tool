# 实现任务清单

## 1. 项目结构与依赖
- [x] 1.1 创建 `api.py` 主文件
- [x] 1.2 创建 `api_models.py` (Pydantic models)
- [x] 1.3 更新 `requirements.txt` 或 `pyproject.toml`
- [x] 1.4 创建 `.env.example` 环境变量模板
- [x] 1.5 创建 `uploads/` 和 `outputs/` 目录

## 2. API 数据模型定义
- [x] 2.1 定义 `ExtractRequest` 请求模型
- [x] 2.2 定义 `ExtractResponse` 响应模型
- [x] 2.3 定义 `TaskStatus` 枚举 (pending, processing, completed, failed)
- [x] 2.4 定义 `TaskResponse` 任务状态模型
- [x] 2.5 定义 `HealthResponse` 健康检查模型
- [x] 2.6 定义 `ErrorResponse` 错误响应模型

## 3. 核心 API 端点实现
- [x] 3.1 实现 `POST /api/v1/extract` - 知识图谱提取
  - [x] 3.1.1 文件上传验证 (JSON 格式, 最大 50MB)
  - [x] 3.1.2 保存上传文件到临时目录
  - [x] 3.1.3 调用 Pipeline 处理
  - [x] 3.1.4 生成双版本输出文件
  - [x] 3.1.5 返回结果 JSON 或下载链接
- [x] 3.2 实现 `GET /api/v1/health` - 健康检查
  - [x] 3.2.1 返回服务状态
  - [x] 3.2.2 返回 Pipeline 版本信息
  - [x] 3.2.3 检查 LLM API 连通性
- [x] 3.3 实现 `GET /api/v1/tasks/{task_id}` - 任务状态查询
  - [x] 3.3.1 查询任务处理状态
  - [x] 3.3.2 返回进度信息
  - [x] 3.3.3 返回结果文件路径

## 4. 异步处理与任务管理
- [x] 4.1 实现后台任务队列 (使用 FastAPI BackgroundTasks)
- [x] 4.2 实现任务状态跟踪 (内存存储或 Redis)
- [x] 4.3 添加任务超时机制 (默认 10 分钟)
- [x] 4.4 实现任务结果清理策略 (保留 24 小时)

## 5. 错误处理与日志
- [x] 5.1 添加全局异常处理器
- [x] 5.2 实现请求日志记录 (请求 ID, 耗时, 状态码)
- [x] 5.3 实现错误响应标准化
- [ ] 5.4 添加速率限制 (可选,防止滥用)

## 6. 配置与环境变量
- [x] 6.1 支持环境变量配置
  - [x] API_HOST (默认 0.0.0.0)
  - [x] API_PORT (默认 8000)
  - [x] UPLOAD_DIR (默认 ./uploads)
  - [x] OUTPUT_DIR (默认 ./outputs)
  - [x] MAX_UPLOAD_SIZE (默认 50MB)
  - [x] TASK_TIMEOUT (默认 600 秒)
- [x] 6.2 支持 Pipeline 参数配置
  - [x] DEFAULT_CHUNK_SIZE (默认 512)
  - [x] DEFAULT_MAX_WORKERS (默认 3)
  - [x] DEFAULT_TEMPERATURE (默认 0.3)
  - [x] DEFAULT_SIMILARITY (默认 0.85)

## 7. 文档与示例
- [x] 7.1 添加 API 文档 (FastAPI 自动生成 Swagger)
- [x] 7.2 更新 `README_PIPELINE.md` 添加 API 使用说明
- [x] 7.3 创建 `examples/api_usage.py` 调用示例
- [x] 7.4 创建 `examples/curl_examples.sh` cURL 示例

## 8. 测试
- [x] 8.1 单元测试 - API 端点测试 (快速验证测试)
- [ ] 8.2 集成测试 - 完整上传提取流程
- [ ] 8.3 错误场景测试 (无效文件, 超大文件, 超时等)
- [ ] 8.4 性能测试 (并发请求处理能力)

## 9. 部署准备
- [ ] 9.1 创建 `Dockerfile`
- [ ] 9.2 创建 `docker-compose.yml`
- [x] 9.3 添加启动脚本 `run_api.sh` / `run_api.bat`
- [ ] 9.4 添加部署文档 `docs/API_DEPLOYMENT.md`
