// API 类型定义

export interface ProcessingStats {
  total_time: number;
  transcription_time: number;
  llm_time: number;
}

export interface AudioMetadata {
  duration_seconds: number;
  format: string;
  file_size_mb: number;
  sample_rate?: number;
  channels?: number;
}

export interface MeetingMinutes {
  title: string;
  content: string;
  key_quotes: string[];
  keywords: string[];
  generated_at: string;
}

export interface AudioTranscriptionResponse {
  success: boolean;
  transcript?: string;
  markdown_content?: string;
  markdown_file_path?: string;
  download_url?: string;
  processing_stats?: ProcessingStats;
  audio_metadata?: AudioMetadata;
  data?: {
    transcription_text: string;
    meeting_minutes: MeetingMinutes;
    audio_metadata: AudioMetadata;
    processing_stats: ProcessingStats;
  };
  error?: string;
  metadata: {
    task_id: string;
    timestamp: string;
    filename: string;
    file_size_mb: number;
    processing_time?: number;
    output_format?: string;
  };
}

// UI 状态类型
export interface AudioState {
  isUploading: boolean;
  isProcessing: boolean;
  progress: number;
  currentTaskId: string | null;
  markdownContent: string | null;
  downloadUrl: string | null;
  error: string | null;
  processingStats: ProcessingStats | null;
}

// 长音频相关类型
export type LongAudioStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'UNKNOWN' | 'CANCELED';

export interface LongAudioSubmissionResponse {
  success: boolean;
  data: {
    task_id: string;
    dashscope_task_id: string;
    task_status: LongAudioStatus;
    model: string;
  };
  metadata: {
    timestamp: string;
  };
}

export interface LongAudioResult {
  transcription_url?: string;
  text?: string;
  content?: string;
  subtask_status?: string;
  [key: string]: unknown;
}

export interface LongAudioTaskSummary {
  taskId: string;
  dashscopeTaskId: string;
  taskType?: 'short' | 'long';
  origin?: 'local' | 'dashscope';
  model: string;
  status: LongAudioStatus;
  fileUrls: string[];
  languageHints?: string[];
  submittedAt: string;
  updatedAt: string;
  remoteResultTtlSeconds?: number;
  remoteResultExpiresAt?: string;
  localResultPaths?: string[];
  localAudioPaths?: string[];
  localDir?: string;
  results?: LongAudioResult[];
  transcriptionUrl?: string;
  summarySnippet?: string;
  transcriptionText?: string;
  meetingMinutes?: MeetingMinutes;
  minutesMarkdownPath?: string;
  minutesGeneratedAt?: string;
  minutesError?: string | null;
  error?: string | null;
}

export interface LongAudioStatusResponse {
  success: boolean;
  data: {
    task_id: string;
    dashscope_task_id: string;
    task_status: LongAudioStatus;
    model: string;
    file_urls: string[];
    language_hints?: string[];
    submitted_at: string;
    updated_at: string;
    results?: LongAudioResult[];
    local_result_paths?: string[];
    local_audio_paths?: string[];
    local_dir?: string;
    remote_result_ttl_seconds?: number;
    remote_result_expires_at?: string;
    transcription_url?: string;
    summary_snippet?: string;
    transcription_text?: string;
    meeting_minutes?: MeetingMinutes;
    minutes_markdown_path?: string;
    minutes_generated_at?: string;
    minutes_error?: string | null;
    error?: string | null;
  };
  metadata: {
    timestamp: string;
    poll_interval_seconds?: number;
    remote_result_ttl_seconds?: number;
    remote_result_expires_at?: string;
    remote_result_expired?: boolean;
    meeting_minutes_ready?: boolean;
    minutes_markdown_path?: string;
    minutes_error?: string | null;
  };
}

export interface DashScopeTask {
  task_id: string;
  status: LongAudioStatus | 'UNKNOWN' | 'CANCELED';
  model_name?: string;
  start_time?: number;
  end_time?: number;
  request_id?: string;
  region?: string;
  [key: string]: unknown;
}

export interface DashScopeTaskListData {
  total?: number;
  total_page?: number;
  page_no?: number;
  page_size?: number;
  data?: DashScopeTask[];
}

export interface DashScopeTaskListResponse {
  success: boolean;
  data: DashScopeTaskListData;
  metadata: Record<string, unknown>;
}

export interface LongAudioFormPayload {
  fileUrl: string;
  model: 'paraformer-v2' | 'paraformer-8k-v2';
  languageHints: string[];
}

export interface DashScopeTaskDetailResponse {
  success: boolean;
  data: {
    output?: {
      task_id?: string;
      task_status?: LongAudioStatus;
      model?: string;
      file_urls?: string[];
      language_hints?: string[];
      submit_time?: string;
      end_time?: string;
      results?: LongAudioResult[];
    };
  };
  metadata?: Record<string, unknown>;
}

export interface TaskFilters {
  status?: LongAudioStatus | 'ALL';
  model?: string;
  search?: string;
}

export interface LongAudioStoreState {
  longTasks: LongAudioTaskSummary[];
  selectedTask: LongAudioTaskSummary | null;
  isSubmittingLong: boolean;
  isLoadingTasks: boolean;
  isLoadingDetail: boolean;
  taskFilters: TaskFilters;
  dashscopePage: number;
  dashscopeTotal?: number;
}
