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
- [x] 2.3 新增可配置环境变量（模型名称、轮询间隔、超时、存储目录），落地在 `.env(.example)`、`audio_api.py`、`paraformer_long_audio.py`
- [x] 2.4 编写结果落盘逻辑，将 DashScope 转写 JSON 保存至 `uploads/audios/long/{timestamp}_long_{dashscope_task_id}/`，并同时缓存源音频
- [x] 2.5 统一长/短音频本地存储命名与目录结构（短音频落盘 `uploads/audios/short/{timestamp}_short_{task_id}`，并缓存结果 JSON / Markdown 路径）
- [ ] 2.6 引入 PostgreSQL 单表持久化（`long_audio_tasks`）
  - [ ] 2.6.1 通过 `.env` (`DATABASE_URL`) + `db/database.py` 建立 psycopg3 async 连接工厂
  - [ ] 2.6.2 定义 `long_audio_tasks` 表结构（task_id/dashscope_task_id/status/model/file_urls/jsonb results/TTL timestamps）并创建索引
  - [ ] 2.6.3 提交/轮询 API 改为读写数据库，淘汰内存 `TaskStore`，保持字段兼容
- [ ] 2.7 复用会议纪要生成逻辑（短/长音频共用）
  - [ ] 2.7.1 抽象 `MeetingMinutesService`（或等价拆分）以便独立生成 Markdown/JSON 纪要
  - [ ] 2.7.2 长音频任务 SUCCEEDED 时调用纪要服务，保存 Markdown + 结构化结果到数据库字段
  - [ ] 2.7.3 `LongAudioStatusResponse` 返回 `meeting_minutes`、`minutes_markdown_path`、`minutes_error` 等可选字段

## 3. 错误处理与限制
- [x] 3.1 将 DashScope 错误码映射为相应的 HTTP 响应（如 InvalidFile、DownloadFailed）（submission/fetch 失败会返回 4xx/5xx 并记录日志）
- [x] 3.2 实施单次请求限制（限制 `file_urls` 为 1-100，未来如需更严格阈值可在配置中收敛）
- [ ] 3.3 为轮询实现超时与重试策略（当前采用 DashScope 即时 fetch + 环境变量控制的轮询间隔/超时，仍待补充 retry/backoff 测试）

## 4. 测试
- [ ] 4.1 请求校验与任务存储的单元测试
- [ ] 4.2 模拟 DashScope 成功/运行中/失败状态的测试
- [ ] 4.3 提交 + 轮询闭环的集成测试

## 5. 文档与可观测性
- [ ] 5.1 在 Swagger/OpenAPI 中补充新端点及模型
- [ ] 5.2 在 README/运维指南中记录相关环境变量与使用方法
- [ ] 5.3 增加日志/指标，覆盖提交量、成功/失败率、平均完成时间

## 6. 异步任务管理增强（DashScope 通用接口）
- [ ] 6.1 编写/更新设计文档，描述 DashScope 异步任务生命周期、轮询策略、TTL 与本地缓存策略
- [ ] 6.2 扩充 Spec 文档，对 PENDING 队列提示、24 小时有效期、20 QPS 限制及停止条件进行规范描述
- [ ] 6.3 在代码层实现任务轮询节流（`LONG_AUDIO_POLL_INTERVAL` 控制）与 `last_fetch_at` 记录，避免超过官方 QPS
- [ ] 6.4 在状态结果中返回 `expires_at`、`remote_result_ttl` 等提示，并在超时后返回 404/过期说明
- [ ] 6.5 加强本地缓存/下载提示，为结果 JSON、音频副本和存储目录提供清晰的路径信息

## 7. 生产环境优化 (Roadmap)
--- [x] 7.1 将长音频任务存储迁移到 PostgreSQL 单表（`long_audio_tasks`），支持多实例/重启恢复
- [ ] 7.2 长音频纪要生成为后台任务/重试策略（Roadmap）
- [ ] 7.2 为长音频任务提供消息通知（Webhook / 邮件），便于大文件完成后提醒用户
- [ ] 7.3 在 README/运维文档中补充生产部署建议（OSS 临时 URL、TTL 告警、任务清理策略）
- [ ] 7.4 评估引入后台 worker 统一管理轮询，避免 API 实例阻塞，支持水平扩展
