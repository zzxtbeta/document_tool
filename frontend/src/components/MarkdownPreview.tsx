import ReactMarkdown from 'react-markdown';
import { useAudioStore } from '../store/useAudioStore';

export const MarkdownPreview: React.FC = () => {
  const { markdownContent, downloadUrl, currentTaskId, isProcessing, processingStats } =
    useAudioStore();

  if (isProcessing) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-900"></div>
      </div>
    );
  }

  if (!markdownContent) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center text-primary-400">
        <svg
          className="w-20 h-20 mb-4 text-primary-300"
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
        <p className="text-lg">上传音频文件后，会议纪要将显示在此处</p>
      </div>
    );
  }

  const handleDownload = () => {
    if (downloadUrl) {
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = ''; // Let server set the filename
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="space-y-4">
      {/* 操作栏 */}
      <div className="flex items-center justify-between pb-4 border-b border-primary-200">
        <div className="text-sm text-primary-600">
          {processingStats && (
            <span>
              处理耗时：{processingStats.total_time.toFixed(2)}s
              <span className="mx-2">|</span>
              转写：{processingStats.transcription_time.toFixed(2)}s
              <span className="mx-2">|</span>
              生成：{processingStats.llm_time.toFixed(2)}s
            </span>
          )}
        </div>
        <button
          onClick={handleDownload}
          disabled={!downloadUrl}
          className="px-4 py-2 bg-primary-900 text-white rounded-lg hover:bg-primary-800 
                     disabled:bg-primary-400 disabled:cursor-not-allowed
                     transition-colors duration-200 flex items-center gap-2"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          下载 Markdown
        </button>
      </div>

      {/* Markdown 内容 */}
      <div className="prose prose-gray max-w-none">
        <ReactMarkdown
          components={{
            h1: ({ ...props }) => (
              <h1 className="text-3xl font-bold text-primary-900 mb-4" {...props} />
            ),
            h2: ({ ...props }) => (
              <h2 className="text-2xl font-semibold text-primary-800 mt-6 mb-3" {...props} />
            ),
            h3: ({ ...props }) => (
              <h3 className="text-xl font-medium text-primary-700 mt-4 mb-2" {...props} />
            ),
            p: ({ ...props }) => (
              <p className="text-primary-700 leading-relaxed mb-4" {...props} />
            ),
            blockquote: ({ ...props }) => (
              <blockquote
                className="border-l-4 border-accent-blue pl-4 italic text-primary-600 my-4"
                {...props}
              />
            ),
            code: ({ ...props }) => (
              <code
                className="bg-primary-100 text-accent-blue px-1.5 py-0.5 rounded text-sm"
                {...props}
              />
            ),
            hr: ({ ...props }) => <hr className="border-primary-300 my-6" {...props} />,
          }}
        >
          {markdownContent}
        </ReactMarkdown>
      </div>

      {/* 任务信息 */}
      {currentTaskId && (
        <div className="mt-6 p-3 bg-primary-50 rounded-lg text-xs text-primary-500">
          任务 ID: {currentTaskId}
        </div>
      )}
    </div>
  );
};
