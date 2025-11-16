# 变更：Paraformer 长音频转写接口

## 为什么
- `qwen3-asr-flash` 只能处理约 3 分钟 / 10MB 的音频，现有 `/api/v1/audio/transcribe` 无法覆盖长时间会议录音。
- 用户希望通过提供 OSS/HTTP URL 的方式转写小时级录音，避免在我们服务器进行大文件上传。
- DashScope 提供的 `paraformer-v2` 支持异步提交 + 轮询，适合长任务场景。

## 变更内容
- 新增专门面向长音频的 API 端点，接受远程 `file_urls`，不再走 multipart 上传。
- 集成 DashScope `paraformer-v2` 的异步调用流程（提交 + fetch），提供 PENDING/RUNNING/SUCCEEDED/FAILED 状态管理。
- 接口立即返回轻量任务信息（task_id、task_status），完成后返回转写结果的下载 URL，暂不触发会议纪要 Pipeline。
- 支持 `paraformer-v2`（多语种、任意采样率）与 `paraformer-8k-v2`（8kHz 中文电话场景）两种模型，允许通过请求或配置切换；仅 `paraformer-v2` 暴露 `language_hints`。
- 强制要求输入源为可公网访问的 HTTP/HTTPS URL（OSS 需使用临时 URL），对本地/`oss://`（SDK）上传直接拒绝；执行官方上限：单次最多 100 个 URL、单文件 ≤2GB 且时长 ≤12 小时。
- 增加可配置的限制（单次 URL 数量、轮询间隔、超时时间），并将结果/元数据持久化到 `uploads/audios/long/{task_id}/`。
- 更新 OpenSpec `api` 能力文档，描述新端点的请求约束、状态机和错误处理。

## 影响
- **Specs**：`specs/api/spec.md` 将增加 paraformer 长音频接口及其异步生命周期的描述。
- **后端**：新增 FastAPI 路由（如 `POST /api/v1/audio/transcribe-long`）和调用 `dashscope.audio.asr.Transcription` 的服务层。
- **Pipeline**：可选的辅助逻辑，用于在拿到 `transcription_url` 后缓存 JSON（暂不生成会议纪要）。
- **配置**：新增模型名称、长音频超时、轮询节奏等环境变量。

## 未决问题
1. 是否需要提供 `GET /api/v1/audio/transcribe-long/{task_id}` 独立状态端点，还是复用现有任务轮询机制？（默认：新增独立端点。）
2. 返回结果时，需要代理/回传 DashScope 的 JSON，还是直接暴露签名 `transcription_url` 并缓存一份？（默认：返回 URL 并缓存副本。）
