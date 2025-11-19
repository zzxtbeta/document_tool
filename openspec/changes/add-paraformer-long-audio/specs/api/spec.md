## ADDED Requirements
### Requirement: 长音频转写异步接口
系统 SHALL 提供新的 `POST /api/v1/audio/transcribe-long` 端点, 使用 DashScope `paraformer-v2` 模型处理远程音频 URL, 并返回异步任务信息。

#### Scenario: 提交长音频任务
- **GIVEN** 客户端提供 1-5 个可访问的音频 `file_urls` 和可选 `language_hints`
- **WHEN** 请求 `POST /api/v1/audio/transcribe-long`
- **THEN** API 应验证 URL, 生成 `task_id`, 调用 `Transcription.async_call`
- **AND** 返回 202 状态, 包含 `task_status` (PENDING|RUNNING)

#### Scenario: 轮询任务状态
- **GIVEN** 已获得 `task_id`
- **WHEN** 客户端请求 `GET /api/v1/audio/transcribe-long/{task_id}`
- **THEN** 后端 SHALL 调用 `Transcription.fetch` 或读取缓存, 返回最新 `task_status`
- **AND** 当状态为 SUCCEEDED 时, 返回所有 `results` 包含 `transcription_url`

#### Scenario: 排队与加速处理说明
- **GIVEN** 任务提交后处于 DashScope 队列
- **WHEN** `output.task_status` 为 `PENDING`
- **THEN** 系统 SHALL 告知客户端排队时间取决于队列长度与音频时长, 可能需要数分钟
- **AND** 一旦转写开始, 语音识别以百倍速完成, 客户端应继续轮询直到状态更新

#### Scenario: 任务失败处理
- **GIVEN** DashScope 子任务失败 (如下载错误)
- **WHEN** 状态为 FAILED 或部分失败
- **THEN** API 应返回对应的失败详情 (code, message, subtask_status)
- **AND** 记录日志以便排查

#### Scenario: 结果持久化
- **GIVEN** 任务状态 SUCCEEDED
- **WHEN** 系统获取 `transcription_url`
- **THEN** 应先将 JSON 结果缓存到 `uploads/audios/long/{task_id}/` 以便拼接全文
- **AND** 生成会议纪要 Markdown 后需上传到 OSS，返回 `minutes_markdown_url`
- **AND** 在状态查询中同时返回本地调试路径与 OSS URL，数据库需记录 URL 以便后续查询

#### Scenario: OSS 私有 Bucket 与签名 URL
- **GIVEN** OSS bucket 为私有访问、对象路径遵循 `prod/gold/userUploads/{projectId}/audio/{taskId}/`
- **WHEN** 系统上传转写 JSON 与纪要 Markdown
- **THEN** `long_audio_tasks` SHALL 记录 `minutes_markdown_object_key`、`remote_result_object_keys` 以及 `minutes_markdown_signed_url`
- **AND** `GET /api/v1/audio/transcribe-long/{task_id}` 每次请求 SHALL 返回 10 分钟有效的签名下载 URL（若签名失败，以 `minutes_error` 说明）
- **AND** 任务元数据 SHALL 持久化 `user_id`、`project_id`、`source_filename`，以便遵循命名规范和前端展示

#### Scenario: 结果有效期与缓存策略
- **GIVEN** DashScope 官方仅保证异步任务结果保留 24 小时
- **WHEN** 客户端尝试使用既有 `transcription_url`
- **THEN** 系统 SHALL 明确提示 URL 超时将失效, 通过本地缓存提供副本并暴露 `local_result_paths`
- **AND** 过期后再次调用 `Transcription.fetch` 可能返回 UNKNOWN, 系统需返回 404/过期提示
- **AND** 若 OSS 上传 Markdown 失败，系统应在 `minutes_error` 中记录并允许后续查询触发重试

#### Scenario: 配置与超时
- **GIVEN** 管理员设置 `LONG_AUDIO_POLL_INTERVAL` 与 `LONG_AUDIO_TIMEOUT`
- **WHEN** 系统轮询任务
- **THEN** 应遵循配置的间隔与超时, 超时后将任务标记为 FAILED 并提示 "Processing timeout"

#### Scenario: 轮询速率与停止条件
- **GIVEN** DashScope 对 `GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}` 的查询限制为 20 QPS
- **WHEN** 后端调用 `Transcription.fetch`
- **THEN** 系统 SHALL 采用节流/退避策略 (不少于配置的 `LONG_AUDIO_POLL_INTERVAL`), 确保不会超过官方限额
- **AND** 一旦任务进入 SUCCEEDED 或 FAILED, 必须停止进一步轮询, 仅返回缓存结果

#### Scenario: 任务持久化 (PostgreSQL 单表)
- **GIVEN** 系统提供 `DATABASE_URL` 环境变量并连接 PostgreSQL
- **WHEN** 提交或更新长音频任务
- **THEN** 系统 SHALL 在 `long_audio_tasks` 单表中持久化任务元数据, 至少包含 `task_id`, `dashscope_task_id`, `task_status`, `model`, `file_urls`, `language_hints`, `results`, `local_result_paths`, `local_audio_paths`, `remote_result_ttl_seconds`, `remote_result_expires_at`, `last_fetch_at`, `submitted_at`, `updated_at`
- **AND** 查询接口 SHALL 以该表为权威数据源, 以保证服务重启或多实例情况下的状态一致性

#### Scenario: 长音频会议纪要生成（共享逻辑）
- **GIVEN** 系统已为短音频实现会议纪要生成 (`AudioPipeline.generate_meeting_minutes`)
- **WHEN** 某长音频任务状态变为 `SUCCEEDED`
- **THEN** `GET /api/v1/audio/transcribe-long/{task_id}` SHALL 在缓存 DashScope 结果后, 使用相同的纪要生成逻辑（相同 prompt/模型）生成结构化纪要
- **AND** Markdown 结果必须上传至 OSS，API 响应同时返回 `minutes_markdown_path`（本地备份）与 `minutes_markdown_url`（OSS 访问地址）；若纪要仍在生成/失败, 字段可为 `null` 并在 metadata 中提示

### Requirement: DashScope 异步任务管理代理
系统 SHALL 暴露 DashScope 官方任务管理接口的受控代理, 便于用户查询/列表/取消任务而无需暴露 API Key。

#### Scenario: 查询单个 DashScope 任务
- **GIVEN** 客户端提供 `dashscope_task_id`
- **WHEN** 请求 `GET /api/v1/audio/dashscope/tasks/{dashscope_task_id}`
- **THEN** 后端 SHALL 调用 `GET https://dashscope.aliyuncs.com/api/v1/tasks/{dashscope_task_id}` 并返回 `request_id`、`output`、`usage`
- **AND** 若 DashScope 返回 4xx/5xx, 系统应将 code/message 透传给客户端

#### Scenario: 批量查询任务状态
- **WHEN** 客户端请求 `GET /api/v1/audio/dashscope/tasks` 并传入官方支持的查询参数 (start_time/end_time/page_no/page_size/status/model_name)
- **THEN** 后端 SHALL 代表客户端调用 DashScope 批量接口并返回 `total/data/page_*`
- **AND** 若未指定时间范围, 系统默认查询最近 24h 任务
- **AND** 若 DashScope 返回 404（表示暂无数据），API MUST 以空列表 `{total:0,data:[]}` 响应而非将 404 透传, 以保证前端轮询稳定

#### Scenario: 取消排队中的任务
- **GIVEN** 任务仍处于 `PENDING`
- **WHEN** 客户端请求 `POST /api/v1/audio/dashscope/tasks/{dashscope_task_id}/cancel`
- **THEN** 后端 SHALL 先查询本地数据库检查任务状态
- **AND** 若任务状态不是 PENDING, 应立即返回 400 错误并提示当前状态，避免调用 DashScope API
- **AND** 若任务状态为 PENDING, 则调用 DashScope 取消接口, 返回 `request_id`
- **AND** 若 DashScope 仍返回非 PENDING 错误，应返回友好的中文错误信息 `UnsupportedOperation`

#### Scenario: 模块解耦与代码重构
- **GIVEN** 系统同时支持短音频和长音频转写
- **WHEN** 开发者需要独立部署或维护短/长音频模块
- **THEN** 系统 SHALL 将短音频和长音频代码完全分离到独立模块（`api/audio/short/`, `api/audio/long/`）
- **AND** Pipeline 文件 SHALL 明确命名以区分功能（`short_audio_pipeline.py`, `long_audio_pipeline.py`）
- **AND** 共享的数据模型 SHALL 放在 `api/audio/shared_models.py` 中
- **AND** 旧的耦合代码文件（`audio_api.py`, `audio_models.py`）SHALL 被删除

#### Scenario: 错误字段类型兼容处理
- **GIVEN** 数据库中 error 字段为 JSONB 类型，可能存储 dict 或 string
- **WHEN** 构建 API 响应时读取 error 字段
- **THEN** 系统 SHALL 统一将 dict 类型序列化为 JSON 字符串
- **AND** Pydantic 模型定义 SHALL 使用 `Optional[str]` 类型
- **AND** `_build_status_data` 函数 SHALL 处理两种输入类型（dict/str）的兼容转换

#### Scenario: 防止重复取消请求
- **GIVEN** 用户可能在短时间内多次点击取消按钮
- **WHEN** 收到取消任务请求
- **THEN** 后端 SHALL 先从本地数据库查询任务当前状态
- **AND** 只有当状态为 PENDING 时才调用 DashScope 取消 API
- **AND** 若状态不是 PENDING, SHALL 立即返回包含当前状态的友好错误信息
- **AND** 前端 SHALL 在取消按钮上添加 loading 状态，防止重复点击
- **AND** 前端 SHALL 只在任务状态为 PENDING 时显示取消按钮
