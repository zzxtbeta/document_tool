import type { MeetingMinutes } from '../types/audio';

interface Props {
  meetingMinutes?: MeetingMinutes | null;
  markdownPath?: string | null;
  transcriptionText?: string | null;
  minutesGeneratedAt?: string | null;
  minutesError?: string | null;
}

export const MeetingMinutesCard = ({
  meetingMinutes,
  markdownPath,
  transcriptionText,
  minutesGeneratedAt,
  minutesError,
}: Props) => {
  if (minutesError) {
    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-rose-600">会议纪要生成失败</h4>
        <p className="text-xs text-rose-500 whitespace-pre-wrap">{minutesError}</p>
      </div>
    );
  }

  if (!meetingMinutes) {
    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-primary-900">会议纪要</h4>
        <p className="text-xs text-primary-500">纪要生成中，请稍后刷新查看。</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-sm font-semibold text-primary-900">会议纪要</h4>
        {minutesGeneratedAt && (
          <p className="text-xs text-primary-500">生成时间：{minutesGeneratedAt}</p>
        )}
      </div>

      <div className="rounded-lg border border-primary-100 bg-primary-50/60 px-3 py-2 space-y-2">
        <div>
          <p className="text-xs text-primary-500">标题</p>
          <p className="text-sm font-semibold text-primary-900">{meetingMinutes.title}</p>
        </div>

        <div>
          <p className="text-xs text-primary-500">主要内容</p>
          <p className="text-sm whitespace-pre-wrap text-primary-800">
            {meetingMinutes.content}
          </p>
        </div>

        {meetingMinutes.key_quotes?.length ? (
          <div>
            <p className="text-xs text-primary-500">关键引述</p>
            <ul className="text-sm list-disc pl-4 space-y-1">
              {meetingMinutes.key_quotes.map((quote, index) => (
                <li key={`${quote}-${index}`} className="text-primary-800">
                  {quote}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {meetingMinutes.keywords?.length ? (
          <div>
            <p className="text-xs text-primary-500">关键词</p>
            <div className="flex flex-wrap gap-2">
              {meetingMinutes.keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="inline-flex items-center rounded-full border border-primary-200 bg-white/80 px-2 py-0.5 text-xs text-primary-700"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {markdownPath ? (
          <div>
            <p className="text-xs text-primary-500">Markdown 路径</p>
            <code className="block rounded bg-white/70 px-2 py-1 text-xs text-primary-800 break-all">
              {markdownPath}
            </code>
          </div>
        ) : null}

        {transcriptionText ? (
          <details className="text-xs text-primary-600">
            <summary className="cursor-pointer text-primary-700">查看原始转写文本</summary>
            <p className="mt-2 whitespace-pre-wrap text-primary-800">{transcriptionText}</p>
          </details>
        ) : null}
      </div>
    </div>
  );
};
