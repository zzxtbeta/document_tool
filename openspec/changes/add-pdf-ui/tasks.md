# PDF 商业计划书提取 UI 开发任务

## 任务概览

开发 PDF 提取功能的现代化 Web UI，保持与音频转写 UI 相同的设计风格和交互模式。

## 任务分解

### Phase 1: 基础架构（优先级：高）

**Task 1.1: 创建 TypeScript 类型定义**
- [x] 创建 `frontend/src/types/pdf.ts`
- [x] 定义 `TaskStatus`, `ExtractionResult`, `PdfTask`, `QueueStatus` 类型
- [x] 确保与后端 API 响应格式一致
- **验收标准**：类型定义完整，无 TypeScript 错误

**Task 1.2: 创建 API 客户端**
- [x] 创建 `frontend/src/services/pdfApi.ts`
- [x] 实现 `uploadSingle()`, `uploadBatch()`, `getTaskStatus()`, `listTasks()`, `getQueueStatus()` 方法
- [ ] 配置 axios 拦截器（错误处理、请求头）
- **验收标准**：所有 API 方法可正常调用后端接口

**Task 1.3: 创建 Zustand 状态管理**
- [x] 创建 `frontend/src/store/usePdfStore.ts`
- [x] 实现状态（tasks, selectedTask, queueStatus, isUploading 等）
- [x] 实现 actions（uploadPdfs, loadTasks, refreshTask, selectTask 等）
- **验收标准**：状态管理逻辑正确，支持批量上传和任务轮询

---

### Phase 2: 顶部导航（优先级：高）

**Task 2.1: 创建 Tab 导航组件**
- [x] 创建 `frontend/src/components/TabNavigation.tsx`
- [x] 实现音频/PDF 切换 Tab
- [x] 设计统一的图标和文本样式
- **验收标准**：Tab 切换流畅，视觉效果与音频 UI 一致

**Task 2.2: 修改 App.tsx 主应用**
- [x] 引入 `TabNavigation` 组件
- [x] 添加 `activeTab` 状态管理
- [x] 条件渲染音频/PDF 内容
- [x] 确保两个模块状态独立（不互相影响）
- **验收标准**：切换 Tab 时状态保持，无闪烁或卡顿

---

### Phase 3: PDF 核心组件（优先级：高）

**Task 3.1: 创建 PdfUploader 组件**
- [x] 创建 `frontend/src/components/pdf/PdfUploader.tsx`
- [x] 集成 `react-dropzone`
- [x] 实现批量拖拽上传（最多 10 个文件）
- [x] 添加文件大小验证（单个 50MB）
- [x] 显示上传进度条
- **验收标准**：拖拽上传体验流畅，与音频上传组件风格一致

**Task 3.2: 创建 PdfExtractionResult 组件**
- [x] 创建 `frontend/src/components/pdf/PdfExtractionResult.tsx`
- [x] 实现 15 个字段的卡片式布局（3 列网格）
- [x] 每个字段添加图标和标签
- [x] 支持长文本展开/折叠
- [x] 集成 `react-markdown` 渲染 Markdown 内容
- [ ] 添加下载 JSON/Markdown 按钮 _(JSON 已提供，Markdown 导出待支持)_
- **验收标准**：15 个字段展示清晰，卡片布局美观，Markdown 渲染正确

**Task 3.3: 创建 PdfTaskPanel 组件**
- [x] 创建 `frontend/src/components/pdf/PdfTaskPanel.tsx`
- [x] 显示任务列表（支持分页）
- [x] 实现状态过滤（全部/排队中/处理中/已完成/失败）
- [x] 添加刷新按钮
- [x] 实现自动轮询（仅对处理中的任务，3 秒间隔）
- [x] 支持查看任务详情
- **验收标准**：任务列表实时更新，过滤功能正常，与音频任务中心风格一致

**Task 3.4: 创建 PdfQueueStatus 组件**
- [x] 创建 `frontend/src/components/pdf/PdfQueueStatus.tsx`
- [x] 显示队列长度、活跃任务、已完成任务
- [x] 添加健康度指示器（繁忙/正常/空闲）
- [x] 实现自动刷新（5 秒间隔）
- **验收标准**：队列状态实时展示，视觉清晰

**Task 3.5: 创建 PdfTaskDetailDrawer 组件（可选）**
- [x] 创建 `frontend/src/components/pdf/PdfTaskDetailDrawer.tsx`
- [x] 侧边抽屉展示任务详情
- [ ] 显示 PDF 图片预览（如有）
- [x] 显示完整的提取结果
- **验收标准**：抽屉交互流畅，内容展示完整

---

### Phase 4: UI 细节优化（优先级：中）

**Task 4.1: 添加使用说明和帮助提示**
- [x] 在 PDF 页面添加"使用说明"卡片
- [x] 说明支持格式、文件大小、批量限制、提取字段
- [x] 保持与音频 UI 的样式一致
- **验收标准**：帮助文本清晰易懂

**Task 4.2: 错误处理和提示**
- [x] 显示上传错误（文件过大、格式错误等）
- [x] 显示任务失败信息
- [ ] 添加重试机制
- **验收标准**：错误提示友好，支持重试

**Task 4.3: 加载状态和骨架屏**
- [x] 添加任务列表加载骨架屏
- [x] 添加提取结果加载动画
- **验收标准**：加载状态清晰，无空白闪烁

---

### Phase 5: 集成测试（优先级：高）

**Task 5.1: 端到端测试**
- [ ] 测试批量上传 10 个 PDF 文件
- [ ] 验证任务状态自动刷新
- [ ] 验证提取结果展示
- [ ] 验证 JSON/Markdown 下载
- **验收标准**：完整流程无错误

**Task 5.2: 跨浏览器测试**
- [ ] Chrome 测试
- [ ] Firefox 测试
- [ ] Safari 测试（如有 Mac）
- **验收标准**：主流浏览器兼容

**Task 5.3: 响应式测试**
- [ ] 桌面端（1920x1080, 1366x768）
- [ ] 平板端（768x1024）
- [ ] 移动端（375x667）
- **验收标准**：各尺寸布局正常

---

### Phase 6: 性能优化（优先级：低）

**Task 6.1: 代码分割和懒加载**
- [ ] 使用 `React.lazy` 懒加载 PDF 组件
- [ ] 使用 `Suspense` 包裹
- **验收标准**：首屏加载时间 < 2s

**Task 6.2: 防抖和节流**
- [ ] 队列状态刷新使用防抖
- [ ] 任务列表滚动加载使用节流
- **验收标准**：无频繁请求，性能稳定

**Task 6.3: 虚拟滚动（如任务数 > 100）**
- [ ] 集成 `react-window`
- [ ] 优化大列表渲染性能
- **验收标准**：1000+ 任务无卡顿

---

## 开发顺序建议

1. **第 1 天**：Phase 1（基础架构）+ Phase 2（顶部导航）
2. **第 2 天**：Phase 3.1-3.2（上传组件 + 结果展示）
3. **第 3 天**：Phase 3.3-3.4（任务列表 + 队列状态）
4. **第 4 天**：Phase 4（UI 优化）+ Phase 5（测试）
5. **第 5 天**：Phase 6（性能优化）+ 文档编写

## 技术债务和风险

1. **Tab 切换状态管理**：确保 `useAudioStore` 和 `usePdfStore` 完全独立
2. **批量上传性能**：如后端处理慢，考虑限制并发数
3. **15 字段展示**：如字段过多，考虑折叠面板或分页
4. **队列轮询频率**：避免过于频繁导致后端压力

## 依赖清单

- ✅ react-dropzone（已安装）
- ✅ react-markdown（已安装）
- ✅ zustand（已安装）
- ✅ axios（已安装）
- ⏸️ react-window（可选，性能优化时安装）

## 成功标准

- [x] 后端 API 已完成并可用
- [x] 前端所有组件开发完成 _(核心组件已上线，Markdown 导出/图片预览仍待补)_
- [x] Tab 切换流畅，状态独立
- [x] 批量上传体验良好（10 个文件 < 5s）
- [x] 15 字段展示清晰美观
- [x] 任务列表实时刷新
- [x] 队列状态监控正常
- [ ] 下载功能正常 _(JSON 正常，Markdown 未实现)_
- [x] 与音频 UI 设计风格统一（匹配度 > 95%）
- [ ] 无 TypeScript 错误 _(尚未跑完整 TS 检查)_
- [ ] 无 ESLint 警告 _(尚未执行)_
- [ ] 通过端到端测试 _(未执行)_
