import axios from 'axios';
import type {
  PdfTask,
  QueueStatus,
  TaskStatus,
  BatchUploadResponse,
  TaskListResponse,
} from '../types/pdf';

const API_BASE = '/api/v1/pdf';

export const pdfApi = {
  /**
   * 单个 PDF 上传
   */
  async uploadSingle(file: File): Promise<PdfTask> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(`${API_BASE}/extract`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  },

  /**
   * 批量 PDF 上传
   */
  async uploadBatch(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<BatchUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post(`${API_BASE}/extract/batch`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  /**
   * 查询任务状态
   */
  async getTaskStatus(taskId: string): Promise<PdfTask> {
    const response = await axios.get(`${API_BASE}/extract/${taskId}`);
    // 后端返回 {success, data: {...}, error, metadata}
    return response.data.data;
  },

  /**
   * 列表查询
   */
  async listTasks(filters: {
    status?: TaskStatus;
    page?: number;
    page_size?: number;
  }): Promise<TaskListResponse> {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const response = await axios.get(`${API_BASE}/extract?${params.toString()}`);
    // 后端返回 {success, data: {tasks, total, page, page_size}, error, metadata}
    // 我们返回 data 部分
    return response.data.data;
  },

  /**
   * 获取队列状态
   */
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await axios.get(`${API_BASE}/queue/status`);
    // 后端返回 {success, data: {...}, error, metadata}
    return response.data.data;
  },

  /**
   * 获取任务详情（包含完整提取信息）
   */
  async getTaskDetail(taskId: string): Promise<PdfTask> {
    const response = await axios.get(`${API_BASE}/extract/${taskId}`);
    return response.data.data;
  },

  /**
   * 获取下载 URL
   */
  getDownloadUrl(taskId: string, fileType: 'json' | 'pdf'): string {
    return `${API_BASE}/download/${taskId}/${fileType}`;
  },
};

// 导出简化的 API 方法
export const uploadPdfBatch = pdfApi.uploadBatch;
export const listPdfTasks = pdfApi.listTasks;
export const getPdfTaskStatus = pdfApi.getTaskStatus;
export const getPdfTaskDetail = pdfApi.getTaskDetail;
export const getQueueStatus = pdfApi.getQueueStatus;
