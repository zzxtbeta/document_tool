import { AudioUploader } from './components/AudioUploader';
import { ProgressBar } from './components/ProgressBar';
import { MarkdownPreview } from './components/MarkdownPreview';
import { AdvancedSettings } from './components/AdvancedSettings';
import { useAudioStore } from './store/useAudioStore';

function App() {
  const { isUploading, isProcessing, error, setAdvancedSettings } = useAudioStore();
  
  const handleSettingsChange = (settings: { asrContext?: string; language?: string }) => {
    setAdvancedSettings(settings);
  };

  return (
    <div className="min-h-screen bg-primary-50">
      {/* Header */}
      <header className="bg-white border-b border-primary-200 shadow-sm">
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
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
            <div>
              <h1 className="text-2xl font-bold text-primary-900">
                音频转写 & 会议纪要生成
              </h1>
              <p className="text-sm text-primary-600 mt-0.5">
                上传音频文件，自动转写并生成结构化会议纪要
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
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
                  <span>处理时间：通常 10-30 秒（取决于音频长度）</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-accent-blue mt-0.5">•</span>
                  <span>生成内容：会议标题、内容总结、关键引用、关键词</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column: Preview */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200 lg:sticky lg:top-8 lg:self-start">
            <h2 className="text-lg font-semibold text-primary-900 mb-4">
              会议纪要预览
            </h2>
            <div className="overflow-y-auto max-h-[calc(100vh-12rem)]">
              <MarkdownPreview />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 py-6 mt-12 border-t border-primary-200">
        <p className="text-center text-sm text-primary-500">
          Powered by DashScope ASR & LLM
        </p>
      </footer>
    </div>
  );
}

export default App;
