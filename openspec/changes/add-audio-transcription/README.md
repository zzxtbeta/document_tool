# 音频转写和会议纪要 API

音频上传、自动转写和智能生成会议纪要的 API 服务。

## 功能特性

- ✅ **音频转写**: 使用阿里云 DashScope ASR (qwen3-asr-flash) 将语音转为文字
- ✅ **会议纪要**: 使用大语言模型 (qwen-plus-latest) 生成结构化纪要
- ✅ **关键信息提取**: 自动提取关键引述和关键词
- ✅ **多格式支持**: 支持 m4a, mp3, wav, flac, opus, aac 等格式
- ✅ **忠实原文**: 严禁曲解，保留重要原话

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `dashscope>=1.14.0` - 阿里云 DashScope SDK（ASR 和 LLM）
- `fastapi>=0.104.0` - Web 框架
- `uvicorn[standard]>=0.24.0` - ASGI 服务器

### 2. 配置环境变量

在 `.env` 文件中设置：

```bash
DASHSCOPE_API_KEY=your_dashscope_api_key
AUDIO_MAX_FILE_SIZE=100  # 最大文件大小（MB），默认 100MB
AUDIO_ASYNC_THRESHOLD=600  # 异步处理阈值（秒），默认 10分钟
```

### 3. 启动 API 服务

**方法 1: 使用批处理脚本（Windows）**
```bash
run_api.bat
```

**方法 2: 直接运行**
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. 测试服务

访问 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

或运行测试脚本：
```bash
# 测试 Pipeline（不需要启动 API）
python test_audio_quick.py

# 测试 API 端点（需要先启动 API）
python test_audio_api.py
```

## API 使用

### 端点 1: 健康检查

**GET** `/api/v1/audio/health`

检查音频服务是否可用。

**响应示例:**
```json
{
  "status": "healthy",
  "service": "audio_transcription",
  "models": {
    "asr": "qwen3-asr-flash",
    "llm": "qwen-plus-latest"
  },
  "max_file_size_mb": 100,
  "async_threshold_seconds": 600
}
```

### 端点 2: 音频转写和生成纪要

**POST** `/api/v1/audio/transcribe`

上传音频文件，获取转写文本和会议纪要。

**请求参数:**
- `file` (必需): 音频文件
- `enable_itn` (可选): 是否启用逆文本归一化，默认 `true`

**支持的音频格式:**
- m4a, mp3, wav, flac, opus, aac

**文件大小限制:**
- 最大 100MB（可配置）

**响应示例:**
```json
{
  "success": true,
  "data": {
    "transcription_text": "完整的转写文本内容...",
    "meeting_minutes": {
      "title": "XX项目尽调访谈",
      "content": "【第一部分】...\n【第二部分】...",
      "key_quotes": [
        "重要原话1",
        "重要原话2"
      ],
      "keywords": [
        "数字化转型",
        "供应链管理",
        "成本控制"
      ],
      "generated_at": "2025-11-13T10:30:00Z"
    },
    "audio_metadata": {
      "duration_seconds": 180.0,
      "format": "m4a",
      "file_size_mb": 12.5,
      "sample_rate": null,
      "channels": null
    },
    "processing_stats": {
      "total_time": 45.2,
      "transcription_time": 30.1,
      "llm_time": 15.1
    }
  },
  "error": null,
  "metadata": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-13T10:30:00Z",
    "filename": "interview.m4a",
    "file_size_mb": 12.5,
    "processing_time": 45.2
  }
}
```

## 使用示例

### Python 客户端

```python
import requests

# 上传音频文件
with open("interview.m4a", "rb") as f:
    files = {"file": ("interview.m4a", f, "audio/m4a")}
    data = {"enable_itn": "true"}
    
    response = requests.post(
        "http://localhost:8000/api/v1/audio/transcribe",
        files=files,
        data=data,
        timeout=300
    )

result = response.json()

# 查看转写文本
print("转写文本:", result['data']['transcription_text'])

# 查看会议纪要
minutes = result['data']['meeting_minutes']
print("\n标题:", minutes['title'])
print("\n内容:", minutes['content'])
print("\n关键词:", ', '.join(minutes['keywords']))
```

完整示例见 `examples/audio_transcription_example.py`。

### cURL 命令

```bash
curl -X POST "http://localhost:8000/api/v1/audio/transcribe" \
  -F "file=@interview.m4a" \
  -F "enable_itn=true"
```

### 快速测试脚本

运行快速测试脚本验证功能：

```bash
python test_audio_quick.py
```

## 会议纪要结构

生成的会议纪要遵循以下结构：

```
【标题】
用一句话概括本次访谈/会议的主题

【主要内容】
分段落梳理讨论要点，每个段落聚焦一个主题。
重要观点用"引号"标注原话。

【关键引述】
1. "重要原话1"
2. "重要原话2"
3. "重要原话3"

【关键词】
<KEYWORD>关键词1</KEYWORD>
<KEYWORD>关键词2</KEYWORD>
<KEYWORD>关键词3</KEYWORD>
```

## 核心原则

会议纪要生成遵循以下核心原则：

1. **忠实原文**: 严禁任何曲解、过度解读或主观推测
2. **保留关键原话**: 重要观点使用引号标注原话
3. **条理清晰**: 按主题或时间顺序梳理内容
4. **易于理解**: 语言简洁，逻辑清晰

## 适用场景

- 投研项目尽调
- 专家访谈
- 客户访谈
- 会议记录

## 技术架构

```
客户端上传音频
    ↓
FastAPI 路由 (api/audio_api.py)
    ↓
AudioPipeline (pipelines/audio_pipeline.py)
    ↓
    ├─ DashScope MultiModalConversation (qwen3-asr-flash) → 转写文本
    └─ DashScope Generation (qwen-plus-latest) → 会议纪要
```

## 项目结构

```
api/
├── main.py              # API 主入口（原 api.py）
├── models.py            # 通用 API 模型（原 api_models.py）
├── audio_api.py         # 音频转写路由
└── audio_models.py      # 音频相关数据模型

pipelines/
├── audio_pipeline.py    # 音频处理 Pipeline
└── prompts/
    └── meeting_minutes.txt  # 会议纪要生成 Prompt

data/
└── audios/             # 音频文件存储
```

## 性能说明

- **短音频 (<10分钟)**: 同步处理，立即返回结果
- **长音频 (≥10分钟)**: 异步处理（即将支持）
- **处理时间**: 取决于音频长度，通常为音频时长的 30-50%

## 错误处理

API 会返回清晰的错误信息：

- `400 Bad Request`: 文件格式不支持
- `413 Payload Too Large`: 文件超过大小限制
- `500 Internal Server Error`: ASR 或 LLM 服务异常
- `503 Service Unavailable`: 音频服务不可用

## 文件存储

上传的音频文件存储在：
```
data/audios/{task_id}/input.{ext}
```

## 开发和调试

### 检查 Pipeline

```bash
python test_audio_quick.py
```

### 查看日志

日志包含详细的处理信息：
- 音频元数据
- ASR 转写耗时
- LLM 生成耗时
- 错误堆栈

## 注意事项

1. **API 密钥**: 确保设置有效的 `DASHSCOPE_API_KEY`
2. **网络连接**: 需要稳定的阿里云 API 连接
3. **文件大小**: 建议控制在 100MB 以内
4. **音频质量**: 清晰的音频会获得更好的转写效果

## 后续优化

- [ ] 异步任务处理（长音频）
- [ ] 音频分片处理（超长音频）
- [ ] 转写结果缓存
- [ ] 多语言支持
- [ ] 说话人分离

## 许可证

MIT License
