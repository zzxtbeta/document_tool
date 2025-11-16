# Delta for API Specification

## ADDED Requirements

### Requirement: 音频上传与转写
系统 SHALL 支持上传音频文件并进行语音转文字转写，返回完整转写文本和结构化会议纪要。

#### Scenario: 音频文件上传
- **GIVEN** 客户端有一个有效的音频文件（m4a, mp3, wav, flac, opus 格式）
- **AND** 文件大小小于 100MB
- **AND** 音频时长小于 120 分钟
- **WHEN** 客户端发送 `POST /api/v1/audio/transcribe` 并上传文件
- **THEN** API 应接受文件并开始处理
- **AND** 响应应包含 task_id 或处理结果

#### Scenario: 短音频同步处理
- **GIVEN** 上传的音频时长小于 10 分钟
- **WHEN** API 接收音频文件
- **THEN** 应同步处理并返回 200 状态码
- **AND** 响应包含完整转写文本（`transcription_text` 字段）
- **AND** 响应包含结构化会议纪要（`meeting_minutes` 字段）
- **AND** 会议纪要包含关键词标签（`<KEYWORD></KEYWORD>` 格式）
- **AND** 处理时间应在 60 秒内完成

#### Scenario: 长音频异步处理
- **GIVEN** 上传的音频时长大于等于 10 分钟
- **WHEN** API 接收音频文件
- **THEN** 应返回 202 状态码（Accepted）
- **AND** 响应包含 `task_id` 字段
- **AND** 后台应异步处理该任务
- **AND** 客户端可通过 `GET /api/v1/tasks/{task_id}` 查询进度

#### Scenario: 音频格式验证
- **GIVEN** 客户端上传的文件格式不在支持列表中
- **OR** 文件不是有效的音频文件
- **WHEN** API 验证文件
- **THEN** 应返回 400 状态码（Bad Request）
- **AND** 错误消息应说明"不支持的音频格式，仅支持 m4a, mp3, wav, flac, opus"

#### Scenario: 音频文件过大
- **GIVEN** 客户端上传的音频文件超过 100MB
- **WHEN** API 检查文件大小
- **THEN** 应返回 413 状态码（Payload Too Large）
- **AND** 错误消息应说明"音频文件超过最大限制（100MB）"

#### Scenario: 音频时长超限
- **GIVEN** 音频文件时长超过 120 分钟
- **WHEN** API 检测音频时长
- **THEN** 应返回 422 状态码（Unprocessable Entity）
- **AND** 错误消息应说明"音频时长超过最大限制（120分钟）"

---

### Requirement: ASR 语音转写
系统 MUST 使用阿里云 DashScope ASR API（qwen3-asr-flash 模型）将音频转换为文本。

#### Scenario: ASR 成功转写
- **GIVEN** 有效的音频文件
- **WHEN** 调用 DashScope ASR API
- **THEN** 应启用 ITN（逆文本归一化）参数
- **AND** 应返回完整转写文本
- **AND** 转写文本应保留所有语句细节
- **AND** 应记录转写耗时

#### Scenario: ASR API 调用失败
- **GIVEN** ASR API 不可用或返回错误
- **WHEN** 尝试转写音频
- **THEN** 应重试最多 3 次（指数退避）
- **AND** 如果所有重试失败，应返回 503 状态码
- **AND** 错误消息应说明"语音转写服务暂时不可用，请稍后重试"
- **AND** 应记录详细错误日志

#### Scenario: 音频文件损坏
- **GIVEN** 音频文件格式正确但内容损坏
- **WHEN** ASR API 尝试处理
- **THEN** 应返回 422 状态码
- **AND** 错误消息应说明"音频文件损坏或无法解析"

---

### Requirement: 会议纪要生成
系统 SHALL 使用 LLM（qwen-plus-latest）生成结构化的会议纪要，忠实原文并便于阅读。

#### Scenario: 会议纪要生成成功
- **GIVEN** 完整的转写文本
- **WHEN** 调用 LLM 生成会议纪要
- **THEN** 会议纪要应包含以下结构：
  - 会议/访谈标题
  - 主要内容梳理（分段落/要点）
  - 关键原话引述（带引号）
  - 关键词标签（3-8个，用 `<KEYWORD></KEYWORD>` 标记）
- **AND** 纪要内容必须忠实原文，严禁曲解和过度解读
- **AND** 纪要应条理清晰、易于理解

#### Scenario: 关键词提取
- **GIVEN** 生成的会议纪要
- **WHEN** 解析纪要内容
- **THEN** 应提取 3-8 个关键词
- **AND** 关键词应使用 `<KEYWORD>XXX</KEYWORD>` 格式标注
- **AND** 关键词应高度凝练，准确反映内容主题
- **AND** 关键词应适用于投研、专家访谈、客户访谈场景

#### Scenario: LLM 生成失败
- **GIVEN** LLM API 不可用或返回错误
- **WHEN** 尝试生成会议纪要
- **THEN** 应重试最多 2 次
- **AND** 如果所有重试失败，应返回 503 状态码
- **AND** 错误消息应说明"会议纪要生成服务暂时不可用"
- **AND** 应仍然返回完整转写文本（即使纪要生成失败）

#### Scenario: Prompt 质量保证
- **GIVEN** 会议纪要生成 Prompt
- **WHEN** 调用 LLM API
- **THEN** Prompt 必须强调以下原则：
  - 忠实原文，禁止任何曲解和过度解读
  - 保留关键原话，必要时使用引号标注
  - 条理清晰，便于快速理解
  - 关键词凝练准确
  - 适用于投研尽调、专家访谈、客户访谈场景

---

### Requirement: 音频转写响应格式
系统 SHALL 返回包含完整转写文本和会议纪要的标准化响应。

#### Scenario: 成功响应格式
- **GIVEN** 音频处理完成
- **WHEN** 返回响应
- **THEN** 响应结构应包含：
  ```json
  {
    "success": true,
    "data": {
      "transcription_text": "完整的语音转写文本...",
      "meeting_minutes": {
        "title": "会议/访谈标题",
        "content": "结构化的纪要内容...",
        "key_quotes": ["关键原话1", "关键原话2"],
        "keywords": ["关键词1", "关键词2", "关键词3"]
      },
      "audio_metadata": {
        "duration_seconds": 180,
        "format": "m4a",
        "file_size_mb": 12.5
      }
    },
    "error": null,
    "metadata": {
      "task_id": "uuid",
      "timestamp": "ISO8601",
      "processing_time": 45.2,
      "transcription_time": 30.1,
      "llm_time": 15.1
    }
  }
  ```

#### Scenario: 部分失败响应
- **GIVEN** ASR 转写成功但 LLM 纪要生成失败
- **WHEN** 返回响应
- **THEN** 应返回 206 状态码（Partial Content）
- **AND** 响应应包含完整转写文本
- **AND** `meeting_minutes` 字段为 null
- **AND** `error` 字段应说明纪要生成失败原因
- **AND** 客户端仍可获取转写文本

---

### Requirement: 音频文件存储管理
系统 SHALL 管理上传音频文件的存储和清理。

#### Scenario: 音频文件上传存储
- **GIVEN** 客户端上传音频文件
- **WHEN** API 接收文件
- **THEN** 文件应保存到 `uploads/audio/{task_id}/input.{ext}`
- **AND** 应设置文件权限为只读
- **AND** 应记录文件元数据（大小、格式、时长）

#### Scenario: 音频输出文件存储
- **GIVEN** 音频处理完成
- **WHEN** 保存结果
- **THEN** 转写文本应保存到 `outputs/audio/{task_id}/transcription.txt`
- **AND** 会议纪要应保存到 `outputs/audio/{task_id}/meeting_minutes.json`

#### Scenario: 音频文件清理策略
- **GIVEN** 上传的音频文件处理完成超过 1 小时
- **WHEN** 定时清理任务运行
- **THEN** 应删除上传的音频文件
- **AND** 输出文件（转写+纪要）应保留 24 小时
- **AND** 超过 24 小时后应删除输出文件
- **AND** 应记录清理日志

---

### Requirement: 音频处理错误处理
系统 MUST 提供完善的音频处理错误处理和日志记录。

#### Scenario: 处理超时
- **GIVEN** 音频处理时间超过配置的超时时间（默认 1800 秒）
- **WHEN** 达到超时时间
- **THEN** 任务应被标记为 failed
- **AND** 错误信息应说明"音频处理超时，请尝试较短的音频或联系支持"
- **AND** 应释放相关资源

#### Scenario: 音频处理日志
- **GIVEN** API 收到音频转写请求
- **WHEN** 处理请求
- **THEN** 应记录日志包含：
  - 任务 ID
  - 音频元数据（时长、格式、大小）
  - ASR 转写耗时
  - LLM 生成耗时
  - 处理总耗时
  - 状态码
  - 错误信息（如有）
- **AND** 日志格式应为：`2025-11-13 10:00:00 - audio_api - INFO - [task_id] POST /api/v1/audio/transcribe - 200 - 45.2s (ASR: 30.1s, LLM: 15.1s)`

---

### Requirement: 音频处理环境配置
系统 MUST 支持通过环境变量配置音频处理参数。

#### Scenario: 音频限制配置
- **GIVEN** 设置环境变量：
  - `AUDIO_MAX_FILE_SIZE=104857600` (100MB)
  - `AUDIO_MAX_DURATION=7200` (120分钟)
  - `AUDIO_ASYNC_THRESHOLD=600` (10分钟)
- **WHEN** API 处理音频文件
- **THEN** 应使用这些配置值进行验证和处理决策

#### Scenario: 音频存储路径配置
- **GIVEN** 设置环境变量：
  - `AUDIO_UPLOAD_DIR=/data/audio/uploads`
  - `AUDIO_OUTPUT_DIR=/data/audio/outputs`
- **WHEN** API 存储音频文件
- **THEN** 应使用配置的路径

#### Scenario: ASR 和 LLM 配置
- **GIVEN** 设置环境变量：
  - `ASR_MODEL=qwen3-asr-flash`
  - `LLM_MODEL=qwen-plus-latest`
  - `ASR_ENABLE_ITN=true`
- **WHEN** 调用 API
- **THEN** 应使用这些配置的模型和参数
