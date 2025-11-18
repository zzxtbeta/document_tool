# 设计：Paraformer 长音频异步任务管理增强

## 背景
DashScope `Transcription` 异步 API 需要先通过 `async_call` 提交任务，再调用 `GET /api/v1/tasks/{task_id}` (`Transcription.fetch`) 轮询结果。官方说明：
- `task_status` 可能经历 `PENDING`→`RUNNING`→`SUCCEEDED/FAILED`
- 队列/处理耗时与队列长度、音频时长相关，通常需数分钟
- 查询接口限流 20 QPS（按 API Key/账号计算）
- 任务结果仅保留 24 小时，超时后无法再查询或下载 DashScope 提供的 `transcription_url`

现有实现每次 `GET /transcribe-long/{task_id}` 都会立即触发一次 `fetch`，可能违反速率限制，也没有向客户端提示排队/TTL 信息。

## 目标
1. 明确地向客户端暴露排队提示、轮询策略、结果 TTL。
2. 在服务端增加 `last_fetch_at` 与节流逻辑，避免超过 DashScope 的 20 QPS 限制。
3. 对成功任务记录 `remote_result_expires_at`（默认 24 小时），即使远端 URL 过期，也能返回本地缓存路径。
4. 更新 Spec/Tasks/Docs，确保未来可推广到其他 DashScope 异步模型。

## 非目标
- 不实现批量查询/取消接口（需 DashScope 账号级 API，留作未来扩展）。
- 不改变 DashScope 默认 TTL；只在本地提示并缓存副本。

## 方案
### 轮询节流
- `ParaformerLongAudioService` 暴露 `poll_interval`（默认 10s，可通过 `LONG_AUDIO_POLL_INTERVAL` 配置）。
- `GET /transcribe-long/{task_id}` 在任务仍处于非终态时检查 `record.last_fetch_at`：
  - 若距离上次 fetch < `poll_interval`，则直接返回缓存状态，不再次请求 DashScope。
  - 否则调用 `Transcription.fetch`，并更新 `last_fetch_at`。

### 队列/加速提示
- Spec & 状态响应中添加描述：`PENDING` 受队列影响，需持续轮询；一旦运行即百倍速完成。
- 记录 `poll_interval_seconds` 供客户端 UI 显示建议轮询间隔。

### 结果 TTL 与缓存
- 新增环境变量 `LONG_AUDIO_RESULT_TTL`（默认 86400 秒）。
- 任务成功时记录 `remote_result_expires_at = now + TTL`，并在 `LongAudioStatusData` 中返回。
- 如果客户端在 24h 后查询，DashScope 可能返回 UNKNOWN。服务端应：
  - 维持任务状态为最后已知值；
  - 返回 `local_result_paths`/`local_audio_paths` 以便下载副本；
  - 在 metadata 中提示远端 URL 已过期（当当前时间 > `remote_result_expires_at`）。

### 数据模型扩展
- `LongAudioStatusData` 新增字段：`remote_result_ttl_seconds`, `remote_result_expires_at`。
- 状态响应 metadata 增加 `poll_interval_seconds`, `remote_result_expired`。

### OSS 接入与持久化
- 运行环境提供 OSS（或兼容 S3）的访问凭证，配置项包括 `OSS_ENDPOINT`、`OSS_BUCKET`、`OSS_ACCESS_KEY_ID/SECRET`。
- 客户端在我们的系统之外先把音频上传到 OSS，因此 `file_urls` 已经指向 OSS；服务端不再重复上传原始音频。
- 当任务首次 `SUCCEEDED` 时：
  1. 仍在本地暂存 DashScope JSON（方便拼接转写文本/重试）。
  2. 生成纪要 Markdown 后，通过统一的 `StorageClient` 上传至 OSS，得到 `minutes_markdown_url`，成功后可删除本地 Markdown。
  3. 仅 Markdown 需要回写 OSS；JSON、音频如需长期保留可由运维策略单独同步，避免重复存储。
- OSS 只存文件，所有可搜索字段（任务状态、URL、错误信息、生成时间）仍写入数据库，防止“把对象存储当数据库”。
- 上传失败要有重试与错误字段：
  - 第一次失败：记录 `minutes_error`，并保留本地 Markdown，供后台或人工重试。
  - 触发新的 `GET /transcribe-long/{task_id}` 且状态仍为 SUCCEEDED 时，如果 `minutes_markdown_url` 为空则再尝试上传；连失败次数可在日志里标记。

### 数据存储（PostgreSQL 单表）
- 通过 `.env` 中的 `DATABASE_URL`（示例：`postgresql://postgres:***@host:5432/db?sslmode=disable`）配置连接，统一由 `db/database.py` 基于 **psycopg3 (async)** 的客户端管理。
- 单表结构在原字段基础上新增：
  - `minutes_markdown_url TEXT`
  - `remote_result_urls TEXT[]`（可选，用于存 OSS 上的 JSON 副本）
  - `upload_attempts INTEGER`（可选，追踪 OSS 重试次数）
- 仍以 `task_id` 为唯一索引；常用查询列建立 B-Tree 索引。
- API 读写全部经过数据库：提交任务写入基础字段；轮询成功后追加 Markdown URL/纪要 JSON/错误信息。

### 会议纪要生成（与短音频复用）
保持短/长音频纪要模板与模型一致，复用 `AudioPipeline.generate_meeting_minutes` & `save_as_markdown` 逻辑，抽象为独立 `MeetingMinutesService`（或等价的可注入组件）。
- 当长音频任务在轮询中首次进入 `SUCCEEDED`：
  1. 在本地缓存 JSON 后拼接完整转写文本；
  2. 调用纪要服务生成结构化结果（title/content/quotes/keywords）；
  3. 将 Markdown 保存至 `uploads/audios/long/{task_id}/minutes.md`，并写入数据库字段 `meeting_minutes`（JSONB） + `minutes_markdown_path`；
  4. `LongAudioStatusResponse` 追加上述字段，若纪要仍在生成或失败，以 `null` + metadata 提示。
- 初期在 API 请求线程中同步执行，后续可扩展为后台任务。需留出重试/错误字段（如 `minutes_error`）以便 UI 告知失败原因。

### 错误/超时
- 若 `LONG_AUDIO_TIMEOUT` 触发（未来扩展），可将任务标记为 FAILED 并提示 `Processing timeout`。
- DashScope 返回 FAILED 时继续暴露 code/message，用于 UI 告警。

## 实现步骤
1. 更新 OpenSpec 文档（spec + tasks + 本设计）。
2. 扩展 `audio_models.py` 数据结构。
3. 在 `audio_api.py` 中：
   - 读取 `LONG_AUDIO_RESULT_TTL`，提交任务时写入记录。
   - 状态查询时检查节流条件；更新 `last_fetch_at`。
   - 任务成功时设置 `remote_result_expires_at` 并缓存音频/JSON（已有逻辑）。
   - 在响应 metadata 中返回 `poll_interval_seconds`, `remote_result_expires_at`, `remote_result_ttl_seconds`, `remote_result_expired`。
4. 运行端到端测试，确保短/长音频响应都包含新的元数据字段且兼容旧客户端。

## 风险与缓解
- **风险：** 客户端解析新增字段失败。→ 采用可选字段，不破坏现有字段；更新 API 文档。
- **风险：** DashScope 时间字符串格式变化。→ `remote_result_expires_at` 使用本地 `datetime.utcnow()` 推算，避免解析失败。
- **风险：** In-memory TaskStore 导致进程重启丢状态。→ 在文档中强调开发阶段限制，生产需持久化（待后续改进）。
