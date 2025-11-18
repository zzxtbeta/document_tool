import { useState, useEffect } from 'react';
import type { PdfTask } from '../../types/pdf';
import { PdfExtractionCard } from './PdfExtractionCard';
import { getPdfTaskDetail } from '../../services/pdfApi';

interface Props {
  task: PdfTask | null;
  onClose: () => void;
}

const statusStyle: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const statusLabel: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

export const PdfTaskDetailDrawer = ({ task, onClose }: Props) => {
  const [detailTask, setDetailTask] = useState<PdfTask | null>(task);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (task?.task_id) {
      loadTaskDetail(task.task_id);
    }
  }, [task?.task_id]);

  const loadTaskDetail = async (taskId: string) => {
    setIsLoading(true);
    try {
      const detail = await getPdfTaskDetail(taskId);
      console.log('📋 Task detail loaded:', detail);
      console.log('📊 Extracted info:', detail.extracted_info);
      setDetailTask(detail);
    } catch (error) {
      console.error('Failed to load task detail:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!task) return null;

  const status = detailTask?.status || task.status;

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="absolute top-0 right-0 h-full w-full max-w-2xl bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-primary-100 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-primary-900">投资受理单详情</h3>
            <p className="text-xs text-primary-500">任务 ID：{task.task_id}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-primary-500 hover:text-primary-700 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {isLoading && (
            <div className="text-sm text-primary-500">正在加载详情...</div>
          )}

          {/* Status Badge */}
          <div className="flex items-center gap-3">
            <span className={`text-xs px-3 py-1 rounded-full font-medium ${statusStyle[status]}`}>
              {statusLabel[status]}
            </span>
            <span className="text-sm text-primary-700">
              {detailTask?.original_filename || task.original_filename}
            </span>
          </div>

          {/* Basic Info */}
          <section className="rounded-lg border border-primary-100 bg-primary-50/50 p-4 space-y-2">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-primary-900">基本信息</h4>
              {status === 'completed' && (
                <a
                  href={`/api/v1/pdf/download/${task.task_id}/json`}
                  download
                  className="text-xs px-3 py-1 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors"
                >
                  📥 下载 JSON
                </a>
              )}
            </div>
            <div className="text-sm space-y-1">
              <p className="text-primary-700">
                <span className="text-primary-500">提交时间：</span>
                {new Date(task.created_at).toLocaleString('zh-CN')}
              </p>
              {detailTask?.submitted_at && (
                <p className="text-primary-700">
                  <span className="text-primary-500">开始处理：</span>
                  {new Date(detailTask.submitted_at).toLocaleString('zh-CN')}
                </p>
              )}
              {detailTask?.completed_at && (
                <p className="text-primary-700">
                  <span className="text-primary-500">完成时间：</span>
                  {new Date(detailTask.completed_at).toLocaleString('zh-CN')}
                </p>
              )}
            </div>
          </section>

          {/* Extraction Result */}
          {(() => {
            console.log('🔍 Render check:', {
              status,
              hasDetailTask: !!detailTask,
              hasExtractedInfo: !!detailTask?.extracted_info,
              extractedInfo: detailTask?.extracted_info
            });
            return null;
          })()}
          {status === 'completed' && detailTask?.extracted_info && (
            <PdfExtractionCard
              extractionResult={detailTask.extracted_info}
              error={detailTask.error}
            />
          )}

          {status === 'failed' && detailTask?.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <h4 className="text-sm font-semibold text-red-900 mb-2">错误信息</h4>
              <p className="text-sm text-red-700 whitespace-pre-wrap">{detailTask.error}</p>
            </div>
          )}

          {status === 'processing' && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
              <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mb-2" />
              <p className="text-sm text-blue-700">正在处理中，请稍候...</p>
            </div>
          )}

          {status === 'pending' && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
              <p className="text-sm text-yellow-700">任务已提交，等待处理...</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-primary-100 px-6 py-4 flex justify-between items-center">
          <button
            type="button"
            onClick={() => task.task_id && loadTaskDetail(task.task_id)}
            disabled={isLoading}
            className="text-sm px-4 py-2 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition-colors disabled:opacity-50"
          >
            🔄 刷新
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 rounded-lg bg-primary-900 text-white hover:bg-primary-800 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
