# PDF 商业计划书提取 UI 变更

## 概述

为 PDF 商业计划书信息提取功能开发现代化 Web UI 界面，与现有音频转写 UI 保持设计风格统一。

## 文件列表

- [proposal.md](./proposal.md) - 变更提案：功能需求、用户场景、成功指标
- [design.md](./design.md) - 技术设计：架构、组件设计、状态管理、API 集成
- [tasks.md](./tasks.md) - 开发任务：分阶段任务清单、验收标准、开发计划

## 核心功能

1. **顶部导航菜单**：音频转写 / PDF 提取 Tab 切换
2. **批量上传**：支持拖拽上传最多 10 个 PDF 文件
3. **15 字段展示**：卡片式布局展示提取的结构化信息
4. **任务中心**：历史任务列表、状态过滤、实时刷新
5. **队列监控**：显示异步队列状态和健康度

## 设计原则

- **设计统一**：与音频 UI 保持相同的 TailwindCSS 黑白灰主题
- **组件复用**：复用现有的 `react-dropzone`、`react-markdown`、`zustand`
- **状态隔离**：`usePdfStore` 和 `useAudioStore` 完全独立
- **体验优先**：批量上传、实时轮询、卡片展示、一键下载

## 技术栈

- **前端**：React 18 + TypeScript + TailwindCSS + Vite
- **状态管理**：Zustand
- **文件上传**：react-dropzone
- **Markdown 渲染**：react-markdown
- **后端**：FastAPI（已完成，无需额外开发）

## 开发状态

- [x] 后端 API 开发完成（7 个端点）
- [x] OpenSpec 提案创建
- [ ] 前端组件开发
- [ ] 集成测试
- [ ] 用户验收

## 相关资源

- 后端 API 目录：`api/pdf/`
- 前端目录：`frontend/src/components/pdf/`
- 状态管理：`frontend/src/store/usePdfStore.ts`
- API 客户端：`frontend/src/services/pdfApi.ts`

## 下一步

1. 开始 Phase 1 开发（基础架构：类型定义、API 客户端、状态管理）
2. 开发 Phase 2（顶部导航 Tab）
3. 开发 Phase 3（PDF 核心组件）
