# API 规范变更：音频转写 UI 支持

## 变更概述

为支持 Web UI 界面，新增 Markdown 格式输出和文件下载接口。

## 端点变更

### 1. POST /api/v1/audio/transcribe（增强）

**描述**：上传音频文件并进行转写，支持返回 JSON 或 Markdown 格式

**变更内容**：
- ✅ 新增 `output_format` 参数（`json` | `markdown`）
- ✅ 新增 `output_dir` 参数，支持自定义输出目录
- ✅ 当 `output_format=markdown` 时，自动保存 `.md` 文件并返回内容
- ✅ 保持向后兼容，默认 `output_format=json`

**请求**：

```http
POST /api/v1/audio/transcribe HTTP/1.1
Content-Type: multipart/form-data

file: (binary)                          # 音频文件（必填）
output_format: markdown                 # 输出格式（可选，默认 json）
output_dir: uploads/audio               # 输出目录（可选）
```

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | File | ✅ | - | 音频文件（m4a/mp3/wav/flac/opus/aac，最大 100MB） |
| `output_format` | string | ❌ | `json` | 输出格式：`json` 或 `markdown` |
| `output_dir` | string | ❌ | `data/audios` | 输出目录路径（相对于项目根目录） |

**响应（output_format=json，默认）**：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript": "哟西，涵哥大大地帅。",
  "meeting_minutes": {
    "title": "简短语音记录",
    "content": "这是一段简短的语音记录...",
    "key_quotes": "\"哟西，涵哥大大地帅。\"",
    "keywords": ["涵哥", "语音记录"]
  },
  "processing_stats": {
    "asr_time": 4.12,
    "llm_time": 4.55,
    "total_time": 8.67
  },
  "audio_metadata": {
    "filename": "interview.m4a",
    "format": "m4a",
    "size_bytes": 4567890,
    "duration_seconds": 120.5
  }
}
```

**响应（output_format=markdown，新增）**：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript": "哟西，涵哥大大地帅。",
  "markdown_content": "# 【会议主题】投研访谈-张三\n\n## 主要内容\n...",
  "markdown_file_path": "uploads/audio/550e8400.../minutes.md",
  "download_url": "/api/v1/audio/download/550e8400-e29b-41d4-a716-446655440000",
  "processing_stats": {
    "asr_time": 4.12,
    "llm_time": 4.55,
    "total_time": 8.67
  },
  "audio_metadata": {
    "filename": "interview.m4a",
    "format": "m4a",
    "size_bytes": 4567890,
    "duration_seconds": 120.5
  }
}
```

**响应字段（markdown 格式特有）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `markdown_content` | string | Markdown 格式的会议纪要完整内容 |
| `markdown_file_path` | string | Markdown 文件在服务器上的路径 |
| `download_url` | string | 下载 Markdown 文件的 URL |

**错误响应**：

```json
// 400 Bad Request - 文件格式错误
{
  "detail": "不支持的音频格式，仅支持 m4a, mp3, wav, flac, opus, aac"
}

// 400 Bad Request - 输出格式错误
{
  "detail": "output_format 必须为 'json' 或 'markdown'"
}

// 400 Bad Request - 目录路径不安全
{
  "detail": "output_dir 包含非法字符或路径遍历"
}

// 500 Internal Server Error - 转写失败
{
  "detail": "音频转写失败，请稍后重试",
  "error_code": "ASR_API_ERROR"
}
```

---

### 3. 长音频 UI 相关接口（新增要求）

为 Web UI 增加长音频 URL 提交、任务历史与结果摘要展示能力。

#### Requirement: 长音频 URL 提交表单
- UI MUST 提供独立表单，允许用户填写远程音频 URL、模型（`paraformer-v2` / `paraformer-8k-v2`）以及可选语言提示。
- 表单提交后调用 `POST /api/v1/audio/transcribe-long`，并立即反馈内部 `task_id`、DashScope `task_id` 以及排队提示（含 24h TTL 说明）。
- 表单应校验 URL 可用性（必填、HTTP/HTTPS/OSS），并展示 DashScope 限制（1-100 个 URL、2GB/12h 上限）。

#### Requirement: 任务中心视图
- UI SHALL 展示任务列表，包含短/长音频（类型标签）、状态（PENDING/RUNNING/SUCCEEDED/FAILED）、模型、提交时间、TTL 倒计时。
- 列表数据来源：
  - 长音频：`GET /api/v1/audio/transcribe-long/{task_id}` + `GET /api/v1/audio/dashscope/tasks`
  - 短音频：本地上传记录（内存/IndexedDB）或后端补齐后扩展
- 列表项需要提供操作按钮：查看详情、下载 Markdown（短）、下载 JSON/音频（长）、取消任务（调用 `/dashscope/tasks/{dashscope_task_id}/cancel`，仅 PENDING 状态）。

#### Requirement: 任务详情摘要（Markdown/Card）
- 当用户点击列表项时，UI SHALL 打开 Drawer/Modal，将 JSON 结果关键信息（音频 URL、语言、subtask_status、transcription_url、本地缓存路径）渲染为易读 Markdown 或卡片。
- 对 `local_result_paths` 中的 JSON，提供“下载 JSON”按钮；对 `local_audio_paths` 提供“下载音频”按钮。
- 对成功的长音频任务，默认展示 DashScope 文本摘要（可从 JSON `text` 字段或自定义字段提取）；若 JSON 中缺少原文，需要提示“请下载 JSON 查看完整内容”。

#### Requirement: DashScope 代理接口集成
- UI MUST 使用新增的 `/api/v1/audio/dashscope/tasks` 和 `/api/v1/audio/dashscope/tasks/{dashscope_task_id}` 接口来展示历史任务及底层详情，默认查询最近 24h，支持分页与状态过滤。
- 当用户点击“取消”按钮时，调用 `/api/v1/audio/dashscope/tasks/{dashscope_task_id}/cancel` 并在 UI 中反馈结果。

---

### 2. GET /api/v1/audio/download/{task_id}（新增）

**描述**：下载指定任务的 Markdown 文件

**请求**：

```http
GET /api/v1/audio/download/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
```

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | ✅ | 任务 ID（从 `/transcribe-md` 接口获取） |

**响应**（200 OK）：

```http
HTTP/1.1 200 OK
Content-Type: text/markdown; charset=utf-8
Content-Disposition: attachment; filename="meeting_minutes_550e8400.md"

# 【会议主题】投研访谈-张三

## 主要内容
...
```

**错误响应**：

```json
// 404 Not Found - 任务不存在或文件已删除
{
  "detail": "文件不存在或已过期"
}
```

---

## 向后兼容性

### 现有客户端无需修改

- **默认行为不变**：不传 `output_format` 参数时，默认返回 JSON 格式（与现有行为一致）
- **响应结构兼容**：JSON 格式响应保持原有结构
- **渐进增强**：新参数为可选，不影响现有代码

---

## Markdown 格式规范

### 标准输出格式

```markdown
# 【会议主题】{标题}

## 主要内容
{会议的主要内容和讨论要点}

## 关键引述
{重要的原话引用}

## 关键词
`关键词1`, `关键词2`, `关键词3`, `关键词4`

---
*生成时间：2025-11-13 14:30:00*
```

### 字段说明

| 段落 | 说明 | 来源 |
|------|------|------|
| `# 【会议主题】` | 一级标题，总结会议主题 | LLM 生成的 `title` 字段 |
| `## 主要内容` | 详细记录会议内容和讨论点 | LLM 生成的 `content` 字段 |
| `## 关键引述` | 重要的原话摘录 | LLM 生成的 `key_quotes` 字段 |
| `## 关键词` | 4-6 个关键词（反引号包裹） | 从 LLM 输出中提取的 `<KEYWORD>` 标签 |
| 页脚时间戳 | 纪要生成时间 | 服务器当前时间 |

### 示例

**输入音频**：一段 5 分钟的投研访谈录音

**输出 Markdown**：

```markdown
# 【会议主题】某科技公司 AI 产品发展战略讨论

## 主要内容
本次访谈主要讨论了公司在 AI 产品方面的发展策略。嘉宾表示，公司将重点布局大模型应用层，特别是在金融和医疗领域的垂直应用。预计 2025 年 Q2 推出首款面向企业客户的 AI 助手产品。

在技术路线选择上，公司倾向于采用开源模型微调方案，而非从零训练。这样可以快速迭代产品，降低成本。同时，公司正在与多家数据供应商洽谈合作，以丰富训练语料。

关于竞争格局，嘉宾认为当前 AI 市场仍处于早期阶段，有足够的增长空间。公司的优势在于对垂直行业的深刻理解和客户资源积累。

## 关键引述
"我们不会去卷基础大模型，而是专注于应用层的差异化竞争。"

"2025 年的目标是服务 500 家企业客户，实现 AI 产品收入占比 30%。"

"开源模型 + 私有数据微调，这是我们的核心技术路线。"

## 关键词
`AI 产品战略`, `垂直应用`, `开源模型微调`, `企业客户`, `2025 年规划`

---
*生成时间：2025-11-13 14:30:00*
```

---

## 安全与验证

### 文件上传验证

1. **文件格式**：严格验证 MIME type 和文件扩展名
   ```python
   ALLOWED_FORMATS = {
       'audio/m4a': ['.m4a'],
       'audio/mp3': ['.mp3'],
       'audio/wav': ['.wav'],
       'audio/flac': ['.flac'],
       'audio/opus': ['.opus'],
       'audio/aac': ['.aac']
   }
   ```

2. **文件大小**：限制最大 100MB
   ```python
   MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
   if file.size > MAX_FILE_SIZE:
       raise HTTPException(status_code=413, detail="文件过大")
   ```

3. **目录路径**：防止路径遍历攻击
   ```python
   import os
   
   def validate_output_dir(output_dir: str) -> Path:
       # 禁止 .. 和绝对路径
       if '..' in output_dir or output_dir.startswith('/'):
           raise HTTPException(status_code=400, detail="非法路径")
       
       # 解析为绝对路径并验证
       base_dir = Path('uploads/audio').resolve()
       target_dir = (base_dir / output_dir).resolve()
       
       # 确保在允许的目录内
       if not str(target_dir).startswith(str(base_dir)):
           raise HTTPException(status_code=400, detail="路径越界")
       
       return target_dir
   ```

### 速率限制

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/transcribe-md")
@limiter.limit("5/minute")  # 每分钟最多 5 次请求
async def transcribe_audio_with_markdown(...):
    ...
```

---

## 文件管理策略

### 目录结构

```
uploads/audio/
├── {task_id_1}/
│   ├── original_audio.m4a      # 原始音频文件
│   ├── transcript.txt          # 转写文本
│   └── minutes.md              # 会议纪要（Markdown）
├── {task_id_2}/
│   └── ...
└── custom_project/             # 用户自定义目录
    ├── {task_id_3}/
    └── ...
```

### 文件清理策略

**自动清理规则**：

- **保留期限**：7 天
- **清理频率**：每天凌晨 2:00
- **清理逻辑**：删除创建时间超过 7 天的任务目录

**实现**（使用定时任务）：

```python
import schedule
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_files():
    base_dir = Path('uploads/audio')
    cutoff_time = datetime.now() - timedelta(days=7)
    
    for task_dir in base_dir.iterdir():
        if task_dir.is_dir():
            created_time = datetime.fromtimestamp(task_dir.stat().st_ctime)
            if created_time < cutoff_time:
                shutil.rmtree(task_dir)
                print(f"Deleted: {task_dir}")

# 每天凌晨 2:00 执行
schedule.every().day.at("02:00").do(cleanup_old_files)
```

---

## 错误码定义

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `INVALID_FORMAT` | 400 | 不支持的音频格式 | 检查文件扩展名 |
| `FILE_TOO_LARGE` | 413 | 文件大小超过限制 | 压缩音频或分割文件 |
| `INVALID_PATH` | 400 | 非法的目录路径 | 使用相对路径且不包含 `..` |
| `ASR_API_ERROR` | 500 | DashScope ASR 调用失败 | 检查 API Key 和网络 |
| `LLM_API_ERROR` | 500 | DashScope LLM 调用失败 | 检查 API 配额和参数 |
| `FILE_NOT_FOUND` | 404 | 文件不存在或已过期 | 确认 task_id 正确 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 | 稍后重试 |

---

## 示例代码

### cURL 示例

```bash
# 1. 默认 JSON 格式（向后兼容）
curl -X POST "http://localhost:8000/api/v1/audio/transcribe" \
  -F "file=@interview.m4a"

# 2. Markdown 格式输出
curl -X POST "http://localhost:8000/api/v1/audio/transcribe" \
  -F "file=@interview.m4a" \
  -F "output_format=markdown" \
  -F "output_dir=uploads/audio"

# 3. 下载 Markdown 文件
curl -X GET "http://localhost:8000/api/v1/audio/download/550e8400-e29b-41d4-a716-446655440000" \
  -o "会议纪要.md"
```

### Python 示例

```python
import requests

# 方式 1：JSON 格式（默认）
with open("interview.m4a", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/audio/transcribe",
        files={"file": ("interview.m4a", f, "audio/m4a")}
    )
    result = response.json()
    print(result["meeting_minutes"])

# 方式 2：Markdown 格式
with open("interview.m4a", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/audio/transcribe",
        files={"file": ("interview.m4a", f, "audio/m4a")},
        data={"output_format": "markdown"}
    )
    result = response.json()
    task_id = result["task_id"]
    markdown_content = result["markdown_content"]
    
    print(f"任务 ID: {task_id}")
    print(f"纪要内容:\n{markdown_content}")
    
    # 下载文件
    download_response = requests.get(
        f"http://localhost:8000/api/v1/audio/download/{task_id}"
    )
    with open("downloaded_minutes.md", "wb") as f:
        f.write(download_response.content)
```

### JavaScript (Axios) 示例

```javascript
import axios from 'axios';

// Markdown 格式输出
const formData = new FormData();
formData.append('file', audioFile);  // File 对象
formData.append('output_format', 'markdown');
formData.append('output_dir', 'uploads/audio');

const response = await axios.post(
  'http://localhost:8000/api/v1/audio/transcribe',
  formData,
  {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      console.log(`上传进度: ${progress}%`);
    }
  }
);

const { task_id, markdown_content } = response.data;

// 下载文件
const downloadUrl = `http://localhost:8000/api/v1/audio/download/${task_id}`;
window.open(downloadUrl);  // 在浏览器中触发下载
```

---

## 兼容性说明

### 向后兼容

- **现有接口不变**：`POST /api/v1/audio/transcribe` 保持原有行为，返回 JSON 格式
- **新增接口隔离**：`/transcribe-md` 作为独立端点，不影响现有客户端
- **数据模型扩展**：`AudioProcessingOutput` 增加 `markdown_file_path` 字段（可选）

### 版本控制

- **当前版本**：`v1`
- **新增功能**：Markdown 输出和文件下载
- **未来计划**：`v2` 可能支持实时转写、批量处理等高级功能

---

## 测试用例

### 测试 1：向后兼容（默认 JSON 格式）

```python
def test_transcribe_default_json():
    """测试默认行为：不传 output_format，返回 JSON"""
    with open("tests/fixtures/sample.m4a", "rb") as f:
        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("sample.m4a", f, "audio/m4a")}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证传统 JSON 响应字段
    assert "task_id" in data
    assert "transcript" in data
    assert "meeting_minutes" in data
    assert "markdown_content" not in data  # 不包含 Markdown 字段
```

### 测试 2：Markdown 格式输出

```python
def test_transcribe_markdown_format():
    """测试 Markdown 格式输出"""
    with open("tests/fixtures/sample.m4a", "rb") as f:
        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("sample.m4a", f, "audio/m4a")},
            data={"output_format": "markdown"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证 Markdown 响应字段
    assert "task_id" in data
    assert "markdown_content" in data
    assert data["markdown_content"].startswith("# 【")
    assert "markdown_file_path" in data
    assert "download_url" in data
    
    # 验证文件存在
    md_path = Path(data["markdown_file_path"])
    assert md_path.exists()
    assert md_path.suffix == ".md"
```

### 测试 3：自定义输出目录

```python
def test_transcribe_custom_output_dir():
    """测试自定义输出目录"""
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("sample.m4a", audio_bytes, "audio/m4a")},
        data={
            "output_format": "markdown",
            "output_dir": "uploads/audio/project_a"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证文件路径
    assert "project_a" in data["markdown_file_path"]
```

### 测试 4：文件下载

```python
def test_download_markdown():
    """测试文件下载"""
    # 先上传（Markdown 格式）
    upload_response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("sample.m4a", audio_bytes, "audio/m4a")},
        data={"output_format": "markdown"}
    )
    task_id = upload_response.json()["task_id"]
    
    # 下载
    download_response = client.get(f"/api/v1/audio/download/{task_id}")
    
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in download_response.headers["content-disposition"]
```

### 测试 5：错误处理

```python
def test_transcribe_invalid_format():
    """测试上传错误格式文件"""
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("doc.pdf", b"fake pdf", "application/pdf")}
    )
    
    assert response.status_code == 400
    assert "不支持的音频格式" in response.json()["detail"]

def test_transcribe_invalid_output_format():
    """测试错误的 output_format 参数"""
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("sample.m4a", audio_bytes, "audio/m4a")},
        data={"output_format": "xml"}
    )
    
    assert response.status_code == 400
    assert "output_format 必须为" in response.json()["detail"]

def test_transcribe_path_traversal():
    """测试路径遍历攻击"""
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("sample.m4a", audio_bytes, "audio/m4a")},
        data={"output_dir": "../../../etc"}
    )
    
    assert response.status_code == 400
    assert "非法路径" in response.json()["detail"]
```

---

## 变更总结

### 新增功能

✅ **参数化输出格式**：通过 `output_format` 参数支持 JSON/Markdown 双格式  
✅ **Markdown 文件生成**：自动保存 `.md` 文件到磁盘  
✅ **文件下载接口**：新增 `/download/{task_id}` 端点  
✅ **自定义目录**：通过 `output_dir` 参数指定输出位置  

### 设计优势

✅ **零冗余**：复用现有端点，无需新增 `/transcribe-md`  
✅ **向后兼容**：默认行为不变，现有客户端无需修改  
✅ **灵活性高**：一个端点满足多种输出需求  
✅ **易于维护**：统一的代码路径，减少重复逻辑  

### 安全增强

✅ **路径验证**：防止路径遍历攻击  
✅ **参数校验**：严格验证 `output_format` 枚举值  
✅ **速率限制**：防止 API 滥用  
✅ **文件清理**：自动删除过期文件  

### 向后兼容

✅ 不传参数时行为与现有完全一致  
✅ JSON 响应结构保持不变  
✅ 新增字段仅在 `output_format=markdown` 时返回  

### 下一步

- [ ] 实现批量处理（一次上传多个文件）
- [ ] 支持异步任务查询（长音频处理）
- [ ] 添加 WebSocket 实时进度推送
