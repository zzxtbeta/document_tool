import React from 'react';
import { useAudioStore } from '../store/useAudioStore';

export const ProgressBar: React.FC = () => {
  const { progress, isUploading, isProcessing, error } = useAudioStore();

  if (!isUploading && !isProcessing && !error && progress === 0) {
    return null;
  }

  const getStatusText = () => {
    if (error) return '处理失败';
    if (progress === 100) return '处理完成！';
    if (progress < 20) return '正在上传...';
    if (progress < 90) return '正在转写和生成纪要...';
    return '即将完成...';
  };

  const getStatusColor = () => {
    if (error) return 'bg-accent-red';
    if (progress === 100) return 'bg-accent-green';
    return 'bg-accent-blue';
  };

  return (
    <div className="w-full space-y-3">
      {/* 进度条 */}
      <div className="w-full bg-primary-200 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ease-out ${getStatusColor()}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 状态文本 */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-primary-600 font-medium">{getStatusText()}</span>
        <span className="text-primary-500">{progress}%</span>
      </div>

      {/* 错误信息 */}
      {error && (
        <div className="mt-2 p-3 bg-red-50 border border-accent-red rounded-lg">
          <p className="text-sm text-accent-red">{error}</p>
        </div>
      )}
    </div>
  );
};
