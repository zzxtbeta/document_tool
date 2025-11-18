import axios, { type AxiosProgressEvent } from 'axios';
import type {
  AudioTranscriptionResponse,
  LongAudioSubmissionResponse,
  LongAudioStatusResponse,
  DashScopeTaskListResponse,
  DashScopeTaskDetailResponse,
} from '../types/audio';

// 配置 axios 实例
const apiClient = axios.create({
  baseURL: '/',
  timeout: 300000,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

const jsonClient = axios.create({
  baseURL: '/',
  timeout: 120000,
});

export interface TranscribeOptions {
  output_format?: 'json' | 'markdown';
  output_dir?: string;
  enable_itn?: boolean;
  asr_context?: string;  // ASR 识别上下文（专业术语提示）
  language?: string;     // 音频语种（'zh', 'en', 'ja', 'ko' 等）
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
}

class AudioApi {
  /**
   * 转写音频文件
   */
  async transcribe(
    file: File,
    options: TranscribeOptions = {}
  ): Promise<AudioTranscriptionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    // 添加可选参数
    if (options.output_format) {
      formData.append('output_format', options.output_format);
    }
    if (options.output_dir) {
      formData.append('output_dir', options.output_dir);
    }
    if (options.enable_itn !== undefined) {
      formData.append('enable_itn', options.enable_itn.toString());
    }
    if (options.asr_context) {
      formData.append('asr_context', options.asr_context);
    }
    if (options.language) {
      formData.append('language', options.language);
    }

    const response = await apiClient.post<AudioTranscriptionResponse>(
      '/api/v1/audio/transcribe',
      formData,
      {
        onUploadProgress: options.onUploadProgress,
      }
    );

    return response.data;
  }

  /**
   * 提交长音频转写任务
   */
  async submitLongTask(payload: {
    file_urls: string[];
    model?: 'paraformer-v2' | 'paraformer-8k-v2';
    language_hints?: string[];
  }): Promise<LongAudioSubmissionResponse> {
    const response = await jsonClient.post<LongAudioSubmissionResponse>(
      '/api/v1/audio/transcribe-long',
      payload
    );
    return response.data;
  }

  /**
   * 获取长音频任务状态
   */
  async getLongTaskStatus(taskId: string): Promise<LongAudioStatusResponse> {
    const response = await jsonClient.get<LongAudioStatusResponse>(
      `/api/v1/audio/transcribe-long/${taskId}`
    );
    return response.data;
  }

  /**
   * DashScope 任务列表
   */
  async listDashScopeTasks(params: {
    task_id?: string;
    start_time?: string;
    end_time?: string;
    model_name?: string;
    status?: string;
    page_no?: number;
    page_size?: number;
  }): Promise<DashScopeTaskListResponse> {
    const response = await jsonClient.get<DashScopeTaskListResponse>(
      '/api/v1/audio/dashscope/tasks',
      { params }
    );
    return response.data;
  }

  /**
   * DashScope 单任务详情
   */
  async fetchDashScopeTask(dashscopeTaskId: string): Promise<DashScopeTaskDetailResponse> {
    const response = await jsonClient.get<DashScopeTaskDetailResponse>(
      `/api/v1/audio/dashscope/tasks/${dashscopeTaskId}`
    );
    return response.data;
  }

  /**
   * 取消 DashScope 任务
   */
  async cancelDashScopeTask(dashscopeTaskId: string): Promise<void> {
    await jsonClient.post(`/api/v1/audio/dashscope/tasks/${dashscopeTaskId}/cancel`);
  }

  /**
   * 获取下载 URL
   */
  getDownloadUrl(taskId: string): string {
    return `/api/v1/audio/download/${taskId}`;
  }

  /**
   * 检查服务健康状态
   */
  async checkHealth(): Promise<{ status: string }> {
    const response = await apiClient.get<{ status: string }>('/api/v1/audio/health');
    return response.data;
  }
}

export const audioApi = new AudioApi();
