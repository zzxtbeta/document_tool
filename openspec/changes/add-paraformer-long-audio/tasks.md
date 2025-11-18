# 任务清单：Paraformer 长音频转写接口

## 1. 规范与规划
- [x] 1.1 学习 DashScope `paraformer-v2` 官方文档，确认异步调用协议（已研读官方 async call/fetch 规范，并梳理可用字段）
- [x] 1.2 定义 `/api/v1/audio/transcribe-long` 的 API 契约（请求、响应、错误）（`openspec/changes/.../specs/api/spec.md` 已更新）
- [x] 1.3 与现有任务轮询机制对齐，或设计独立状态查询端点（最终采用独立 `GET /api/v1/audio/transcribe-long/{task_id}` 并沿用 TaskStore 结构）

## 2. 后端实现
- [x] 2.1 创建长音频转写的 FastAPI 路由
  - [x] 2.1.1 实现 `POST /api/v1/audio/transcribe-long`，接受包含 `file_urls`、`language_hints` 的 JSON
  - [x] 2.1.2 校验输入（URL 协议、数量上限、重复检测）
  - [x] 2.1.3 通过 `dashscope.audio.asr.Transcription.async_call` 提交异步任务
  - [x] 2.1.4 持久化任务元数据（task_id、状态、提交的文件、本地目录）
- [x] 2.2 实现轮询/状态查询端点
  - [x] 2.2.1 `GET /api/v1/audio/transcribe-long/{task_id}` 可从 DashScope 或缓存拉取最新状态
  - [x] 2.2.2 缓存成功任务的结果，返回转写下载 URL 及元数据（含本地 JSON / 音频路径）
- [x] 2.8 模块解耦与代码重构
  - [x] 2.8.1 将短音频和长音频代码完全解耦到独立模块（`api/audio/short/`, `api/audio/long/`）
  - [x] 2.8.2 重命名 pipeline 文件以明确区分（`short_audio_pipeline.py`, `long_audio_pipeline.py`）
  - [x] 2.8.3 删除旧的耦合代码文件（`audio_api.py`, `audio_models.py`）
  - [x] 2.8.4 修复 error 字段类型不匹配问题（JSONB dict → str 序列化）
  - [x] 2.8.5 在 `_build_status_data` 中添加 error 字段类型兼容处理
  - [x] 2.8.6 添加 `_get_long_audio_task_by_dashscope_id` 函数用于取消任务前的状态检查
  - [x] 2.8.7 优化取消任务逻辑：先检查本地状态再调用 DashScope API，避免无效请求
- [x] 2.3 新增可配置环境变量（模型名称、轮询间隔、超时、存储目录），落地在 `.env(.example)`、`audio_api.py`、`paraformer_long_audio.py`
- [x] 2.4 编写结果落盘逻辑，将 DashScope 转写 JSON 保存至 `uploads/audios/long/{timestamp}_long_{dashscope_task_id}/`，并同时缓存源音频
- [x] 2.5 统一长/短音频本地存储命名与目录结构（短音频落盘 `uploads/audios/short/{timestamp}_short_{task_id}`，并缓存结果 JSON / Markdown 路径）
- [x] 2.6 引入 PostgreSQL 单表持久化（`long_audio_tasks`）
  - [x] 2.6.1 通过 `.env` (`DATABASE_URL`) + `db/database.py` 建立 psycopg3 async 连接工厂（current backend 运行中使用 async pool）
  - [x] 2.6.2 定义 `long_audio_tasks` 表结构（含 user_id/project_id/source_filename/oss_object_prefix 等新增列）并创建索引
  - [x] 2.6.3 提交/轮询 API 改为读写数据库，淘汰内存 `TaskStore`，保持字段兼容（task 元数据、TTL、last_fetch_at 均由数据库驱动）
- [x] 2.7 复用会议纪要生成逻辑（短/长音频共用）
  - [x] 2.7.1 抽象 `MeetingMinutesService`（或等价拆分）以便独立生成 Markdown/JSON 纪要
  - [x] 2.7.2 长音频任务 SUCCEEDED 时调用纪要服务，保存 Markdown + 结构化结果到数据库字段
  - [x] 2.7.3 `LongAudioStatusResponse` 返回 `meeting_minutes`、`minutes_markdown_path`、`minutes_markdown_url`、`minutes_error`、`minutes_markdown_signed_url` 等可选字段
  - [x] 2.7.4 引入 `OSSStorageClient`，按 `prefix/bronze/userUploads/{projectId}/audio/{taskId}/` 上传纪要与转写 JSON，记录 OSS URL、object key，并生成 10 分钟有效的签名下载链接

## 3. 错误处理与限制
- [x] 3.1 将 DashScope 错误码映射为相应的 HTTP 响应（如 InvalidFile、DownloadFailed）（submission/fetch 失败会返回 4xx/5xx 并记录日志）
- [x] 3.2 实施单次请求限制（限制 `file_urls` 为 1-100，未来如需更严格阈值可在配置中收敛）
- [x] 3.3 轮询错误处理优化
  - [x] 3.3.1 前端轮询时静默处理网络错误，避免干扰用户体验
  - [x] 3.3.2 后端 error 字段统一序列化为 JSON 字符串，确保 Pydantic 验证通过
  - [x] 3.3.3 取消任务前先检查本地状态，避免重复 API 调用和速率限制问题
  - [x] 3.3.4 TaskHistoryPanel 和 TaskDetailDrawer 中的取消按钮都添加完整错误处理
- [ ] 3.4 为轮询实现超时与重试策略（当前采用 DashScope 即时 fetch + 环境变量控制的轮询间隔/超时，仍待补充 retry/backoff 测试）

## 4. 测试
- [ ] 4.1 请求校验与任务存储的单元测试
- [ ] 4.2 模拟 DashScope 成功/运行中/失败状态的测试
- [ ] 4.3 提交 + 轮询闭环的集成测试

## 5. 文档与可观测性
- [ ] 5.1 在 Swagger/OpenAPI 中补充新端点及模型
- [ ] 5.2 在 README/运维指南中记录相关环境变量与使用方法
- [ ] 5.3 增加日志/指标，覆盖提交量、成功/失败率、平均完成时间

## 6. 前端实现与优化
- [x] 6.1 OSS 下载链接集成
  - [x] 6.1.1 在 TaskDetailDrawer 中添加 OSS JSON 下载链接
  - [x] 6.1.2 在 TaskDetailDrawer 中添加会议纪要 Markdown 临时签名 URL 下载
  - [x] 6.1.3 在 store 中正确映射 `remoteResultUrls` 和 `minutesMarkdownSignedUrl`
- [x] 6.2 自动轮询优化
  - [x] 6.2.1 实现 5 秒间隔的自动轮询（仅针对 PENDING/RUNNING 任务）
  - [x] 6.2.2 轮询时静默处理错误，避免显示全局错误提示
  - [x] 6.2.3 组件卸载时清理轮询定时器
- [x] 6.3 取消任务 UI 改进
  - [x] 6.3.1 只在 PENDING 状态显示取消按钮（符合 DashScope API 限制）
  - [x] 6.3.2 添加取消按钮 loading 状态，防止重复点击
  - [x] 6.3.3 显示取消失败的详细错误信息（包含当前状态）
  - [x] 6.3.4 TaskHistoryPanel 中的取消按钮添加错误处理
- [x] 6.4 类型定义完善
  - [x] 6.4.1 在 `LongAudioStatusResponse.data` 中添加 `error` 字段
  - [x] 6.4.2 确保所有状态映射正确（PENDING/RUNNING/SUCCEEDED/FAILED/CANCELED/UNKNOWN）

## 7. 异步任务管理增强（DashScope 通用接口）
- [ ] 6.1 编写/更新设计文档，描述 DashScope 异步任务生命周期、轮询策略、TTL 与本地缓存策略
- [ ] 6.2 扩充 Spec 文档，对 PENDING 队列提示、24 小时有效期、20 QPS 限制及停止条件进行规范描述
- [ ] 6.3 在代码层实现任务轮询节流（`LONG_AUDIO_POLL_INTERVAL` 控制）与 `last_fetch_at` 记录，避免超过官方 QPS
- [ ] 6.4 在状态结果中返回 `expires_at`、`remote_result_ttl` 等提示，并在超时后返回 404/过期说明
- [ ] 6.5 加强本地缓存/下载提示，为结果 JSON、音频副本和存储目录提供清晰的路径信息

## 8. 生产环境优化 (Roadmap)
- [x] 8.1 将长音频任务存储迁移到 PostgreSQL 单表（`long_audio_tasks`），支持多实例/重启恢复
- [ ] 8.2 长音频纪要生成为后台任务/重试策略（Roadmap）
- [ ] 8.3 为长音频任务提供消息通知（Webhook / 邮件），便于大文件完成后提醒用户
- [ ] 8.4 在 README/运维文档中补充生产部署建议（OSS 临时 URL、TTL 告警、任务清理策略）
- [ ] 8.5 评估引入后台 worker 统一管理轮询，避免 API 实例阻塞，支持水平扩展
