import { create } from 'zustand';
import { audioApi, type TranscribeOptions } from '../services/audioApi';
import type { AudioState } from '../types/audio';

interface AudioStore extends AudioState {
  // Advanced settings
  asrContext?: string;
  language?: string;
  
  // Actions
  uploadAudio: (file: File, options?: TranscribeOptions) => Promise<void>;
  resetState: () => void;
  setError: (error: string | null) => void;
  setAdvancedSettings: (settings: { asrContext?: string; language?: string }) => void;
}

const initialState: AudioState = {
  isUploading: false,
  isProcessing: false,
  progress: 0,
  currentTaskId: null,
  markdownContent: null,
  downloadUrl: null,
  error: null,
  processingStats: null,
};

export const useAudioStore = create<AudioStore>((set, get) => ({
  ...initialState,
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
    } catch (error: any) {
      set({
        isUploading: false,
        isProcessing: false,
        progress: 0,
        error: error.response?.data?.detail || error.message || '上传失败，请重试',
      });
    }
  },

  resetState: () => set(initialState),

  setError: (error: string | null) => set({ error }),
  
  setAdvancedSettings: (settings: { asrContext?: string; language?: string }) => {
    set({
      asrContext: settings.asrContext,
      language: settings.language,
    });
  },
}));
