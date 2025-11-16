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
