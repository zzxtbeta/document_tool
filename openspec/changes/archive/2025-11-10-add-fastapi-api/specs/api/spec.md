# API 规范

## ADDED Requirements

### Requirement: RESTful API 接口
系统 SHALL 提供基于 FastAPI 的 RESTful API 接口,支持知识图谱提取服务的远程调用。

#### Scenario: API 服务启动
- **GIVEN** API 服务已配置环境变量 (DASHSCOPE_API_KEY 等)
- **WHEN** 运行 `uvicorn api:app --host 0.0.0.0 --port 8000`
- **THEN** API 服务应在 8000 端口启动
- **AND** Swagger 文档应可访问 `http://localhost:8000/docs`

#### Scenario: 服务健康检查
- **WHEN** 客户端发送 `GET /api/v1/health`
- **THEN** 应返回 200 状态码
- **AND** 返回 JSON 包含 `{"status": "healthy", "version": "1.2.0", "llm_available": true}`

---

### Requirement: 文件上传与知识图谱提取
系统 SHALL 支持上传 JSON 文档并提取知识图谱,返回双版本输出。

#### Scenario: 小文件同步处理
- **GIVEN** 上传的 JSON 文件小于 10MB 且页数小于 50
- **WHEN** 客户端发送 `POST /api/v1/extract` 并上传文件
- **THEN** API 应同步处理并返回 200 状态码
- **AND** 响应 JSON 包含 `raw_graph` 和 `aligned_graph` 字段
- **AND** 处理时间应在 30 秒内完成

#### Scenario: 大文件异步处理
- **GIVEN** 上传的 JSON 文件大于 10MB 或页数大于 50
- **WHEN** 客户端发送 `POST /api/v1/extract` 并上传文件
- **THEN** API 应返回 202 状态码 (Accepted)
- **AND** 响应包含 `task_id` 字段
- **AND** 后台应异步处理该任务

#### Scenario: 查询异步任务状态
- **GIVEN** 已提交异步任务,获得 task_id
- **WHEN** 客户端发送 `GET /api/v1/tasks/{task_id}`
- **THEN** 应返回任务状态 (pending, processing, completed, failed)
- **AND** 如果完成,应包含结果数据或下载链接

#### Scenario: 可配置 Pipeline 参数
- **GIVEN** 客户端需要自定义处理参数
- **WHEN** 在请求体中传入 `{"chunk_size": 1024, "max_workers": 8}`
- **THEN** Pipeline 应使用这些参数处理文档
- **AND** 如果未指定,应使用默认值 (chunk_size=512, max_workers=3)

---

### Requirement: 文件格式验证
系统 MUST 验证上传文件的格式和大小,确保安全性。

#### Scenario: 有效 JSON 文件
- **GIVEN** 客户端上传的文件是有效的 JSON 格式
- **AND** 包含必需字段 `type` 和 `page_idx`
- **WHEN** API 进行验证
- **THEN** 验证应通过,继续处理

#### Scenario: 无效文件格式
- **GIVEN** 客户端上传的文件不是 JSON 或格式错误
- **WHEN** API 进行验证
- **THEN** 应返回 400 状态码 (Bad Request)
- **AND** 错误消息应说明 "无效的 JSON 格式"

#### Scenario: 文件过大
- **GIVEN** 客户端上传的文件超过 50MB
- **WHEN** API 检查文件大小
- **THEN** 应返回 413 状态码 (Payload Too Large)
- **AND** 错误消息应说明 "文件大小超过限制 (50MB)"

#### Scenario: 缺失必需字段
- **GIVEN** JSON 文件缺少 `type` 或 `page_idx` 字段
- **WHEN** API 进行内容验证
- **THEN** 应返回 422 状态码 (Unprocessable Entity)
- **AND** 错误消息应列出缺失的字段

---

### Requirement: 标准化 API 响应
系统 SHALL 使用统一的响应格式,包含成功状态、数据和元数据。

#### Scenario: 成功响应
- **GIVEN** API 请求处理成功
- **WHEN** 返回响应
- **THEN** 响应结构应包含:
  ```json
  {
    "success": true,
    "data": { ... },
    "error": null,
    "metadata": {
      "task_id": "uuid",
      "timestamp": "ISO8601",
      "processing_time": 3.14
    }
  }
  ```

#### Scenario: 错误响应
- **GIVEN** API 请求处理失败 (验证失败、处理异常等)
- **WHEN** 返回响应
- **THEN** 响应结构应包含:
  ```json
  {
    "success": false,
    "data": null,
    "error": {
      "code": "ERROR_CODE",
      "message": "人类可读的错误描述",
      "details": { ... }
    },
    "metadata": { ... }
  }
  ```

---

### Requirement: 错误处理与日志
系统 MUST 提供完善的错误处理和日志记录机制。

#### Scenario: LLM API 调用失败
- **GIVEN** LLM API 不可用或返回错误
- **WHEN** Pipeline 尝试提取实体
- **THEN** 应捕获异常并返回 503 状态码 (Service Unavailable)
- **AND** 错误消息应说明 "LLM 服务暂时不可用,请稍后重试"
- **AND** 应记录详细错误日志 (包括 API 响应)

#### Scenario: 请求日志记录
- **GIVEN** API 收到任何请求
- **WHEN** 处理请求
- **THEN** 应记录日志包含:
  - 请求 ID (UUID)
  - 请求方法和路径
  - 客户端 IP
  - 处理耗时
  - 状态码
- **AND** 日志格式应为: `2025-11-10 12:00:00 - api - INFO - [req_id] POST /api/v1/extract - 200 - 3.14s`

#### Scenario: 超时处理
- **GIVEN** 异步任务处理时间超过配置的超时时间 (默认 600 秒)
- **WHEN** 达到超时时间
- **THEN** 任务应被标记为 failed
- **AND** 错误信息应说明 "处理超时"
- **AND** 应释放相关资源

---

### Requirement: 文件存储与清理
系统 SHALL 管理上传和输出文件的存储,并自动清理过期文件。

#### Scenario: 上传文件存储
- **GIVEN** 客户端上传文件
- **WHEN** API 接收文件
- **THEN** 文件应保存到 `uploads/{task_id}/input.json`
- **AND** 应设置文件权限为只读

#### Scenario: 输出文件存储
- **GIVEN** Pipeline 处理完成
- **WHEN** 保存结果
- **THEN** 双版本文件应保存到:
  - `outputs/{task_id}/result_raw.json`
  - `outputs/{task_id}/result_aligned.json`

#### Scenario: 过期文件清理
- **GIVEN** 输出文件创建时间超过 24 小时
- **WHEN** 定时清理任务运行
- **THEN** 应删除该文件及其目录
- **AND** 应记录清理日志

---

### Requirement: 环境变量配置
系统 MUST 支持通过环境变量配置 API 和 Pipeline 参数。

#### Scenario: API 服务配置
- **GIVEN** 设置环境变量 `API_HOST=127.0.0.1`, `API_PORT=9000`
- **WHEN** 启动 API 服务
- **THEN** 应监听 127.0.0.1:9000

#### Scenario: Pipeline 默认参数配置
- **GIVEN** 设置环境变量 `DEFAULT_CHUNK_SIZE=1024`, `DEFAULT_MAX_WORKERS=8`
- **WHEN** 请求未指定参数
- **THEN** Pipeline 应使用这些默认值

#### Scenario: 文件存储路径配置
- **GIVEN** 设置环境变量 `UPLOAD_DIR=/data/uploads`, `OUTPUT_DIR=/data/outputs`
- **WHEN** API 处理文件
- **THEN** 应使用配置的路径存储文件

---

### Requirement: API 文档
系统 SHALL 提供交互式 API 文档,便于开发者集成。

#### Scenario: Swagger 文档访问
- **GIVEN** API 服务运行中
- **WHEN** 访问 `http://localhost:8000/docs`
- **THEN** 应显示 Swagger UI 文档
- **AND** 所有端点应可见并可测试

#### Scenario: OpenAPI Schema 导出
- **GIVEN** API 服务运行中
- **WHEN** 访问 `http://localhost:8000/openapi.json`
- **THEN** 应返回完整的 OpenAPI 3.0 JSON schema

---

### Requirement: CORS 支持
系统 SHALL 支持跨域资源共享 (CORS),允许前端应用调用。

#### Scenario: 允许跨域请求
- **GIVEN** 前端应用在不同域名运行
- **WHEN** 发送跨域请求到 API
- **THEN** 响应应包含 CORS 头:
  - `Access-Control-Allow-Origin: *` (或配置的域名)
  - `Access-Control-Allow-Methods: GET, POST`
  - `Access-Control-Allow-Headers: Content-Type`
