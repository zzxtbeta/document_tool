import { create } from 'zustand';
import { audioApi, type TranscribeOptions } from '../services/audioApi';
import type { AxiosError } from 'axios';
import type {
  AudioState,
  LongAudioFormPayload,
  LongAudioSubmissionResponse,
  LongAudioTaskSummary,
  LongAudioStatus,
  LongAudioStatusResponse,
  LongAudioStoreState,
  DashScopeTask,
  TaskFilters,
} from '../types/audio';

interface AudioStore extends AudioState, LongAudioStoreState {
  // Advanced settings
  asrContext?: string;
  language?: string;
  
  // Actions
  uploadAudio: (file: File, options?: TranscribeOptions) => Promise<void>;
  resetState: () => void;
  setError: (error: string | null) => void;
  setAdvancedSettings: (settings: { asrContext?: string; language?: string }) => void;
  submitLongAudio: (payload: LongAudioFormPayload) => Promise<LongAudioSubmissionResponse | null>;
  refreshLongTask: (taskId: string) => Promise<void>;
  loadDashScopeTasks: (filters?: { status?: LongAudioStatus | 'ALL'; model?: string }) => Promise<void>;
  cancelDashScopeTask: (dashscopeTaskId: string) => Promise<void>;
  selectTask: (task: LongAudioTaskSummary | null) => void;
  setTaskFilters: (filters: TaskFilters) => void;
  fetchDashScopeTaskDetail: (dashscopeTaskId: string) => Promise<void>;
}

const initialAudioState: AudioState = {
  isUploading: false,
  isProcessing: false,
  progress: 0,
  currentTaskId: null,
  markdownContent: null,
  downloadUrl: null,
  error: null,
  processingStats: null,
};

const initialLongState: LongAudioStoreState = {
  longTasks: [],
  selectedTask: null,
  isSubmittingLong: false,
  isLoadingTasks: false,
  isLoadingDetail: false,
  taskFilters: {
    status: 'ALL',
  },
  dashscopePage: 1,
  dashscopeTotal: 0,
};

type ApiErrorResponse = { detail?: string };

const isAxiosError = (error: unknown): error is AxiosError<ApiErrorResponse> =>
  typeof error === 'object' && error !== null && 'isAxiosError' in error;

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (detail) return detail;
    if (error.message) return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

const mergeTasks = (
  existing: LongAudioTaskSummary[],
  updates: LongAudioTaskSummary[],
): LongAudioTaskSummary[] => {
  const map = new Map(existing.map((task) => [task.taskId, task]));
  for (const update of updates) {
    const prev = map.get(update.taskId);
    map.set(update.taskId, prev ? { ...prev, ...update } : update);
  }

  return Array.from(map.values()).sort((a, b) => {
    const aTime = a.updatedAt || a.submittedAt;
    const bTime = b.updatedAt || b.submittedAt;
    return new Date(bTime).getTime() - new Date(aTime).getTime();
  });
};

const mapStatusResponseToSummary = (
  response: LongAudioStatusResponse
): LongAudioTaskSummary => {
  const data = response.data;
  const firstResult = Array.isArray(data.results) ? data.results[0] : undefined;
  const summarySnippet =
    data.summary_snippet ||
    data.meeting_minutes?.content?.slice(0, 200) ||
    data.transcription_text?.slice(0, 200) ||
    firstResult?.text ||
    firstResult?.content;
  return {
    taskId: data.task_id,
    dashscopeTaskId: data.dashscope_task_id,
    taskType: 'long',
    origin: 'local',
    model: data.model,
    status: data.task_status,
    fileUrls: data.file_urls,
    languageHints: data.language_hints,
    submittedAt: data.submitted_at,
    updatedAt: data.updated_at,
    remoteResultTtlSeconds: data.remote_result_ttl_seconds,
    remoteResultExpiresAt: data.remote_result_expires_at,
    localResultPaths: data.local_result_paths,
    localAudioPaths: data.local_audio_paths,
    localDir: data.local_dir,
    results: data.results,
    transcriptionUrl: firstResult?.transcription_url,
    summarySnippet,
    transcriptionText: data.transcription_text,
    meetingMinutes: data.meeting_minutes,
    minutesMarkdownPath:
      data.minutes_markdown_path || response.metadata?.minutes_markdown_path,
    minutesGeneratedAt: data.minutes_generated_at,
    minutesError: data.minutes_error ?? response.metadata?.minutes_error ?? null,
    error: data.error,
  };
};

const fromSubmission = (
  res: LongAudioSubmissionResponse,
  payload: LongAudioFormPayload
): LongAudioTaskSummary => ({
  taskId: res.data.task_id,
  dashscopeTaskId: res.data.dashscope_task_id,
  taskType: 'long',
  origin: 'local',
  model: res.data.model,
  status: res.data.task_status,
  fileUrls: [payload.fileUrl],
  languageHints: payload.languageHints,
  submittedAt: res.metadata.timestamp,
  updatedAt: res.metadata.timestamp,
});

export const useAudioStore = create<AudioStore>((set, get) => ({
  ...initialAudioState,
  ...initialLongState,
  asrContext: undefined,
  language: undefined,

  uploadAudio: async (file: File, options: TranscribeOptions = {}) => {
    set({ 
      isUploading: true, 
      isProcessing: true,
      error: null, 
      progress: 0,
      markdownContent: null,
      downloadUrl: null,
    });

    try {
      // 获取高级设置
      const { asrContext, language } = get();
      
      // 默认使用 markdown 格式
      const uploadOptions: TranscribeOptions = {
        output_format: 'markdown',
        enable_itn: true,
        asr_context: asrContext,
        language: language,
        ...options,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const uploadProgress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            // 上传阶段占 20%，处理阶段占 80%
            set({ progress: Math.min(uploadProgress * 0.2, 20) });
          }
        },
      };

      // 上传完成后，模拟处理进度
      const progressInterval = setInterval(() => {
        set((state) => ({
          progress: Math.min(state.progress + 5, 90),
        }));
      }, 500);

      const response = await audioApi.transcribe(file, uploadOptions);

      clearInterval(progressInterval);

      if (response.success) {
        set({
          isUploading: false,
          isProcessing: false,
          progress: 100,
          currentTaskId: response.metadata.task_id,
          markdownContent: response.markdown_content || null,
          downloadUrl: response.download_url || null,
          processingStats: response.processing_stats || null,
          error: null,
        });
      } else {
        throw new Error(response.error || '处理失败');
      }
    } catch (error) {
      set({
        isUploading: false,
        isProcessing: false,
        progress: 0,
        error: extractErrorMessage(error, '上传失败，请重试'),
      });
    }
  },

  fetchDashScopeTaskDetail: async (dashscopeTaskId: string) => {
    set({ isLoadingDetail: true });
    try {
      const response = await audioApi.fetchDashScopeTask(dashscopeTaskId);
      const output = response.data?.output || {};
      const results = output.results || [];
      const summary: LongAudioTaskSummary = {
        taskId: output.task_id || dashscopeTaskId,
        dashscopeTaskId,
        taskType: 'long',
        origin: 'dashscope',
        model: output.model || '-',
        status: (output.task_status as LongAudioStatus) || 'UNKNOWN',
        fileUrls: output.file_urls || [],
        languageHints: output.language_hints || [],
        submittedAt: output.submit_time || new Date().toISOString(),
        updatedAt: output.end_time || new Date().toISOString(),
        transcriptionUrl: results?.[0]?.transcription_url,
        summarySnippet: results?.[0]?.text || results?.[0]?.content,
        results,
      };

      set((state) => ({
        isLoadingDetail: false,
        selectedTask:
          state.selectedTask && state.selectedTask.dashscopeTaskId === dashscopeTaskId
            ? { ...state.selectedTask, ...summary }
            : summary,
        longTasks: mergeTasks(state.longTasks, [summary]),
      }));
    } catch (error) {
      set({
        isLoadingDetail: false,
        error: extractErrorMessage(error, '获取任务详情失败'),
      });
    }
  },

  resetState: () => set({ ...initialAudioState }),

  setError: (error: string | null) => set({ error }),
  
  setAdvancedSettings: (settings: { asrContext?: string; language?: string }) => {
    set({
      asrContext: settings.asrContext,
      language: settings.language,
    });
  },

  submitLongAudio: async (payload: LongAudioFormPayload) => {
    set({ isSubmittingLong: true, error: null });
    try {
      const response = await audioApi.submitLongTask({
        file_urls: [payload.fileUrl],
        model: payload.model,
        language_hints: payload.languageHints.filter(Boolean),
      });
      const newTask = fromSubmission(response, payload);
      set((state) => ({
        isSubmittingLong: false,
        longTasks: mergeTasks(state.longTasks, [newTask]),
      }));
      return response;
    } catch (error) {
      set({
        isSubmittingLong: false,
        error: extractErrorMessage(error, '长音频提交失败'),
      });
      return null;
    }
  },

  refreshLongTask: async (taskId: string) => {
    try {
      const response = await audioApi.getLongTaskStatus(taskId);
      const summary = mapStatusResponseToSummary(response);
      set((state) => ({
        longTasks: state.longTasks.map((task) =>
          task.taskId === taskId ? { ...task, ...summary } : task
        ),
        selectedTask:
          state.selectedTask && state.selectedTask.taskId === taskId
            ? { ...state.selectedTask, ...summary }
            : state.selectedTask,
      }));
    } catch (error) {
      set({ error: extractErrorMessage(error, '刷新任务失败') });
    }
  },

  loadDashScopeTasks: async (filters = {}) => {
    const currentFilters = { ...get().taskFilters, ...filters } as TaskFilters;
    set({ isLoadingTasks: true, taskFilters: currentFilters });
    try {
      const params: Record<string, string | number | undefined> = {
        status:
          currentFilters.status && currentFilters.status !== 'ALL'
            ? currentFilters.status
            : undefined,
        model_name: currentFilters.model,
        page_no: 1,
        page_size: 20,
      };
      const response = await audioApi.listDashScopeTasks(params);
      const listData = response.data || {};
      const dashscopeTasks = listData.data ?? [];
      const tasks = dashscopeTasks.map((item: DashScopeTask) => ({
        taskId: item.task_id,
        dashscopeTaskId: item.task_id,
        taskType: 'long' as const,
        origin: 'dashscope' as const,
        model: item.model_name || '-',
        status: item.status as LongAudioStatus,
        fileUrls: [],
        submittedAt: item.start_time ? new Date(item.start_time).toISOString() : '',
        updatedAt: item.end_time ? new Date(item.end_time).toISOString() : '',
      }));
      set((state) => ({
        longTasks: mergeTasks(state.longTasks, tasks),
        isLoadingTasks: false,
        dashscopeTotal: listData.total,
      }));
    } catch (error) {
      set({
        isLoadingTasks: false,
        error: extractErrorMessage(error, '加载任务失败'),
      });
    }
  },

  cancelDashScopeTask: async (dashscopeTaskId: string) => {
    try {
      await audioApi.cancelDashScopeTask(dashscopeTaskId);
      set((state) => ({
        longTasks: state.longTasks.map((task) =>
          task.dashscopeTaskId === dashscopeTaskId
            ? { ...task, status: 'CANCELED', error: '已取消任务' }
            : task
        ),
      }));
    } catch (error) {
      set({ error: extractErrorMessage(error, '取消失败') });
    }
  },

  selectTask: (task: LongAudioTaskSummary | null) => {
    if (!task) {
      set({ selectedTask: null });
      return;
    }
    set({ selectedTask: task });
    if (task.origin === 'local') {
      void get().refreshLongTask(task.taskId);
    } else if (task.dashscopeTaskId) {
      void get().fetchDashScopeTaskDetail(task.dashscopeTaskId);
    }
  },

  setTaskFilters: (filters: TaskFilters) => set({ taskFilters: filters }),
}));
