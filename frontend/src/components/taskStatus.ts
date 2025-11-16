import type { LongAudioStatus } from '../types/audio';

export const STATUS_LABEL: Record<LongAudioStatus, string> = {
  PENDING: '排队中',
  RUNNING: '处理中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  UNKNOWN: '未知',
  CANCELED: '已取消',
};

export const STATUS_STYLE: Record<LongAudioStatus, string> = {
  PENDING: 'bg-amber-50 text-amber-700 border border-amber-100',
  RUNNING: 'bg-sky-50 text-sky-700 border border-sky-100',
  SUCCEEDED: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  FAILED: 'bg-rose-50 text-rose-700 border border-rose-100',
  UNKNOWN: 'bg-gray-100 text-gray-600 border border-gray-200',
  CANCELED: 'bg-gray-100 text-gray-600 border border-gray-200',
};
