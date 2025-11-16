import { useState } from 'react';

interface AdvancedSettingsProps {
  onSettingsChange: (settings: {
    asrContext?: string;
    language?: string;
  }) => void;
}

export const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({
  onSettingsChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [asrContext, setAsrContext] = useState('');
  const [language, setLanguage] = useState('');

  const handleAsrContextChange = (value: string) => {
    setAsrContext(value);
    onSettingsChange({ asrContext: value || undefined, language: language || undefined });
  };

  const handleLanguageChange = (value: string) => {
    setLanguage(value);
    onSettingsChange({ asrContext: asrContext || undefined, language: value || undefined });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <h2 className="text-lg font-semibold text-primary-900 flex items-center gap-2">
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
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          高级设置
        </h2>
        <svg
          className={`w-5 h-5 text-primary-600 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="mt-6 space-y-4">
          {/* Language Selection */}
          <div>
            <label
              htmlFor="language"
              className="block text-sm font-medium text-primary-700 mb-2"
            >
              音频语种（可选）
            </label>
            <select
              id="language"
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              className="w-full px-3 py-2 border border-primary-300 rounded-lg
                         focus:ring-2 focus:ring-accent-blue focus:border-accent-blue
                         text-primary-900 bg-white"
            >
              <option value="">自动检测</option>
              <option value="zh">中文</option>
              <option value="en">英文</option>
              <option value="ja">日语</option>
              <option value="ko">韩语</option>
            </select>
            <p className="mt-1 text-xs text-primary-500">
              指定语种可提升识别准确率，不指定则自动检测
            </p>
          </div>

          {/* ASR Context */}
          <div>
            <label
              htmlFor="asrContext"
              className="block text-sm font-medium text-primary-700 mb-2"
            >
              专业术语提示（可选）
            </label>
            <textarea
              id="asrContext"
              value={asrContext}
              onChange={(e) => handleAsrContextChange(e.target.value)}
              rows={3}
              placeholder="例如：本次讨论涉及医学术语，如CT、核磁共振、血常规等"
              className="w-full px-3 py-2 border border-primary-300 rounded-lg
                         focus:ring-2 focus:ring-accent-blue focus:border-accent-blue
                         text-primary-900 resize-none"
            />
            <p className="mt-1 text-xs text-primary-500">
              输入专业领域的术语提示，帮助模型更准确识别特定词汇
            </p>
          </div>

          {/* Examples */}
          <div className="mt-4 p-3 bg-primary-50 rounded-lg">
            <h4 className="text-xs font-semibold text-primary-700 mb-2">
              💡 使用示例
            </h4>
            <ul className="text-xs text-primary-600 space-y-1">
              <li>
                <strong>医疗：</strong>
                "讨论涉及医学术语，如CT、核磁共振、血常规、心电图等"
              </li>
              <li>
                <strong>金融：</strong>
                "内容包含投资术语，如PE、IRR、估值、尽调等"
              </li>
              <li>
                <strong>技术：</strong>
                "涉及技术术语，如API、RESTful、微服务、Kubernetes等"
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
