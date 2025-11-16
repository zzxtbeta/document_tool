# 音频转写 UI 界面技术设计

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   浏览器 (Browser)                    │
│  ┌──────────────────────────────────────────────┐   │
│  │          React UI (TypeScript)               │   │
│  │  - 拖拽上传组件 (react-dropzone)              │   │
│  │  - Markdown 预览 (react-markdown)            │   │
│  │  - 进度显示 (状态管理)                         │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │ HTTP/REST
                        ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend                        │
│  ┌──────────────────────────────────────────────┐   │
│  │  新增 API 路由                                 │   │
│  │  - POST /api/v1/audio/transcribe-md          │   │
│  │  - GET  /api/v1/audio/download/{task_id}    │   │
│  │  - GET  /api/v1/audio/preview/{task_id}     │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  AudioPipeline 增强                           │   │
│  │  - save_as_markdown() 新方法                  │   │
│  │  - 目录参数支持                                │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              文件系统                                │
│  uploads/audio/                                     │
│    ├── {task_id}/                                   │
│    │   ├── {filename}.m4a       (原始音频)          │
│    │   ├── transcript.txt       (转写文本)          │
│    │   └── minutes.md           (会议纪要)          │
│    └── custom_dir/               (用户自定义目录)    │
└─────────────────────────────────────────────────────┘
```

## 前端设计

### 技术栈选型

```typescript
// package.json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-dropzone": "^14.2.3",       // 拖拽上传
    "react-markdown": "^9.0.1",         // Markdown 渲染
    "axios": "^1.6.0",                  // HTTP 客户端
    "zustand": "^4.4.7"                 // 状态管理
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.16"
  }
}
```

**选型理由**：
- **React 18**：主流框架，生态成熟，TypeScript 支持完善
- **react-dropzone**：拖拽上传最佳实践库，API 简洁
- **react-markdown**：纯 JS Markdown 渲染，无需额外构建
- **TailwindCSS**：工具类优先，快速定制黑白灰主题
- **zustand**：轻量级状态管理，无模板代码

### 目录结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── AudioUploader.tsx        # 拖拽上传组件
│   │   ├── MarkdownPreview.tsx      # Markdown 预览组件
│   │   ├── ProgressBar.tsx          # 进度条组件
│   │   └── FileList.tsx             # 文件列表组件
│   ├── services/
│   │   └── audioApi.ts              # API 客户端
│   ├── store/
│   │   └── useAudioStore.ts         # 全局状态管理
│   ├── types/
│   │   └── audio.ts                 # TypeScript 类型定义
│   ├── App.tsx                      # 根组件
│   ├── main.tsx                     # 入口文件
│   └── index.css                    # 全局样式 (TailwindCSS)
├── tailwind.config.js               # TailwindCSS 配置
├── tsconfig.json                    # TypeScript 配置
├── vite.config.ts                   # Vite 配置
└── package.json
```

### 核心组件设计

#### 1. AudioUploader.tsx（拖拽上传组件）

```typescript
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAudioStore } from '../store/useAudioStore';

export const AudioUploader: React.FC = () => {
  const { uploadAudio, setProgress } = useAudioStore();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // 文件验证
    const validFormats = ['audio/m4a', 'audio/mp3', 'audio/wav', 'audio/flac'];
    if (!validFormats.includes(file.type)) {
      alert('仅支持 m4a, mp3, wav, flac 格式');
      return;
    }

    // 上传
    await uploadAudio(file, {
      output_dir: 'uploads/audio',  // 可配置
      format: 'markdown'
    });
  }, [uploadAudio]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.m4a', '.mp3', '.wav', '.flac', '.opus', '.aac']
    },
    maxSize: 100 * 1024 * 1024,  // 100MB
    multiple: false
  });

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center
        transition-colors cursor-pointer
        ${isDragActive 
          ? 'border-blue-500 bg-blue-50' 
          : 'border-gray-300 hover:border-gray-400'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="text-gray-600">
        {isDragActive ? (
          <p className="text-lg">松开鼠标上传文件...</p>
        ) : (
          <>
            <p className="text-lg mb-2">拖拽音频文件到此处，或点击选择</p>
            <p className="text-sm text-gray-400">
              支持 m4a, mp3, wav, flac 格式，最大 100MB
            </p>
          </>
        )}
      </div>
    </div>
  );
};
```

#### 2. MarkdownPreview.tsx（Markdown 预览）

```typescript
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { useAudioStore } from '../store/useAudioStore';

export const MarkdownPreview: React.FC = () => {
  const { currentMinutes, isLoading } = useAudioStore();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (!currentMinutes) {
    return (
      <div className="text-center text-gray-400 py-12">
        上传音频文件后，会议纪要将显示在此处
      </div>
    );
  }

  return (
    <div className="prose prose-gray max-w-none">
      <ReactMarkdown>{currentMinutes}</ReactMarkdown>
      <button
        onClick={() => {/* 下载逻辑 */}}
        className="mt-4 px-4 py-2 bg-gray-900 text-white rounded hover:bg-gray-800"
      >
        下载 Markdown 文件
      </button>
    </div>
  );
};
```

#### 3. useAudioStore.ts（状态管理）

```typescript
import { create } from 'zustand';
import { audioApi } from '../services/audioApi';

interface AudioState {
  currentMinutes: string | null;
  isLoading: boolean;
  progress: number;
  error: string | null;
  uploadAudio: (file: File, options: any) => Promise<void>;
  setProgress: (progress: number) => void;
}

export const useAudioStore = create<AudioState>((set) => ({
  currentMinutes: null,
  isLoading: false,
  progress: 0,
  error: null,

  uploadAudio: async (file, options) => {
    set({ isLoading: true, error: null, progress: 0 });
    
    try {
      // 模拟上传进度
      const progressInterval = setInterval(() => {
        set((state) => ({ 
          progress: Math.min(state.progress + 10, 90) 
        }));
      }, 500);

      // 调用 API
      const response = await audioApi.transcribe(file, options);
      
      clearInterval(progressInterval);
      set({ 
        currentMinutes: response.markdown_content,
        isLoading: false,
        progress: 100
      });
    } catch (error) {
      set({ 
        error: '处理失败，请重试',
        isLoading: false,
        progress: 0
      });
    }
  },

  setProgress: (progress) => set({ progress })
}));
```

### UI 设计规范

#### 配色方案（黑白灰主题）

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f9fafb',   // 极浅灰
          100: '#f3f4f6',  // 浅灰
          200: '#e5e7eb',  // 中浅灰
          300: '#d1d5db',  // 灰
          400: '#9ca3af',  // 中灰
          500: '#6b7280',  // 深灰
          600: '#4b5563',  // 较深灰
          700: '#374151',  // 深灰
          800: '#1f2937',  // 极深灰
          900: '#111827',  // 黑
        },
        accent: {
          blue: '#3b82f6',    // 点缀色：蓝
          green: '#10b981',   // 点缀色：绿（成功）
          red: '#ef4444',     // 点缀色:红（错误）
        }
      }
    }
  }
};
```

#### 布局设计

```
┌────────────────────────────────────────────────────┐
│  Header (固定顶部)                                   │
│  [Logo]  音频转写与会议纪要生成                       │
└────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────┐
│  Main Content (双栏布局)                             │
│  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  左侧：上传区      │  │  右侧：预览区           │  │
│  │                  │  │                       │  │
│  │  [拖拽上传框]     │  │  [Markdown 预览]      │  │
│  │                  │  │                       │  │
│  │  [进度条]         │  │  [下载按钮]           │  │
│  │                  │  │                       │  │
│  │  [历史记录]       │  │                       │  │
│  └──────────────────┘  └───────────────────────┘  │
└────────────────────────────────────────────────────┘
```

## 后端增强

### API 端点设计

#### 1. POST /api/v1/audio/transcribe（增强）

**功能**：音频转写，支持 JSON 或 Markdown 格式输出

**新增参数**：

```typescript
interface TranscribeRequest {
  file: File;                       // 音频文件（必填）
  output_format?: 'json' | 'markdown';  // 输出格式（可选，默认 'json'）
  output_dir?: string;              // 输出目录（可选，默认 'uploads/audios'）
  enable_itn?: boolean;             // 启用逆文本规范化（可选，默认 true）
  
  // 新增 ASR 配置参数
  asr_context?: string;             // ASR 识别上下文（可选，用于专业术语提示）
  language?: string;                // 音频语种（可选，如 'zh'、'en'，不指定则自动检测）
}
```

**参数说明**：

- `asr_context`: 定制化识别上下文，用于提高专业领域词汇的识别准确率
  - 示例：医疗领域可传入 "本次对话涉及医学术语，如CT、核磁共振、血常规等"
  - 示例：金融领域可传入 "讨论内容包含投资、估值、PE、IRR 等金融术语"
  - 为空则使用默认识别能力
  
- `language`: 指定音频语种
  - 支持值：'zh'（中文）、'en'（英文）、'ja'（日语）、'ko'（韩语）等
  - 不指定则模型自动检测语种
  - 已知语种时指定可提升识别准确率
```

**JSON 格式响应（默认）**：

```typescript
interface TranscribeJsonResponse {
  task_id: string;
  transcript: string;
  meeting_minutes: MeetingMinutes;
  processing_stats: ProcessingStats;
  audio_metadata: AudioMetadata;
}
```

**Markdown 格式响应**：

```typescript
interface TranscribeMarkdownResponse {
  task_id: string;
  transcript: string;
  markdown_content: string;          // 新增：Markdown 格式纪要
  markdown_file_path: string;        // 新增：文件路径
  download_url: string;              // 新增：下载链接
  processing_stats: ProcessingStats;
  audio_metadata: AudioMetadata;
}
```

**设计优势**：
- ✅ **零冗余**：复用现有端点，仅新增参数
- ✅ **向后兼容**：默认行为完全不变
- ✅ **灵活切换**：前端可根据需要选择格式

#### 2. GET /api/v1/audio/download/{task_id}（新增）

**功能**：下载 Markdown 文件

**响应**：`FileResponse`，Content-Type: `text/markdown`

---

## 后端增强

### pipelines/audio_pipeline.py（新增方法）

```python
class AudioPipeline:
    def save_as_markdown(
        self, 
        minutes: MeetingMinutes, 
        output_path: Path
    ) -> Path:
        """保存会议纪要为 Markdown 文件"""
        
        # 构建 Markdown 内容（保留 LLM 原始格式）
        markdown_content = f"""# {minutes.title}

## 主要内容
{minutes.content}

## 关键引述
{minutes.key_quotes}

## 关键词
{', '.join([f'`{kw}`' for kw in minutes.keywords])}

---
*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content, encoding='utf-8')
        
        return output_path
```

#### api/audio_api.py（增强现有路由）

```python
@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    output_format: str = Form("json"),  # 新增参数
    output_dir: str = Form("data/audios")  # 新增参数
):
    """音频转写接口，支持 JSON 或 Markdown 格式输出"""
    
    # 验证 output_format
    if output_format not in ["json", "markdown"]:
        raise HTTPException(
            status_code=400,
            detail="output_format 必须为 'json' 或 'markdown'"
        )
    
    # 验证文件格式和大小（现有逻辑）
    # ...
    
    # 执行转写和生成纪要（现有逻辑）
    task_id = str(uuid.uuid4())
    audio_path = Path(output_dir) / task_id / file.filename
    result = await pipeline.transcribe_audio(audio_path)
    
    # 根据 output_format 返回不同响应
    if output_format == "markdown":
        # 保存为 Markdown
        md_filename = f"{file.filename.stem}_minutes.md"
        md_path = audio_path.parent / md_filename
        pipeline.save_as_markdown(result.meeting_minutes, md_path)
        
        # 读取 Markdown 内容
        markdown_content = md_path.read_text(encoding='utf-8')
        
        # 返回 Markdown 响应
        return {
            "task_id": task_id,
            "transcript": result.transcript,
            "markdown_content": markdown_content,
            "markdown_file_path": str(md_path),
            "download_url": f"/api/v1/audio/download/{task_id}",
            "processing_stats": result.processing_stats,
            "audio_metadata": result.audio_metadata
        }
    else:
        # 返回传统 JSON 响应（现有逻辑）
        return {
            "task_id": task_id,
            "transcript": result.transcript,
            "meeting_minutes": result.meeting_minutes,
            "processing_stats": result.processing_stats,
            "audio_metadata": result.audio_metadata
        }

@router.get("/download/{task_id}")
async def download_markdown(task_id: str):
    """下载 Markdown 文件"""
    # 查找文件
    base_dir = Path("data/audios")
    md_files = list(base_dir.glob(f"{task_id}/*_minutes.md"))
    
    if not md_files:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    md_path = md_files[0]
    return FileResponse(
        path=md_path,
        filename=f"meeting_minutes_{task_id}.md",
        media_type="text/markdown"
    )
```

**重要变更**：
- ✅ **仅增强一个端点**：`/transcribe` 支持双格式
- ✅ **共享核心逻辑**：ASR 和 LLM 处理逻辑完全复用
- ✅ **条件分支返回**：根据 `output_format` 决定响应结构
```

## 部署方案

### 开发环境

```bash
# 后端
cd d:\code\document_tool
conda activate document
uvicorn api.main:app --reload --port 8000

# 前端
cd frontend
npm run dev  # Vite dev server on port 5173
```

### 生产环境

```python
# api/main.py（新增静态文件托管）
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

**构建步骤**：

```bash
# 1. 构建前端
cd frontend
npm run build  # 输出到 dist/

# 2. 启动后端（包含前端静态文件）
cd ..
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 测试计划

### 前端测试

1. **组件测试**：使用 Vitest + React Testing Library
2. **端到端测试**：使用 Playwright 测试完整上传流程

```javascript
import axios from 'axios';

// API 客户端配置
const audioApi = {
  async transcribe(file, format = 'markdown') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('output_format', format);
    
    const response = await axios.post(
      '/api/v1/audio/transcribe',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          // 更新进度条
        }
      }
    );
    
    return response.data;
  },
  
  download(taskId) {
    return `/api/v1/audio/download/${taskId}`;
  }
};
```
```

### 后端测试

```python
# tests/test_audio_api.py

def test_transcribe_default_json():
    """测试默认 JSON 格式（向后兼容）"""
    with open("tests/fixtures/sample.m4a", "rb") as f:
        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("sample.m4a", f, "audio/m4a")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "meeting_minutes" in data
    assert "markdown_content" not in data  # 默认不返回 Markdown

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
    assert "markdown_content" in data
    assert data["markdown_content"].startswith("# ")
    assert Path(data["markdown_file_path"]).exists()

def test_transcribe_invalid_format():
    """测试错误的 output_format"""
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("sample.m4a", audio_bytes, "audio/m4a")},
        data={"output_format": "xml"}
    )
    
    assert response.status_code == 400
    assert "output_format 必须为" in response.json()["detail"]
```
```

## 性能优化

1. **前端**：
   - 使用 `React.lazy` 懒加载 Markdown 预览组件
   - 上传前压缩文件元数据，减少请求体积
   - 使用 Web Worker 处理大文件预览

2. **后端**：
   - 异步处理长音频文件（> 10MB）
   - 使用 Redis 缓存已处理的任务结果
   - 定期清理过期文件（> 7 天）

## 安全考虑

1. **文件上传**：
   - 严格验证文件类型和大小
   - 使用 UUID 作为文件名，避免路径遍历
   - 限制上传速率（每用户每分钟 5 次）

2. **目录访问**：
   - 禁止访问 `uploads/` 之外的目录
   - 验证 `output_dir` 参数，拒绝 `../` 路径

3. **Markdown 渲染**：
   - 使用 `react-markdown` 自动转义 HTML
   - 禁用危险特性（如内联脚本）

## 未来扩展

1. **批量处理**：支持一次上传多个音频文件
2. **历史记录**：展示最近处理的任务列表
3. **编辑功能**：在线编辑 Markdown 纪要
4. **导出格式**：支持导出为 PDF、Word
5. **实时转写**：支持实时录音并生成纪要
