# 音频转写 UI 前端

现代化的音频转写和会议纪要生成界面，使用 React + TypeScript + TailwindCSS 构建。

## 技术栈

- **框架**: React 18.2.0 + TypeScript 5.3.0
- **构建工具**: Vite 5.0.0 + SWC
- **样式**: TailwindCSS 3.4.0（自定义黑白灰主题）
- **状态管理**: Zustand 4.4.7
- **文件上传**: react-dropzone 14.2.3
- **Markdown 渲染**: react-markdown 9.0.1
- **HTTP 客户端**: axios 1.6.0

## 功能特性

- ✅ 拖拽上传音频文件（m4a, mp3, wav, flac, opus, aac）
- ✅ 实时处理进度展示
- ✅ Markdown 格式会议纪要预览
- ✅ 一键下载 Markdown 文件
- ✅ 响应式设计（支持桌面和移动端）
- ✅ 处理统计信息展示（转写时间、LLM 时间）

## 快速开始

### 前置要求

- Node.js 18+ 或 20+
- npm 或 yarn
- 后端 API 服务运行在 `http://localhost:8000`

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 完整使用流程

1. **启动后端服务**（在项目根目录）：
   ```bash
   python -m uvicorn api:app --reload --port 8000
   ```

2. **启动前端服务**（在 frontend 目录）：
   ```bash
   npm run dev
   ```

3. **使用界面**：
   - 拖拽或点击上传音频文件
   - 等待处理完成（10-30 秒）
   - 查看右侧的 Markdown 预览
   - 点击"下载 Markdown"按钮保存文件

## 项目结构

```
frontend/
├── src/
│   ├── components/         # React 组件
│   │   ├── AudioUploader.tsx      # 拖拽上传组件
│   │   ├── ProgressBar.tsx        # 进度条组件
│   │   └── MarkdownPreview.tsx    # Markdown 预览组件
│   ├── services/          # API 服务
│   │   └── audioApi.ts           # 音频转写 API 客户端
│   ├── store/            # 状态管理
│   │   └── useAudioStore.ts      # Zustand store
│   ├── types/            # TypeScript 类型定义
│   │   └── audio.ts              # 音频相关类型
│   ├── App.tsx           # 主应用组件
│   ├── main.tsx          # 应用入口
│   └── index.css         # 全局样式
├── public/               # 静态资源
├── index.html           # HTML 模板
├── vite.config.ts       # Vite 配置（含代理设置）
├── tailwind.config.js   # TailwindCSS 配置
└── package.json         # 依赖管理
```

## API 代理配置

开发环境下，Vite 会将 `/api` 请求代理到后端：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

## 设计主题

采用现代化的黑白灰配色方案：

- **主色调**: 灰色系（50-900）
- **强调色**: 蓝色（accent-blue）、绿色（accent-green）、红色（accent-red）
- **圆角**: 8px/12px（rounded-lg/xl）
- **阴影**: 柔和阴影（shadow-sm）
- **过渡**: 平滑过渡动画（duration-200/300）

## 组件说明

### AudioUploader

拖拽上传组件，支持文件验证和拖拽状态反馈。

**特性**：
- 文件格式验证
- 文件大小限制（100MB）
- 拖拽高亮效果
- 处理中禁用状态

### ProgressBar

进度条组件，显示上传和处理进度。

**特性**：
- 动态进度百分比
- 状态文本提示
- 错误信息展示
- 颜色编码（蓝色-处理中，绿色-完成，红色-错误）

### MarkdownPreview

Markdown 预览组件，展示生成的会议纪要。

**特性**：
- 自定义 Markdown 样式
- 处理统计信息展示
- 下载按钮
- 空状态提示
- 加载动画

## 故障排查

### 代理不工作

检查后端服务是否运行在 `localhost:8000`，或修改 `vite.config.ts` 中的代理配置。

### CORS 错误

确保后端启用了 CORS：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 上传失败

- 检查文件格式是否支持
- 确认文件大小不超过 100MB
- 查看浏览器控制台的错误信息

## 性能优化

- 使用 Vite SWC 编译器加速构建
- Zustand 轻量级状态管理
- 组件按需加载
- TailwindCSS JIT 模式

## 浏览器支持

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

---

## 原始 Vite 模板说明

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

