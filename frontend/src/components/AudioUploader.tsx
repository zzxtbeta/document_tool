import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAudioStore } from '../store/useAudioStore';

export const AudioUploader: React.FC = () => {
  const { uploadAudio, isUploading, isProcessing } = useAudioStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      // 文件大小验证（100MB）
      const maxSize = 100 * 1024 * 1024;
      if (file.size > maxSize) {
        alert('文件大小超过 100MB 限制');
        return;
      }

      // 上传
      await uploadAudio(file);
    },
    [uploadAudio]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.m4a', '.mp3', '.wav', '.flac', '.opus', '.aac'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
    multiple: false,
    disabled: isUploading || isProcessing,
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
            : isUploading || isProcessing
            ? 'border-primary-300 bg-primary-50 cursor-not-allowed'
            : 'border-primary-300 hover:border-primary-400 hover:bg-primary-50'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {/* 图标 */}
        <svg
          className={`w-16 h-16 ${
            isDragActive
              ? 'text-accent-blue'
              : isUploading || isProcessing
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
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>

        {/* 文本 */}
        {isDragActive ? (
          <p className="text-lg font-medium text-accent-blue">松开鼠标上传文件...</p>
        ) : isUploading ? (
          <p className="text-lg font-medium text-primary-600">正在上传...</p>
        ) : isProcessing ? (
          <p className="text-lg font-medium text-primary-600">正在处理...</p>
        ) : (
          <>
            <p className="text-lg font-medium text-primary-700">
              拖拽音频文件到此处，或点击选择
            </p>
            <p className="text-sm text-primary-500">
              支持 m4a, mp3, wav, flac, opus, aac 格式
            </p>
            <p className="text-xs text-primary-400">最大文件大小：100MB</p>
          </>
        )}
      </div>
    </div>
  );
};
