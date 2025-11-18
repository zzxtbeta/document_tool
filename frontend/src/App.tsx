import { useState } from 'react';
import { AudioUploader } from './components/AudioUploader';
import { ProgressBar } from './components/ProgressBar';
import { MarkdownPreview } from './components/MarkdownPreview';
import { AdvancedSettings } from './components/AdvancedSettings';
import { LongAudioForm } from './components/LongAudioForm';
import { TaskHistoryPanel } from './components/TaskHistoryPanel';
import { TaskDetailDrawer } from './components/TaskDetailDrawer';
import { TabNavigation } from './components/TabNavigation';
import { PdfUploader } from './components/pdf/PdfUploader';
import { PdfExtractionResult } from './components/pdf/PdfExtractionResult';
import { PdfTaskPanel } from './components/pdf/PdfTaskPanel';
import { PdfQueueStatus } from './components/pdf/PdfQueueStatus';
import { useAudioStore } from './store/useAudioStore';
import { usePdfStore } from './store/usePdfStore';

type TabType = 'audio' | 'pdf';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('audio');
  const { isUploading, isProcessing, error, setAdvancedSettings } = useAudioStore();
  
  const handleSettingsChange = (settings: { asrContext?: string; language?: string }) => {
    setAdvancedSettings(settings);
  };

  return (
    <div className="min-h-screen bg-primary-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <svg
              className="w-8 h-8 text-primary-900"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <div>
              <h1 className="text-2xl font-bold text-primary-900">
                智能文档处理平台
              </h1>
              <p className="text-sm text-primary-600 mt-0.5">
                音频转写 & PDF 信息提取
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'audio' ? (
          <AudioContent
            isUploading={isUploading}
            isProcessing={isProcessing}
            error={error}
            handleSettingsChange={handleSettingsChange}
          />
        ) : (
          <PdfContent />
        )}
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 py-6 mt-12 border-t border-primary-200">
        <p className="text-center text-sm text-primary-500">
          Powered by DashScope ASR & LLM + Qwen VL
        </p>
      </footer>

      <TaskDetailDrawer />
    </div>
  );
}

// 音频内容组件
const AudioContent: React.FC<{
  isUploading: boolean;
  isProcessing: boolean;
  error: string | null;
  handleSettingsChange: (settings: { asrContext?: string; language?: string }) => void;
}> = ({ isUploading, isProcessing, error, handleSettingsChange }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Left Column: Upload */}
      <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
              <h2 className="text-lg font-semibold text-primary-900 mb-4">
                上传音频文件
              </h2>
              <AudioUploader />
            </div>

            {/* Advanced Settings */}
            <AdvancedSettings onSettingsChange={handleSettingsChange} />

            {/* Progress */}
            {(isUploading || isProcessing) && (
              <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
                <h2 className="text-lg font-semibold text-primary-900 mb-4">
                  处理进度
                </h2>
                <ProgressBar />
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <svg
                    className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-red-900">
                      处理失败
                    </h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <LongAudioForm />

            {/* Help Section */}
            <div className="bg-accent-blue bg-opacity-5 rounded-xl p-6 border border-accent-blue border-opacity-20">
              <h3 className="text-sm font-semibold text-primary-900 mb-3">
                使用说明
              </h3>
              <ul className="space-y-2 text-sm text-primary-700">
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>支持格式：m4a, mp3, wav, flac, opus, aac</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>文件大小限制：100 MB</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>处理时间：短音频通常 10-30 秒；长音频需等待 DashScope 队列</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>生成内容：会议标题、内容总结、关键引用、关键词</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-6 lg:sticky lg:top-8 lg:self-start">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
              <h2 className="text-lg font-semibold text-primary-900 mb-4">
                会议纪要预览
              </h2>
              <div className="overflow-y-auto max-h-[40vh]">
                <MarkdownPreview />
              </div>
            </div>

            <TaskHistoryPanel />
          </div>
        </div>
      );
    };

    // PDF 内容组件
    const PdfContent = () => {
      const { isUploading, selectedResult, selectedTask, error, clearError } = usePdfStore();

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
                  <svg
                    className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-red-900">处理失败</h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                  <button
                    onClick={clearError}
                    className="text-red-400 hover:text-red-600"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            {/* Help Section */}
            <div className="bg-accent-blue bg-opacity-5 rounded-xl p-6 border border-accent-blue border-opacity-20">
              <h3 className="text-sm font-semibold text-primary-900 mb-3">使用说明</h3>
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
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>处理时间：通常 30-60 秒，取决于 PDF 页数</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-6 lg:sticky lg:top-8 lg:self-start">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
              <h2 className="text-lg font-semibold text-primary-900 mb-4">
                商业计划书受理单
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
