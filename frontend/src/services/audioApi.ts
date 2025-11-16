import axios, { type AxiosProgressEvent } from 'axios';
import type { AudioTranscriptionResponse } from '../types/audio';

// 配置 axios 实例
const apiClient = axios.create({
  baseURL: '/api', // Use Vite proxy in development
  timeout: 300000, // 5 分钟超时
  headers: {
    'Content-Type': 'multipart/form-data',
  },
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
   * 获取下载 URL
   */
  getDownloadUrl(taskId: string): string {
    return `/api/v1/audio/download/${taskId}`;
  }

  /**
   * 检查服务健康状态
   */
  async checkHealth(): Promise<any> {
    const response = await apiClient.get('/api/v1/audio/health');
    return response.data;
  }
}

export const audioApi = new AudioApi();
