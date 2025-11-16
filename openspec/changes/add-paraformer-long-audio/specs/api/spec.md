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
- **THEN** 应将 JSON 结果缓存到 `uploads/audios/long/{task_id}/`
- **AND** 在状态查询中返回缓存路径 (如 `local_result_path`)

#### Scenario: 结果有效期与缓存策略
- **GIVEN** DashScope 官方仅保证异步任务结果保留 24 小时
- **WHEN** 客户端尝试使用既有 `transcription_url`
- **THEN** 系统 SHALL 明确提示 URL 超时将失效, 通过本地缓存提供副本并暴露 `local_result_paths`
- **AND** 过期后再次调用 `Transcription.fetch` 可能返回 UNKNOWN, 系统需返回 404/过期提示

#### Scenario: 配置与超时
- **GIVEN** 管理员设置 `LONG_AUDIO_POLL_INTERVAL` 与 `LONG_AUDIO_TIMEOUT`
- **WHEN** 系统轮询任务
- **THEN** 应遵循配置的间隔与超时, 超时后将任务标记为 FAILED 并提示 "Processing timeout"

#### Scenario: 轮询速率与停止条件
- **GIVEN** DashScope 对 `GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}` 的查询限制为 20 QPS
- **WHEN** 后端调用 `Transcription.fetch`
- **THEN** 系统 SHALL 采用节流/退避策略 (不少于配置的 `LONG_AUDIO_POLL_INTERVAL`), 确保不会超过官方限额
- **AND** 一旦任务进入 SUCCEEDED 或 FAILED, 必须停止进一步轮询, 仅返回缓存结果

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

#### Scenario: 取消排队中的任务
- **GIVEN** 任务仍处于 `PENDING`
- **WHEN** 客户端请求 `POST /api/v1/audio/dashscope/tasks/{dashscope_task_id}/cancel`
- **THEN** 后端 SHALL 调用 DashScope 取消接口, 返回 `request_id`
- **AND** 若任务非 PENDING, 应返回官方错误信息 `UnsupportedOperation`
