import { useState, type FormEvent } from 'react';
import { useAudioStore } from '../store/useAudioStore';

const MODEL_OPTIONS: { label: string; value: 'paraformer-v2' | 'paraformer-8k-v2'; hint?: string }[] = [
  { label: 'paraformer-v2（多语种，推荐）', value: 'paraformer-v2', hint: '支持 language_hints' },
  { label: 'paraformer-8k-v2（电话场景）', value: 'paraformer-8k-v2', hint: '仅中文 8kHz' },
];

export const LongAudioForm = () => {
  const submitLongAudio = useAudioStore((state) => state.submitLongAudio);
  const isSubmittingLong = useAudioStore((state) => state.isSubmittingLong);

  const [fileUrl, setFileUrl] = useState('');
  const [model, setModel] = useState<'paraformer-v2' | 'paraformer-8k-v2'>('paraformer-v2');
  const [languageHints, setLanguageHints] = useState('');
  const [helperText, setHelperText] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!fileUrl.trim()) {
      setFormError('请输入可访问的音频 URL');
      return;
    }

    const hints = languageHints
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    const response = await submitLongAudio({
      fileUrl: fileUrl.trim(),
      model,
      languageHints: hints,
    });

    if (response) {
      setHelperText(
        `已创建长音频任务：${response.data.task_id}（DashScope: ${response.data.dashscope_task_id}）`
      );
      setFormError(null);
      setFileUrl('');
      setLanguageHints('');
    } else {
      setHelperText(null);
      setFormError('创建任务失败，请检查 URL 或稍后重试');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 border border-primary-200">
      <h2 className="text-lg font-semibold text-primary-900 mb-4">长音频 URL 转写</h2>
      <p className="text-sm text-primary-600 mb-4">
        适用于 10 分钟以上的录音。务必提供可公网访问的 HTTP/HTTPS/OSS URL，DashScope 任务结果 24 小时内有效，
        建议在完成后立即下载本地副本。
      </p>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm font-medium text-primary-800">音频 URL*</label>
          <input
            type="url"
            required
            value={fileUrl}
            onChange={(event) => setFileUrl(event.target.value)}
            placeholder="https://example-bucket.oss-cn-hangzhou.aliyuncs.com/audio.m4a"
            className="w-full rounded-lg border border-primary-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-primary-800">选择模型</label>
            <select
              value={model}
              onChange={(event) => setModel(event.target.value as 'paraformer-v2' | 'paraformer-8k-v2')}
              className="w-full rounded-lg border border-primary-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              {MODEL_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-primary-500">
              {MODEL_OPTIONS.find((item) => item.value === model)?.hint}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-primary-800">语言提示（可选，逗号分隔）</label>
            <input
              type="text"
              value={languageHints}
              onChange={(event) => setLanguageHints(event.target.value)}
              placeholder="zh,en"
              className="w-full rounded-lg border border-primary-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              disabled={model === 'paraformer-8k-v2'}
            />
            {model === 'paraformer-8k-v2' && (
              <p className="text-xs text-primary-500">8k 中文模型不支持 language_hints</p>
            )}
          </div>
        </div>

        <div className="rounded-lg bg-primary-50 border border-primary-100 p-3 text-xs text-primary-700">
          <p>DashScope 限制提示：</p>
          <ul className="list-disc pl-4 space-y-1 mt-1">
            <li>一次提交 1-100 个 URL，单文件 ≤ 2GB、时长 ≤ 12h</li>
            <li>任务完成后结果 URL 仅保留 24 小时，请尽快下载本地副本</li>
            <li>排队时间与文件时长、队列长度有关，通常需数分钟</li>
          </ul>
        </div>

        {formError && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {formError}
          </div>
        )}

        {helperText && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-100 rounded-lg px-3 py-2">
            {helperText}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmittingLong}
          className="w-full md:w-auto inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary-900 text-white text-sm font-medium hover:bg-primary-800 disabled:opacity-60"
        >
          {isSubmittingLong ? '提交中…' : '提交长音频任务'}
        </button>
      </form>
    </div>
  );
};
