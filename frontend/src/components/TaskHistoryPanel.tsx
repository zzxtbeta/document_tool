import { useEffect, useRef } from 'react';
import { useAudioStore } from '../store/useAudioStore';
import type { LongAudioStatus } from '../types/audio';
import { STATUS_LABEL, STATUS_STYLE } from './taskStatus';

const STATUS_FILTERS: { label: string; value: LongAudioStatus | 'ALL' }[] = [
  { label: '全部状态', value: 'ALL' },
  { label: '排队中', value: 'PENDING' },
  { label: '处理中', value: 'RUNNING' },
  { label: '已完成', value: 'SUCCEEDED' },
  { label: '失败', value: 'FAILED' },
  { label: '已取消', value: 'CANCELED' },
];

export const TaskHistoryPanel = () => {
  const longTasks = useAudioStore((state) => state.longTasks);
  const isLoadingTasks = useAudioStore((state) => state.isLoadingTasks);
  const taskFilters = useAudioStore((state) => state.taskFilters);
  const loadDashScopeTasks = useAudioStore((state) => state.loadDashScopeTasks);
  const refreshLongTask = useAudioStore((state) => state.refreshLongTask);
  const cancelDashScopeTask = useAudioStore((state) => state.cancelDashScopeTask);
  const selectTask = useAudioStore((state) => state.selectTask);
  const setTaskFilters = useAudioStore((state) => state.setTaskFilters);

  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      void loadDashScopeTasks({});
    }
  }, [loadDashScopeTasks]);

  const handleFilterChange = async (status: LongAudioStatus | 'ALL') => {
    const nextFilters = { ...taskFilters, status };
    setTaskFilters(nextFilters);
    await loadDashScopeTasks(nextFilters);
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString();
  };

  const renderTTL = (task: typeof longTasks[number]) => {
    if (!task.remoteResultExpiresAt) return '—';
    const expires = new Date(task.remoteResultExpiresAt).getTime();
    const diffMinutes = Math.floor((expires - Date.now()) / 60000);
    if (diffMinutes <= 0) return '已过期';
    return `${diffMinutes} 分钟`;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-primary-200">
      <div className="flex items-center justify-between px-6 py-4 border-b border-primary-100">
        <div>
          <h2 className="text-lg font-semibold text-primary-900">任务中心</h2>
          <p className="text-sm text-primary-500">长音频任务与 DashScope 队列</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={taskFilters.status || 'ALL'}
            onChange={(event) => handleFilterChange(event.target.value as LongAudioStatus | 'ALL')}
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
            onClick={() => loadDashScopeTasks(taskFilters)}
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
        {!isLoadingTasks && longTasks.length === 0 && (
          <div className="p-6 text-sm text-primary-500">暂无任务</div>
        )}

        {longTasks.map((task) => (
          <div key={task.taskId} className="p-6 flex flex-col gap-3 lg:gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-mono text-primary-700">{task.taskId}</span>
                {task.taskType && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 border border-primary-100">
                    {task.taskType === 'long' ? 'Long' : 'Short'}
                  </span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLE[task.status ?? 'UNKNOWN']}`}>
                  {STATUS_LABEL[task.status ?? 'UNKNOWN']}
                </span>
              </div>
              <div className="text-sm text-primary-600">
                <span className="mr-4">模型：{task.model}</span>
                <span className="mr-4">提交：{formatTimestamp(task.submittedAt)}</span>
                <span>更新：{formatTimestamp(task.updatedAt)}</span>
              </div>
              {task.remoteResultExpiresAt && (
                <div className="text-xs text-primary-500">
                  DashScope TTL：{renderTTL(task)}（过期自动失效）
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => refreshLongTask(task.taskId)}
                className="text-sm px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50"
              >
                刷新状态
              </button>
              <button
                type="button"
                onClick={() => selectTask(task)}
                className="text-sm px-3 py-1.5 rounded-lg bg-primary-900 text-white hover:bg-primary-800"
              >
                查看详情
              </button>
              {task.status === 'PENDING' && (
                <button
                  type="button"
                  onClick={() => cancelDashScopeTask(task.dashscopeTaskId)}
                  className="text-sm px-3 py-1.5 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50"
                >
                  取消任务
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
