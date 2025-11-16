# 技术设计文档

## 架构概览

```
┌─────────────┐
│   客户端    │
│ (上传音频)  │
└──────┬──────┘
       │ POST /api/v1/audio/transcribe
       ▼
┌─────────────────────────────────────┐
│      FastAPI 路由层                 │
│      api/audio_api.py               │
│  - 文件上传处理                     │
│  - 格式和大小验证                   │
│  - 调用 AudioPipeline               │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      AudioPipeline                  │
│      pipelines/audio_pipeline.py    │
│  ┌───────────────────────────────┐  │
│  │ 1. validate_audio_file()      │  │
│  │    - 格式检查                 │  │
│  │    - 大小检查                 │  │
│  │    - 时长检测                 │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │ 2. transcribe_audio()         │  │
│  │    - 调用 DashScope ASR       │  │
│  │    - 启用 ITN                 │  │
│  │    - 重试逻辑                 │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │ 3. generate_minutes()         │  │
│  │    - 调用 qwen-plus LLM       │  │
│  │    - 结构化纪要生成           │  │
│  │    - 关键词提取               │  │
│  └───────────┬───────────────────┘  │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │ 4. format_output()            │  │
│  │    - 组装响应数据             │  │
│  │    - 元数据记录               │  │
│  └───────────────────────────────┘  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      响应返回                       │
│  - 转写文本                         │
│  - 会议纪要                         │
│  - 元数据                           │
└─────────────────────────────────────┘
```

## 目录结构

```
api/
├── __init__.py
├── main.py                   # API 主入口（整合现有 api.py）
├── audio_api.py              # 音频接口路由
└── audio_models.py           # 音频 API 数据模型

pipelines/
├── audio_pipeline.py         # 音频处理流程
└── prompts/
    └── meeting_minutes.txt   # 会议纪要 prompt

data/
└── audios/                   # 上传的音频文件存储
```

---

## 核心组件设计

### 1. AudioPipeline 类

**职责**：
- 协调音频转写和会议纪要生成的完整流程
- 管理与外部 API（ASR、LLM）的交互
- 处理错误和重试逻辑

**关键方法**：
```python
class AudioPipeline:
    def __init__(self, api_key: str, config: AudioConfig):
        """初始化 Pipeline，配置 DashScope 客户端"""
        
    async def validate_audio_file(self, file_path: str) -> AudioMetadata:
        """验证音频文件并提取元数据"""
        
    async def transcribe_audio(self, file_path: str) -> str:
        """调用 ASR API 转写音频为文本"""
        
    async def generate_meeting_minutes(self, transcription: str) -> MeetingMinutes:
        """调用 LLM 生成会议纪要"""
        
    async def process(self, file_path: str) -> AudioProcessingOutput:
        """主处理流程：验证 -> 转写 -> 生成纪要"""
```

---

### 2. 数据模型设计

#### AudioMetadata（音频元数据）
```python
class AudioMetadata(BaseModel):
    duration_seconds: float  # 音频时长（秒）
    format: str              # 文件格式（m4a, mp3, etc.）
    file_size_mb: float      # 文件大小（MB）
    sample_rate: Optional[int]  # 采样率
    channels: Optional[int]     # 声道数
```

#### MeetingMinutes（会议纪要）
```python
class MeetingMinutes(BaseModel):
    title: str                    # 会议/访谈标题
    content: str                  # 结构化纪要内容
    key_quotes: List[str]         # 关键原话引述
    keywords: List[str]           # 关键词（3-8个）
    generated_at: datetime        # 生成时间
```

#### AudioProcessingOutput（完整输出）
```python
class AudioProcessingOutput(BaseModel):
    transcription_text: str       # 完整转写文本
    meeting_minutes: MeetingMinutes  # 会议纪要
    audio_metadata: AudioMetadata    # 音频元数据
    processing_stats: ProcessingStats  # 处理统计
```

---

### 3. Prompt 设计

#### ASR 系统提示词（`prompts/audio_transcription.txt`）
```
你是一个专业的语音识别助手，能够将音频内容准确地转录为文本。

要求：
1. 准确转录所有语音内容，包括口语化表达
2. 保留语气词（嗯、啊、呃等）
3. 标注不清晰的部分为 [不清晰]
4. 区分不同说话人（如果可识别）
5. 保持原始语句顺序

输出格式：纯文本，不添加额外注释。
```

#### 会议纪要生成 Prompt（`prompts/meeting_minutes.txt`）
```
你是一个专业的会议纪要整理专家，擅长将访谈录音转写文本整理成条理清晰的会议纪要。

输入：完整的访谈转写文本
输出：结构化的会议纪要

核心原则：
1. **忠实原文**：严禁任何曲解、过度解读或主观推测
2. **保留关键原话**：重要观点使用引号标注原话
3. **条理清晰**：按主题或时间顺序梳理内容
4. **易于理解**：语言简洁，逻辑清晰

纪要结构：
1. **标题**：概括本次访谈/会议的主题
2. **主要内容**：分段落梳理讨论要点
3. **关键引述**：保留重要原话（带引号）
4. **关键词**：提取 3-8 个关键词，用 <KEYWORD>XXX</KEYWORD> 标签标注

适用场景：投研项目尽调、专家访谈、客户访谈

示例关键词：
<KEYWORD>数字化转型</KEYWORD>
<KEYWORD>供应链管理</KEYWORD>
<KEYWORD>成本控制</KEYWORD>

请开始整理以下转写文本：
{transcription_text}
```

---

### 4. API 端点详细设计

#### POST /api/v1/audio/transcribe

**请求**：
```
Content-Type: multipart/form-data

file: <audio_file>  (必需)
options: {          (可选)
  "enable_itn": true,
  "language": "zh",
  "custom_prompt": "..."
}
```

**响应（同步处理）**：
```json
{
  "success": true,
  "data": {
    "transcription_text": "完整转写文本...",
    "meeting_minutes": {
      "title": "XX项目尽调访谈",
      "content": "...",
      "key_quotes": ["重要原话1", "重要原话2"],
      "keywords": ["关键词1", "关键词2"]
    },
    "audio_metadata": {
      "duration_seconds": 180,
      "format": "m4a",
      "file_size_mb": 12.5
    }
  },
  "error": null,
  "metadata": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-13T10:30:00Z",
    "processing_time": 45.2,
    "transcription_time": 30.1,
    "llm_time": 15.1
  }
}
```

**响应（异步处理）**：
```json
{
  "success": true,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "estimated_time": 300
  },
  "error": null,
  "metadata": {
    "timestamp": "2025-11-13T10:30:00Z"
  }
}
```

---

### 5. 同步/异步决策逻辑

```python
async def should_process_async(audio_metadata: AudioMetadata) -> bool:
    """
    决定是否异步处理音频
    
    异步处理条件：
    - 音频时长 >= 10 分钟（可配置）
    - 文件大小 >= 50MB（可配置）
    - 当前系统负载高（可选）
    """
    async_threshold = int(os.getenv("AUDIO_ASYNC_THRESHOLD", "600"))  # 默认 10 分钟
    
    if audio_metadata.duration_seconds >= async_threshold:
        return True
    
    if audio_metadata.file_size_mb >= 50:
        return True
        
    return False
```

---

### 6. 错误处理策略

#### ASR API 错误处理
```python
async def transcribe_audio_with_retry(file_path: str, max_retries: int = 3):
    """带重试的 ASR 调用"""
    for attempt in range(max_retries):
        try:
            response = await call_dashscope_asr(file_path)
            return response
        except DashScopeAPIError as e:
            if attempt == max_retries - 1:
                raise ServiceUnavailableError("ASR 服务暂时不可用")
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

#### LLM API 错误处理
```python
async def generate_minutes_with_fallback(transcription: str):
    """带降级的会议纪要生成"""
    try:
        minutes = await call_llm_api(transcription)
        return minutes
    except LLMAPIError as e:
        logger.error(f"LLM 生成失败: {e}")
        # 降级：返回转写文本，纪要为空
        return None
```

---

### 7. 性能优化考虑

#### 音频分片处理（未来优化）
- 超长音频（>60分钟）切分为多个片段
- 并行调用 ASR API
- 拼接转写结果后再生成纪要

#### 缓存机制
- 对相同音频文件（基于 MD5 哈希）缓存转写结果
- 减少重复 API 调用

#### 资源管理
- 限制并发处理数量（避免内存溢出）
- 及时清理临时文件
- 监控 API 调用频率（避免触发限流）

---

### 8. 安全考虑

- **文件上传安全**：
  - 验证 MIME 类型
  - 限制文件大小
  - 隔离存储（每个 task_id 独立目录）
  
- **API 安全**：
  - 密钥管理（环境变量，不硬编码）
  - 请求频率限制
  - 日志脱敏（不记录音频内容）

- **数据隐私**：
  - 音频文件和转写文本自动清理
  - 敏感信息不写入日志
  - 支持客户端指定保留时间

---

## 技术栈

- **Web 框架**：FastAPI
- **ASR 服务**：阿里云 DashScope qwen3-asr-flash (MultiModalConversation API)
- **LLM 服务**：阿里云 DashScope qwen-plus-latest
- **音频处理**：无需额外库（DashScope 直接处理）
- **异步任务**：asyncio + 现有任务队列
- **存储**：本地文件系统

---

## 部署注意事项

1. **环境变量配置**：
   - `DASHSCOPE_API_KEY`：阿里云 API 密钥
   - `AUDIO_MAX_FILE_SIZE`：最大文件大小（字节）
   - `AUDIO_MAX_DURATION`：最大时长（秒）
   - `AUDIO_ASYNC_THRESHOLD`：异步处理阈值（秒）

2. **存储空间**：
   - 确保 `uploads/audio/` 和 `outputs/audio/` 有足够空间
   - 配置定时清理任务

3. **网络要求**：
   - 稳定的阿里云 API 连接
   - 足够的带宽（音频上传）

4. **监控指标**：
   - ASR 调用成功率
   - LLM 调用成功率
   - 平均处理时长
   - 错误率
