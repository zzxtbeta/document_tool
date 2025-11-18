import React, { useEffect, useRef, useState } from 'react';
import { usePdfStore } from '../../store/usePdfStore';
import type { TaskStatus, PdfTask } from '../../types/pdf';
import { PdfTaskDetailDrawer } from './PdfTaskDetailDrawer';

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
  const setTaskFilters = usePdfStore((state) => state.setTaskFilters);

  const [selectedTaskForDetail, setSelectedTaskForDetail] = useState<PdfTask | null>(null);

  const hasFetchedRef = useRef(false);
  const pollIntervalRef = useRef<number | null>(null);

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
        console.log(`🔄 Starting poll for ${activeTasks.length} active tasks`);
        pollIntervalRef.current = setInterval(async () => {
          let hasCompletedTask = false;
          
          for (const task of activeTasks) {
            try {
              const updatedTask = await refreshTask(task.task_id);
              // 检测任务状态变化（从 pending/processing 变为 completed/failed）
              if (updatedTask && 
                  (task.status === 'pending' || task.status === 'processing') &&
                  (updatedTask.status === 'completed' || updatedTask.status === 'failed')) {
                hasCompletedTask = true;
                console.log(`✅ Task ${task.task_id} completed with status: ${updatedTask.status}`);
              }
            } catch (error) {
              console.warn(`Failed to refresh task ${task.task_id}:`, error);
            }
          }

          // 如果有任务完成，重新加载列表以确保数据完整
          if (hasCompletedTask) {
            console.log('🔄 Reloading task list due to completed tasks');
            await loadTasks(taskFilters);
          }
        }, POLL_INTERVAL);
      }
    } else {
      if (pollIntervalRef.current) {
        console.log('⏹️ Stopping poll - no active tasks');
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
  }, [tasks, refreshTask, loadTasks, taskFilters]);

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
            🔄 刷新
          </button>
        </div>
      </div>

      <div className="divide-y divide-primary-100 max-h-[60vh] overflow-y-auto">
        {isLoadingTasks && (
          <div className="p-6 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-900"></div>
            <p className="text-sm text-primary-500 mt-2">加载任务中...</p>
          </div>
        )}
        {!isLoadingTasks && tasks.length === 0 && (
          <div className="p-12 text-center">
            <svg className="w-16 h-16 mx-auto mb-4 text-primary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm text-primary-500">暂无任务记录</p>
          </div>
        )}

        {tasks.map((task) => (
          <div
            key={task.task_id}
            className="p-6 flex flex-col gap-3 lg:gap-2 lg:flex-row lg:items-center lg:justify-between hover:bg-primary-50 transition-colors"
          >
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-primary-900 truncate max-w-xs" title={task.original_filename}>
                  📄 {task.original_filename}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border ${
                    STATUS_STYLE[task.status]
                  }`}
                >
                  {STATUS_LABEL[task.status]}
                </span>
              </div>
              <div className="text-xs text-primary-600 space-y-1">
                <div>
                  <span className="mr-4">📅 创建: {formatTimestamp(task.created_at)}</span>
                  {task.updated_at && (
                    <span>🔄 更新: {formatTimestamp(task.updated_at)}</span>
                  )}
                </div>
                {/* 显示受理单关键信息 */}
                <div className="flex gap-4 flex-wrap">
                  {(task as any).company_name && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">🏭 公司:</span>
                      <span className="text-primary-900">{(task as any).company_name}</span>
                    </span>
                  )}
                  {(task as any).industry && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">🏭 行业:</span>
                      <span className="text-primary-900">{(task as any).industry}</span>
                    </span>
                  )}
                </div>
              </div>
              {task.error && (
                <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded border border-red-200">
                  ❌ {task.error}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => refreshTask(task.task_id)}
                className="text-sm px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition-colors"
              >
                🔄 刷新
              </button>
              {task.status === 'completed' && (
                <>
                  <a
                    href={`/api/v1/pdf/download/${task.task_id}/json`}
                    download
                    className="text-sm px-3 py-1.5 rounded-lg border border-green-200 text-green-700 hover:bg-green-50 transition-colors"
                  >
                    📥 下载JSON
                  </a>
                  <button
                    type="button"
                    onClick={() => setSelectedTaskForDetail(task)}
                    className="text-sm px-3 py-1.5 rounded-lg bg-primary-900 text-white hover:bg-primary-800 transition-colors"
                  >
                    📋 查看受理单
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Task Detail Drawer */}
      <PdfTaskDetailDrawer
        task={selectedTaskForDetail}
        onClose={() => setSelectedTaskForDetail(null)}
      />
    </div>
  );
};
