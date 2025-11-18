// PDF 提取相关的 TypeScript 类型定义

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

// 核心团队成员
export interface CoreTeamMember {
  name: string;
  role: string;
  background: string;
}

// 融资轮次
export interface FundingRound {
  round: string;
  amount: string;
  investors: string[];
}

// 当前融资
export interface CurrentFunding {
  round: string;
  target_amount: string;
  status: string;
}

// 融资状态
export interface FinancingStatus {
  completed_rounds?: FundingRound[];
  current_round?: CurrentFunding;
  funding_need?: string;
  use_of_funds?: string[];
}

// 财务状态
export interface FinancialStatus {
  current?: string;
  future?: string;
}

// 提取结果（匹配后端返回的 JSON 结构）
export interface ExtractionResult {
  project_contact?: string;
  contact_info?: string;
  project_leader?: string;
  company_name?: string;
  company_address?: string;
  industry?: string;
  core_team?: CoreTeamMember[];
  core_product?: string;
  core_technology?: string;
  competition_analysis?: string;
  market_size?: string;
  financial_status?: FinancialStatus;
  financing_status?: FinancingStatus;
  keywords?: string[];
  project_source?: string;
}

// PDF 任务
export interface PdfTask {
  task_id: string;
  original_filename: string;
  status: TaskStatus;
  created_at: string;
  updated_at?: string;
  submitted_at?: string;
  completed_at?: string;
  pdf_url?: string;
  images?: string[];
  result?: ExtractionResult;
  error?: string;
  // 提取信息字段
  extracted_info?: ExtractionResult;
  extracted_info_url?: string;
  extracted_info_object_key?: string;
  company_name?: string;
  industry?: string;
  project_contact?: string;
  project_leader?: string;
}

// 队列状态
export interface QueueStatus {
  is_running: boolean;
  queue_length: number;
  active_tasks: number;
  completed_tasks: number;
  active_workers: number;
  pending_tasks: number;
  queue_capacity: number;
  max_workers: number;
  max_queue_size: number;
}

// API 响应类型
export interface PdfExtractionResponse {
  task_id: string;
  original_filename: string;
  status: TaskStatus;
  pdf_url?: string;
  created_at: string;
}

export interface BatchUploadResponse {
  task_ids: string[];
  total_files: number;
  message: string;
}

export interface TaskListResponse {
  tasks: PdfTask[];
  total: number;
  page: number;
  page_size: number;
}
