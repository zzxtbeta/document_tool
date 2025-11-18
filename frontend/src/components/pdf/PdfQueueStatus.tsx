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
        <div className="flex items-center justify-center gap-2">
          <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-primary-900"></div>
          <div className="text-sm text-primary-500">加载队列状态中...</div>
        </div>
      </div>
    );
  }

  const healthColor =
    queueStatus.queue_length > 50
      ? 'text-red-600'
      : queueStatus.queue_length > 20
      ? 'text-yellow-600'
      : 'text-green-600';

  const healthBgColor =
    queueStatus.queue_length > 50
      ? 'bg-red-50'
      : queueStatus.queue_length > 20
      ? 'bg-yellow-50'
      : 'bg-green-50';

  const healthIcon =
    queueStatus.queue_length > 50
      ? '🔴'
      : queueStatus.queue_length > 20
      ? '🟡'
      : '🟢';

  return (
    <div className="bg-white rounded-lg border border-primary-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-primary-900">⚡ 队列状态</h3>
        <div className={`text-xs font-medium px-2 py-1 rounded-full ${healthBgColor} ${healthColor} flex items-center gap-1`}>
          <span>{healthIcon}</span>
          {queueStatus.queue_length > 50
            ? '队列繁忙'
            : queueStatus.queue_length > 20
            ? '队列正常'
            : '队列空闲'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
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

      <div className="space-y-2 pt-4 border-t border-primary-100">
        <div className="flex items-center justify-between text-xs">
          <span className="text-primary-600">并发限制</span>
          <span className="font-medium text-primary-900">{queueStatus.max_workers} 个任务</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-primary-600">队列容量</span>
          <span className="font-medium text-primary-900">{queueStatus.max_queue_size} 个任务</span>
        </div>
      </div>
    </div>
  );
};
