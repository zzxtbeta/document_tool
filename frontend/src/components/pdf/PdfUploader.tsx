import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { usePdfStore } from '../../store/usePdfStore';

export const PdfUploader: React.FC = () => {
  const { uploadPdfs, isUploading, uploadProgress } = usePdfStore();

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
    <div className="space-y-4">
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

      {/* 上传进度条 */}
      {isUploading && (
        <div className="bg-white rounded-lg border border-primary-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-primary-700">上传中...</span>
            <span className="text-sm text-primary-600">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-primary-100 rounded-full h-2">
            <div
              className="bg-accent-blue h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        </div>
      )}
    </div>
  );
};
