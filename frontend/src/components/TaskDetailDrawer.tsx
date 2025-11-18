import { type ReactNode, useState } from 'react';
import { useAudioStore } from '../store/useAudioStore';
import { STATUS_LABEL, STATUS_STYLE } from './taskStatus';
import { MeetingMinutesCard } from './MeetingMinutesCard';

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="space-y-2">
    <h4 className="text-sm font-semibold text-primary-900">{title}</h4>
    <div className="rounded-lg border border-primary-100 bg-primary-50/50 px-3 py-2 text-sm text-primary-700">
      {children}
    </div>
  </div>
);

export const TaskDetailDrawer = () => {
  const selectedTask = useAudioStore((state) => state.selectedTask);
  const isLoadingDetail = useAudioStore((state) => state.isLoadingDetail);
  const selectTask = useAudioStore((state) => state.selectTask);
  const refreshLongTask = useAudioStore((state) => state.refreshLongTask);
  const cancelDashScopeTask = useAudioStore((state) => state.cancelDashScopeTask);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  if (!selectedTask) return null;

  const closeDrawer = () => selectTask(null);
  const status = selectedTask.status || 'UNKNOWN';
  const result = Array.isArray(selectedTask.results) ? selectedTask.results[0] : null;

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/30" onClick={closeDrawer} />
      <div className="absolute top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl flex flex-col">
        <div className="flex items-center justify-between border-b border-primary-100 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-primary-900">任务详情</h3>
            <p className="text-xs text-primary-500">DashScope 任务 ID：{selectedTask.dashscopeTaskId}</p>
          </div>
          <button
            type="button"
            onClick={closeDrawer}
            className="p-2 text-primary-500 hover:text-primary-700"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {isLoadingDetail && (
            <div className="text-sm text-primary-500">正在加载任务详情...</div>
          )}

          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-primary-700">{selectedTask.taskId}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLE[status]}`}>
              {STATUS_LABEL[status]}
            </span>
          </div>

          <Section title="基本信息">
            <div className="space-y-1">
              <p>类型：{selectedTask.taskType === 'short' ? '短音频' : '长音频'}</p>
              <p>模型：{selectedTask.model}</p>
              <p>提交时间：{selectedTask.submittedAt}</p>
              <p>最近更新：{selectedTask.updatedAt}</p>
              {selectedTask.remoteResultExpiresAt && (
                <p>DashScope TTL：{selectedTask.remoteResultExpiresAt}</p>
              )}
            </div>
          </Section>

          {selectedTask.fileUrls?.length ? (
            <Section title="音频 URL">
              <ul className="list-disc pl-4 space-y-1">
                {selectedTask.fileUrls.map((url) => (
                  <li key={url} className="break-all">
                    <a href={url} target="_blank" rel="noreferrer" className="text-primary-700 underline">
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {selectedTask.localResultPaths?.length ? (
            <Section title="本地结果 JSON">
              <ul className="list-disc pl-4 space-y-1 text-xs break-all">
                {selectedTask.localResultPaths.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
              <p className="text-xs text-primary-500 mt-2">可登录服务器后根据路径获取 JSON 文件。</p>
            </Section>
          ) : null}

          {selectedTask.remoteResultUrls?.length ? (
            <Section title="OSS 转写 JSON">
              <ul className="space-y-2">
                {selectedTask.remoteResultUrls.map((url, idx) => (
                  <li key={url}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-primary-700 hover:text-primary-900 underline"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      转写结果 #{idx} (公开访问)
                    </a>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {selectedTask.localAudioPaths?.length ? (
            <Section title="本地音频副本">
              <ul className="list-disc pl-4 space-y-1 text-xs break-all">
                {selectedTask.localAudioPaths.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
            </Section>
          ) : null}

          {result?.transcription_url && (
            <Section title="DashScope 转写 JSON">
              <a
                href={result.transcription_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-primary-700 underline"
              >
                打开 DashScope JSON
              </a>
            </Section>
          )}

          {selectedTask.summarySnippet && (
            <Section title="识别摘要">
              <p className="text-sm whitespace-pre-wrap">{selectedTask.summarySnippet}</p>
            </Section>
          )}

          {(selectedTask.meetingMinutes || selectedTask.minutesError) && (
            <Section title="会议纪要">
              <MeetingMinutesCard
                meetingMinutes={selectedTask.meetingMinutes}
                markdownPath={selectedTask.minutesMarkdownPath}
                transcriptionText={selectedTask.transcriptionText}
                minutesGeneratedAt={selectedTask.minutesGeneratedAt}
                minutesError={selectedTask.minutesError}
              />
              {selectedTask.minutesMarkdownSignedUrl && (
                <div className="mt-3 pt-3 border-t border-primary-100">
                  <a
                    href={selectedTask.minutesMarkdownSignedUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 text-sm text-primary-700 hover:text-primary-900 underline"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    下载会议纪要 Markdown
                  </a>
                  <p className="text-xs text-primary-500 mt-1">临时下载链接(10分钟内有效)</p>
                </div>
              )}
            </Section>
          )}
        </div>

        <div className="border-t border-primary-100 px-6 py-4 flex flex-wrap gap-3">
          {cancelError && (
            <div className="w-full text-sm text-rose-600 bg-rose-50 px-3 py-2 rounded-lg">
              {cancelError}
            </div>
          )}
          <button
            type="button"
            onClick={() => refreshLongTask(selectedTask.taskId)}
            className="px-4 py-2 rounded-lg border border-primary-200 text-sm text-primary-700 hover:bg-primary-50"
          >
            刷新
          </button>
          {selectedTask.status === 'PENDING' && (
            <button
              type="button"
              onClick={async () => {
                if (isCancelling) return;
                setCancelError(null);
                setIsCancelling(true);
                try {
                  await cancelDashScopeTask(selectedTask.dashscopeTaskId);
                  await refreshLongTask(selectedTask.taskId);
                } catch (error: any) {
                  const errorMsg = error?.response?.data?.detail || error?.message || '取消失败';
                  setCancelError(errorMsg);
                  console.error('取消任务失败:', error);
                } finally {
                  setIsCancelling(false);
                }
              }}
              disabled={isCancelling}
              className="px-4 py-2 rounded-lg border border-rose-200 text-sm text-rose-600 hover:bg-rose-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isCancelling ? '取消中...' : '取消任务'}
            </button>
          )}
          <button
            type="button"
            onClick={closeDrawer}
            className="ml-auto px-4 py-2 rounded-lg bg-primary-900 text-white text-sm hover:bg-primary-800"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
