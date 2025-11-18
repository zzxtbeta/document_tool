# PDF 商业计划书提取 UI 界面技术设计

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   浏览器 (Browser)                    │
│  ┌──────────────────────────────────────────────┐   │
│  │          React UI (TypeScript)               │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  Tab Navigation (音频 / PDF 切换)       │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  PDF 上传区 (react-dropzone)           │  │   │
│  │  │  - 批量拖拽上传 (最多 10 个)             │  │   │
│  │  │  - 进度显示                             │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  提取结果展示                           │  │   │
│  │  │  - 15 字段卡片布局                      │  │   │
│  │  │  - Markdown 渲染                       │  │   │
│  │  │  - JSON/MD 文件下载                    │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  任务中心                               │  │   │
│  │  │  - 历史任务列表                         │  │   │
│  │  │  - 状态过滤                             │  │   │
│  │  │  - 队列状态监控                         │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │ HTTP/REST
                        ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (已完成)                │
│  ┌──────────────────────────────────────────────┐   │
│  │  PDF API 路由 (api/pdf/routes.py)            │   │
│  │  - POST /api/v1/pdf/extract                 │   │
│  │  - POST /api/v1/pdf/extract/batch           │   │
│  │  - GET  /api/v1/pdf/extract/{task_id}      │   │
│  │  - GET  /api/v1/pdf/extract (列表查询)       │   │
│  │  - GET  /api/v1/pdf/queue/status           │   │
│  │  - GET  /api/v1/pdf/download/{task_id}     │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  PDFExtractionService (已完成)              │   │
│  │  - AsyncTaskQueue (5 并发)                  │   │
│  │  - Qwen3-VL-Flash (response_format)        │   │
│  │  - pdf2image + OSS 存储                     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 前端设计

### 顶部导航设计

#### 1. TabNavigation.tsx（顶部 Tab 切换）

```typescript
import React from 'react';

type TabType = 'audio' | 'pdf';

interface TabNavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange,
}) => {
  const tabs = [
    {
      id: 'audio' as const,
      label: '音频转写',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
      ),
      description: '会议纪要生成',
    },
    {
      id: 'pdf' as const,
      label: 'PDF 提取',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      description: '商业计划书信息提取',
    },
  ];

  return (
    <div className="border-b border-primary-200 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-3 py-4 border-b-2 transition-all
                ${
                  activeTab === tab.id
                    ? 'border-primary-900 text-primary-900'
                    : 'border-transparent text-primary-600 hover:text-primary-900 hover:border-primary-300'
                }
              `}
            >
              <div className={activeTab === tab.id ? 'text-primary-900' : 'text-primary-500'}>
                {tab.icon}
              </div>
              <div className="text-left">
                <div className="font-semibold text-sm">{tab.label}</div>
                <div className="text-xs text-primary-500">{tab.description}</div>
              </div>
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
};
```

### PDF 核心组件设计

#### 2. PdfUploader.tsx（拖拽上传组件）

```typescript
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { usePdfStore } from '../../store/usePdfStore';

export const PdfUploader: React.FC = () => {
  const { uploadPdfs, isUploading } = usePdfStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      // 批量上传限制：最多 10 个
      if (acceptedFiles.length > 10) {
        alert('一次最多上传 10 个 PDF 文件');
        return;
      }

      // 文件大小验证（每个文件 50MB）
      const maxSize = 50 * 1024 * 1024;
      const oversizedFiles = acceptedFiles.filter((f) => f.size > maxSize);
      if (oversizedFiles.length > 0) {
        alert(`以下文件超过 50MB 限制：\n${oversizedFiles.map((f) => f.name).join('\n')}`);
        return;
      }

      // 批量上传
      await uploadPdfs(acceptedFiles);
    },
    [uploadPdfs]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true,
    maxFiles: 10,
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center
        transition-all duration-200 cursor-pointer
        ${
          isDragActive
            ? 'border-accent-blue bg-blue-50 scale-105'
            : isUploading
            ? 'border-primary-300 bg-primary-50 cursor-not-allowed'
            : 'border-primary-300 hover:border-primary-400 hover:bg-primary-50'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {/* PDF 图标 */}
        <svg
          className={`w-16 h-16 ${
            isDragActive
              ? 'text-accent-blue'
              : isUploading
              ? 'text-primary-400'
              : 'text-primary-500'
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>

        {/* 文本 */}
        {isDragActive ? (
          <p className="text-lg font-medium text-accent-blue">松开鼠标上传文件...</p>
        ) : isUploading ? (
          <p className="text-lg font-medium text-primary-600">正在上传...</p>
        ) : (
          <>
            <p className="text-lg font-medium text-primary-700">
              拖拽 PDF 文件到此处，或点击选择
            </p>
            <p className="text-sm text-primary-500">支持批量上传，一次最多 10 个文件</p>
            <p className="text-xs text-primary-400">单个文件最大 50MB</p>
          </>
        )}

        {/* 错误提示 */}
        {fileRejections.length > 0 && (
          <div className="mt-2 text-sm text-red-600">
            {fileRejections.map(({ file, errors }) => (
              <div key={file.name}>
                {file.name}: {errors.map((e) => e.message).join(', ')}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
```

#### 3. PdfExtractionResult.tsx（15 字段卡片展示）

```typescript
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { usePdfStore } from '../../store/usePdfStore';
import type { ExtractionResult } from '../../types/pdf';

// 15 个字段的配置
const FIELD_CONFIG = [
  { key: 'company_name', label: '公司名称', icon: '🏢' },
  { key: 'established_date', label: '成立时间', icon: '📅' },
  { key: 'registered_capital', label: '注册资本', icon: '💰' },
  { key: 'legal_representative', label: '法定代表人', icon: '👤' },
  { key: 'business_scope', label: '经营范围', icon: '📋', expandable: true },
  { key: 'main_products_services', label: '主营业务', icon: '🛒', expandable: true },
  { key: 'target_market', label: '目标市场', icon: '🎯', expandable: true },
  { key: 'competitive_advantage', label: '竞争优势', icon: '🚀', expandable: true },
  { key: 'revenue', label: '营业收入', icon: '💵' },
  { key: 'profit', label: '利润', icon: '📈' },
  { key: 'assets', label: '资产', icon: '🏦' },
  { key: 'liabilities', label: '负债', icon: '📉' },
  { key: 'funding_amount', label: '融资金额', icon: '💸' },
  { key: 'funding_purpose', label: '融资用途', icon: '🎨', expandable: true },
  { key: 'team_info', label: '团队信息', icon: '👥', expandable: true },
];

interface PdfExtractionResultProps {
  result: ExtractionResult | null;
  taskId?: string;
}

export const PdfExtractionResult: React.FC<PdfExtractionResultProps> = ({
  result,
  taskId,
}) => {
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const { downloadFile } = usePdfStore();

  if (!result) {
    return (
      <div className="text-center text-primary-400 py-12">
        上传 PDF 文件后，提取结果将显示在此处
      </div>
    );
  }

  const toggleExpand = (key: string) => {
    const newExpanded = new Set(expandedFields);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedFields(newExpanded);
  };

  const renderField = (field: typeof FIELD_CONFIG[number]) => {
    const value = result[field.key as keyof ExtractionResult];
    const isExpanded = expandedFields.has(field.key);
    const shouldTruncate = field.expandable && typeof value === 'string' && value.length > 200;

    return (
      <div
        key={field.key}
        className="bg-white rounded-lg border border-primary-200 p-4 hover:shadow-md transition-shadow"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{field.icon}</span>
            <h3 className="text-sm font-semibold text-primary-900">{field.label}</h3>
          </div>
          {shouldTruncate && (
            <button
              onClick={() => toggleExpand(field.key)}
              className="text-xs text-accent-blue hover:underline"
            >
              {isExpanded ? '收起' : '展开'}
            </button>
          )}
        </div>

        <div className="text-sm text-primary-700">
          {value ? (
            typeof value === 'string' ? (
              <div
                className={`prose prose-sm max-w-none ${
                  shouldTruncate && !isExpanded ? 'line-clamp-3' : ''
                }`}
              >
                <ReactMarkdown>{value}</ReactMarkdown>
              </div>
            ) : (
              <pre className="text-xs bg-primary-50 p-2 rounded overflow-x-auto">
                {JSON.stringify(value, null, 2)}
              </pre>
            )
          ) : (
            <span className="text-primary-400 italic">未提取到信息</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* 下载按钮 */}
      <div className="flex items-center justify-between bg-primary-50 rounded-lg p-4 border border-primary-200">
        <div>
          <h3 className="text-sm font-semibold text-primary-900">提取结果</h3>
          <p className="text-xs text-primary-600">共 15 个字段</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => taskId && downloadFile(taskId, 'json')}
            className="px-4 py-2 bg-white border border-primary-300 text-primary-700 rounded-lg hover:bg-primary-50 text-sm"
          >
            下载 JSON
          </button>
          <button
            onClick={() => taskId && downloadFile(taskId, 'markdown')}
            className="px-4 py-2 bg-primary-900 text-white rounded-lg hover:bg-primary-800 text-sm"
          >
            下载 Markdown
          </button>
        </div>
      </div>

      {/* 15 字段卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FIELD_CONFIG.map(renderField)}
      </div>
    </div>
  );
};
```

#### 4. PdfTaskPanel.tsx（任务列表）

```typescript
import React, { useEffect, useRef } from 'react';
import { usePdfStore } from '../../store/usePdfStore';
import type { TaskStatus } from '../../types/pdf';

const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

const STATUS_STYLE: Record<TaskStatus, string> = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  processing: 'bg-blue-50 text-blue-700 border-blue-200',
  completed: 'bg-green-50 text-green-700 border-green-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
};

const STATUS_FILTERS: { label: string; value: TaskStatus | 'all' }[] = [
  { label: '全部状态', value: 'all' },
  { label: '排队中', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
];

const POLL_INTERVAL = 3000; // 3秒轮询

export const PdfTaskPanel: React.FC = () => {
  const tasks = usePdfStore((state) => state.tasks);
  const isLoadingTasks = usePdfStore((state) => state.isLoadingTasks);
  const taskFilters = usePdfStore((state) => state.taskFilters);
  const loadTasks = usePdfStore((state) => state.loadTasks);
  const refreshTask = usePdfStore((state) => state.refreshTask);
  const selectTask = usePdfStore((state) => state.selectTask);
  const setTaskFilters = usePdfStore((state) => state.setTaskFilters);

  const hasFetchedRef = useRef(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 初始加载任务列表
  useEffect(() => {
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      void loadTasks({});
    }
  }, [loadTasks]);

  // 自动轮询未完成的任务
  useEffect(() => {
    const activeTasks = tasks.filter(
      (task) => task.status === 'pending' || task.status === 'processing'
    );

    if (activeTasks.length > 0) {
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(async () => {
          for (const task of activeTasks) {
            try {
              await refreshTask(task.task_id);
            } catch (error) {
              console.warn(`Failed to refresh task ${task.task_id}:`, error);
            }
          }
        }, POLL_INTERVAL);
      }
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [tasks, refreshTask]);

  const handleFilterChange = async (status: TaskStatus | 'all') => {
    const nextFilters = { ...taskFilters, status: status === 'all' ? undefined : status };
    setTaskFilters(nextFilters);
    await loadTasks(nextFilters);
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-primary-200">
      <div className="flex items-center justify-between px-6 py-4 border-b border-primary-100">
        <div>
          <h2 className="text-lg font-semibold text-primary-900">任务中心</h2>
          <p className="text-sm text-primary-500">PDF 提取任务历史记录</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={taskFilters.status || 'all'}
            onChange={(e) => handleFilterChange(e.target.value as TaskStatus | 'all')}
            className="rounded-lg border border-primary-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          >
            {STATUS_FILTERS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => loadTasks(taskFilters)}
            className="inline-flex items-center rounded-lg border border-primary-200 px-3 py-1.5 text-sm text-primary-700 hover:bg-primary-50"
            disabled={isLoadingTasks}
          >
            刷新
          </button>
        </div>
      </div>

      <div className="divide-y divide-primary-100 max-h-[60vh] overflow-y-auto">
        {isLoadingTasks && (
          <div className="p-6 text-sm text-primary-500">加载任务中...</div>
        )}
        {!isLoadingTasks && tasks.length === 0 && (
          <div className="p-6 text-sm text-primary-500">暂无任务</div>
        )}

        {tasks.map((task) => (
          <div
            key={task.task_id}
            className="p-6 flex flex-col gap-3 lg:gap-2 lg:flex-row lg:items-center lg:justify-between hover:bg-primary-50 transition-colors"
          >
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-primary-900 truncate max-w-xs">
                  {task.original_filename}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border ${
                    STATUS_STYLE[task.status]
                  }`}
                >
                  {STATUS_LABEL[task.status]}
                </span>
              </div>
              <div className="text-sm text-primary-600">
                <span className="mr-4">任务 ID: {task.task_id}</span>
                <span>创建时间: {formatTimestamp(task.created_at)}</span>
              </div>
              {task.error && (
                <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                  错误: {task.error}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => refreshTask(task.task_id)}
                className="text-sm px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50"
              >
                刷新状态
              </button>
              {task.status === 'completed' && (
                <button
                  type="button"
                  onClick={() => selectTask(task)}
                  className="text-sm px-3 py-1.5 rounded-lg bg-primary-900 text-white hover:bg-primary-800"
                >
                  查看结果
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

#### 5. PdfQueueStatus.tsx（队列状态监控）

```typescript
import React, { useEffect } from 'react';
import { usePdfStore } from '../../store/usePdfStore';

export const PdfQueueStatus: React.FC = () => {
  const queueStatus = usePdfStore((state) => state.queueStatus);
  const loadQueueStatus = usePdfStore((state) => state.loadQueueStatus);

  useEffect(() => {
    // 初始加载
    void loadQueueStatus();

    // 每 5 秒刷新一次
    const interval = setInterval(() => {
      void loadQueueStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [loadQueueStatus]);

  if (!queueStatus) {
    return (
      <div className="bg-white rounded-lg border border-primary-200 p-4">
        <div className="text-sm text-primary-500">加载队列状态中...</div>
      </div>
    );
  }

  const healthColor =
    queueStatus.queue_length > 50
      ? 'text-red-600'
      : queueStatus.queue_length > 20
      ? 'text-yellow-600'
      : 'text-green-600';

  return (
    <div className="bg-white rounded-lg border border-primary-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-primary-900">队列状态</h3>
        <div className={`text-xs font-medium ${healthColor}`}>
          {queueStatus.queue_length > 50
            ? '队列繁忙'
            : queueStatus.queue_length > 20
            ? '队列正常'
            : '队列空闲'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-900">
            {queueStatus.queue_length}
          </div>
          <div className="text-xs text-primary-500 mt-1">队列长度</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-accent-blue">
            {queueStatus.active_tasks}
          </div>
          <div className="text-xs text-primary-500 mt-1">活跃任务</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-accent-green">
            {queueStatus.completed_tasks}
          </div>
          <div className="text-xs text-primary-500 mt-1">已完成</div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-primary-100">
        <div className="flex items-center justify-between text-xs">
          <span className="text-primary-600">并发限制</span>
          <span className="font-medium text-primary-900">5 个任务</span>
        </div>
        <div className="flex items-center justify-between text-xs mt-2">
          <span className="text-primary-600">队列容量</span>
          <span className="font-medium text-primary-900">100 个任务</span>
        </div>
      </div>
    </div>
  );
};
```

### 状态管理设计

#### 6. usePdfStore.ts（Zustand 状态管理）

```typescript
import { create } from 'zustand';
import { pdfApi } from '../services/pdfApi';
import type { PdfTask, ExtractionResult, QueueStatus, TaskStatus } from '../types/pdf';

interface PdfState {
  // 上传状态
  isUploading: boolean;
  uploadProgress: number;

  // 任务列表
  tasks: PdfTask[];
  isLoadingTasks: boolean;
  taskFilters: { status?: TaskStatus; page?: number; page_size?: number };

  // 当前选中的任务
  selectedTask: PdfTask | null;
  selectedResult: ExtractionResult | null;

  // 队列状态
  queueStatus: QueueStatus | null;

  // 错误
  error: string | null;

  // Actions
  uploadPdfs: (files: File[]) => Promise<void>;
  loadTasks: (filters: PdfState['taskFilters']) => Promise<void>;
  refreshTask: (taskId: string) => Promise<void>;
  selectTask: (task: PdfTask) => Promise<void>;
  loadQueueStatus: () => Promise<void>;
  downloadFile: (taskId: string, fileType: 'json' | 'markdown') => void;
  setTaskFilters: (filters: PdfState['taskFilters']) => void;
  clearError: () => void;
}

export const usePdfStore = create<PdfState>((set, get) => ({
  isUploading: false,
  uploadProgress: 0,
  tasks: [],
  isLoadingTasks: false,
  taskFilters: { page: 1, page_size: 20 },
  selectedTask: null,
  selectedResult: null,
  queueStatus: null,
  error: null,

  uploadPdfs: async (files) => {
    set({ isUploading: true, error: null, uploadProgress: 0 });

    try {
      // 批量上传
      const response = await pdfApi.uploadBatch(files, (progress) => {
        set({ uploadProgress: progress });
      });

      // 添加到任务列表
      set((state) => ({
        tasks: [...response.task_ids.map((id) => ({ task_id: id, status: 'pending' as TaskStatus })), ...state.tasks],
        isUploading: false,
        uploadProgress: 100,
      }));

      // 刷新任务列表
      await get().loadTasks(get().taskFilters);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '上传失败',
        isUploading: false,
        uploadProgress: 0,
      });
    }
  },

  loadTasks: async (filters) => {
    set({ isLoadingTasks: true, error: null });

    try {
      const response = await pdfApi.listTasks(filters);
      set({ tasks: response.tasks, isLoadingTasks: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '加载任务失败',
        isLoadingTasks: false,
      });
    }
  },

  refreshTask: async (taskId) => {
    try {
      const task = await pdfApi.getTaskStatus(taskId);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.task_id === taskId ? task : t)),
      }));
    } catch (error) {
      console.warn('刷新任务失败:', error);
    }
  },

  selectTask: async (task) => {
    set({ selectedTask: task, selectedResult: null });

    if (task.status === 'completed') {
      try {
        const fullTask = await pdfApi.getTaskStatus(task.task_id);
        set({ selectedResult: fullTask.result });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : '加载结果失败' });
      }
    }
  },

  loadQueueStatus: async () => {
    try {
      const status = await pdfApi.getQueueStatus();
      set({ queueStatus: status });
    } catch (error) {
      console.warn('加载队列状态失败:', error);
    }
  },

  downloadFile: (taskId, fileType) => {
    const url = pdfApi.getDownloadUrl(taskId, fileType);
    window.open(url, '_blank');
  },

  setTaskFilters: (filters) => {
    set({ taskFilters: filters });
  },

  clearError: () => {
    set({ error: null });
  },
}));
```

### API 客户端设计

#### 7. pdfApi.ts（API 客户端）

```typescript
import axios from 'axios';
import type { PdfTask, ExtractionResult, QueueStatus, TaskStatus } from '../types/pdf';

const API_BASE = '/api/v1/pdf';

export const pdfApi = {
  /**
   * 单个 PDF 上传
   */
  async uploadSingle(file: File): Promise<PdfTask> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(`${API_BASE}/extract`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  },

  /**
   * 批量 PDF 上传
   */
  async uploadBatch(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<{ task_ids: string[]; total_files: number }> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post(`${API_BASE}/extract/batch`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  /**
   * 查询任务状态
   */
  async getTaskStatus(taskId: string): Promise<PdfTask> {
    const response = await axios.get(`${API_BASE}/extract/${taskId}`);
    return response.data;
  },

  /**
   * 列表查询
   */
  async listTasks(filters: {
    status?: TaskStatus;
    page?: number;
    page_size?: number;
  }): Promise<{ tasks: PdfTask[]; total: number; page: number; page_size: number }> {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const response = await axios.get(`${API_BASE}/extract?${params.toString()}`);
    return response.data;
  },

  /**
   * 获取队列状态
   */
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await axios.get(`${API_BASE}/queue/status`);
    return response.data;
  },

  /**
   * 获取下载 URL
   */
  getDownloadUrl(taskId: string, fileType: 'json' | 'markdown'): string {
    return `${API_BASE}/download/${taskId}/${fileType}`;
  },
};
```

### TypeScript 类型定义

#### 8. pdf.ts（类型定义）

```typescript
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExtractionResult {
  company_name: string;
  established_date: string;
  registered_capital: string;
  legal_representative: string;
  business_scope: string;
  main_products_services: string;
  target_market: string;
  competitive_advantage: string;
  revenue: string;
  profit: string;
  assets: string;
  liabilities: string;
  funding_amount: string;
  funding_purpose: string;
  team_info: string;
}

export interface PdfTask {
  task_id: string;
  original_filename: string;
  status: TaskStatus;
  created_at: string;
  updated_at?: string;
  pdf_url?: string;
  images?: string[];
  result?: ExtractionResult;
  error?: string;
}

export interface QueueStatus {
  queue_length: number;
  active_tasks: number;
  completed_tasks: number;
  max_workers: number;
  max_queue_size: number;
}
```

## 主应用集成

### App.tsx 修改

```typescript
import { useState } from 'react';
import { TabNavigation } from './components/TabNavigation';
import { AudioUploader } from './components/AudioUploader';
import { PdfUploader } from './components/pdf/PdfUploader';
import { PdfExtractionResult } from './components/pdf/PdfExtractionResult';
import { PdfTaskPanel } from './components/pdf/PdfTaskPanel';
import { PdfQueueStatus } from './components/pdf/PdfQueueStatus';
import { useAudioStore } from './store/useAudioStore';
import { usePdfStore } from './store/usePdfStore';

type TabType = 'audio' | 'pdf';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('audio');

  return (
    <div className="min-h-screen bg-primary-50">
      {/* Header */}
      <header className="bg-white border-b border-primary-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-primary-900">
            智能文档处理平台
          </h1>
          <p className="text-sm text-primary-600 mt-0.5">
            音频转写 & PDF 信息提取
          </p>
        </div>
      </header>

      {/* Tab Navigation */}
      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'audio' ? (
          <AudioContent />
        ) : (
          <PdfContent />
        )}
      </main>
    </div>
  );
}

// 音频内容组件（现有逻辑）
const AudioContent = () => {
  // ... 现有音频 UI 逻辑
};

// PDF 内容组件（新增）
const PdfContent = () => {
  const { isUploading, selectedResult, selectedTask, error } = usePdfStore();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Left Column: Upload */}
      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
          <h2 className="text-lg font-semibold text-primary-900 mb-4">
            上传 PDF 文件
          </h2>
          <PdfUploader />
        </div>

        {/* Queue Status */}
        <PdfQueueStatus />

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-red-900">处理失败</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Help Section */}
        <div className="bg-accent-blue bg-opacity-5 rounded-xl p-6 border border-accent-blue border-opacity-20">
          <h3 className="text-sm font-semibold text-primary-900 mb-3">
            使用说明
          </h3>
          <ul className="space-y-2 text-sm text-primary-700">
            <li className="flex items-start gap-2">
              <span className="text-accent-blue mt-0.5">•</span>
              <span>支持格式：PDF</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent-blue mt-0.5">•</span>
              <span>文件大小限制：单个 50 MB</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent-blue mt-0.5">•</span>
              <span>批量上传：一次最多 10 个文件</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent-blue mt-0.5">•</span>
              <span>提取字段：公司信息、财务数据、业务描述等 15 个字段</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Right Column */}
      <div className="space-y-6 lg:sticky lg:top-8 lg:self-start">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
          <h2 className="text-lg font-semibold text-primary-900 mb-4">
            提取结果预览
          </h2>
          <div className="overflow-y-auto max-h-[60vh]">
            <PdfExtractionResult
              result={selectedResult}
              taskId={selectedTask?.task_id}
            />
          </div>
        </div>

        <PdfTaskPanel />
      </div>
    </div>
  );
};

export default App;
```

## 部署和测试

### 开发环境

```bash
# 前端
cd frontend
npm install           # 安装依赖
npm run dev           # 启动开发服务器

# 后端（已完成）
cd ..
uvicorn api.main:app --reload --port 8000
```

### 集成测试

1. **Tab 切换测试**：验证音频和 PDF 页面切换时状态保持
2. **批量上传测试**：上传 10 个 PDF 文件，验证进度条和任务创建
3. **队列状态测试**：验证队列状态实时更新
4. **任务轮询测试**：验证处理中任务自动刷新
5. **结果展示测试**：验证 15 个字段卡片渲染正确
6. **下载测试**：验证 JSON 和 Markdown 文件下载

## 性能优化

1. **虚拟滚动**：任务列表超过 100 项时使用 `react-window`
2. **懒加载**：PDF 预览组件使用 `React.lazy`
3. **防抖节流**：队列状态刷新使用防抖
4. **缓存策略**：已完成任务结果缓存在 `localStorage`

## 安全考虑

1. **文件验证**：前端和后端双重验证文件类型和大小
2. **XSS 防护**：使用 `react-markdown` 自动转义
3. **CSRF 保护**：FastAPI 内置 CSRF 中间件
4. **速率限制**：后端限制每用户每分钟 10 次上传

## 未来扩展

1. **PDF 预览**：集成 PDF.js 在线预览
2. **字段编辑**：支持在线编辑提取结果
3. **导出功能**：支持导出为 Excel、Word
4. **OCR 支持**：扫描件 PDF 自动 OCR
5. **批量导出**：一键导出所有任务结果
