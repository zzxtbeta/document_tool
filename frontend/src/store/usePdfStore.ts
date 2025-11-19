import { create } from 'zustand';
import { pdfApi } from '../services/pdfApi';
import type { PdfTask, ExtractionResult, QueueStatus, TaskStatus } from '../types/pdf';

interface PdfState {
  // 上传状态
  isUploading: boolean;
  uploadProgress: number;

  // 任务列表
  tasks: PdfTask[];
  isLoadingTasks: boolean;
  taskFilters: { status?: TaskStatus; page?: number; page_size?: number };

  // 当前选中的任务
  selectedTask: PdfTask | null;
  selectedResult: ExtractionResult | null;

  // 队列状态
  queueStatus: QueueStatus | null;

  // 错误
  error: string | null;

  // Actions
  uploadPdfs: (files: File[]) => Promise<void>;
  loadTasks: (filters: PdfState['taskFilters']) => Promise<void>;
  refreshTask: (taskId: string) => Promise<PdfTask | null>;
  selectTask: (task: PdfTask) => Promise<void>;
  loadQueueStatus: () => Promise<void>;
  downloadFile: (taskId: string, fileType: 'json' | 'pdf') => void;
  deleteTask: (taskId: string) => Promise<void>;
  setTaskFilters: (filters: PdfState['taskFilters']) => void;
  clearError: () => void;
  clearSelectedTask: () => void;
}

export const usePdfStore = create<PdfState>((set, get) => ({
  isUploading: false,
  uploadProgress: 0,
  tasks: [],
  isLoadingTasks: false,
  taskFilters: { page: 1, page_size: 20 },
  selectedTask: null,
  selectedResult: null,
  queueStatus: null,
  error: null,

  uploadPdfs: async (files) => {
    set({ isUploading: true, error: null, uploadProgress: 0 });

    try {
      // 批量上传
      await pdfApi.uploadBatch(files, (progress) => {
        set({ uploadProgress: progress });
      });

      set({
        isUploading: false,
        uploadProgress: 100,
      });

      // 刷新任务列表
      await get().loadTasks(get().taskFilters);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '上传失败',
        isUploading: false,
        uploadProgress: 0,
      });
    }
  },

  loadTasks: async (filters) => {
    set({ isLoadingTasks: true, error: null });

    try {
      const response = await pdfApi.listTasks(filters);
      set({ tasks: response.tasks, isLoadingTasks: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '加载任务失败',
        isLoadingTasks: false,
      });
    }
  },

  refreshTask: async (taskId) => {
    try {
      const task = await pdfApi.getTaskStatus(taskId);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.task_id === taskId ? task : t)),
      }));

      // 如果当前选中的任务被刷新，同时更新选中状态
      const currentSelected = get().selectedTask;
      if (currentSelected && currentSelected.task_id === taskId) {
        set({
          selectedTask: task,
          selectedResult: task.extracted_info || task.result || null,
        });
      }

      return task; // 返回更新后的任务
    } catch (error) {
      console.warn('刷新任务失败:', error);
      return null;
    }
  },

  selectTask: async (task) => {
    set({
      selectedTask: task,
      selectedResult: task.extracted_info || task.result || null,
    });

    // 如果任务已完成且没有结果，重新获取
    if (task.status === 'completed' && !task.extracted_info && !task.result) {
      try {
        const fullTask = await pdfApi.getTaskStatus(task.task_id);
        set({
          selectedTask: fullTask,
          selectedResult: fullTask.extracted_info || fullTask.result || null,
        });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : '加载结果失败' });
      }
    }
  },

  loadQueueStatus: async () => {
    try {
      const status = await pdfApi.getQueueStatus();
      set({ queueStatus: status });
    } catch (error) {
      console.warn('加载队列状态失败:', error);
    }
  },

  downloadFile: (taskId, fileType) => {
    const url = pdfApi.getDownloadUrl(taskId, fileType);
    window.open(url, '_blank');
  },

  deleteTask: async (taskId) => {
    try {
      await pdfApi.deleteTask(taskId);
      // 删除成功后，从任务列表中移除
      set((state) => ({
        tasks: state.tasks.filter((task) => task.task_id !== taskId),
        selectedTask: state.selectedTask?.task_id === taskId ? null : state.selectedTask,
        selectedResult: state.selectedTask?.task_id === taskId ? null : state.selectedResult,
      }));
    } catch (error) {
      set({ error: `删除任务失败: ${error instanceof Error ? error.message : '未知错误'}` });
      throw error;
    }
  },

  setTaskFilters: (filters) => {
    set({ taskFilters: filters });
  },

  clearError: () => {
    set({ error: null });
  },

  clearSelectedTask: () => {
    set({ selectedTask: null, selectedResult: null });
  },
}));
