-- 创建 PDF 提取任务表
-- 用于存储 PDF 商业计划书智能解析任务的元数据和提取结果

CREATE TABLE IF NOT EXISTS pdf_extraction_tasks (
    -- ========== 主键与标识 ==========
    task_id TEXT PRIMARY KEY,
    task_status TEXT NOT NULL CHECK (task_status IN ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED')),
    model TEXT NOT NULL DEFAULT 'qwen3-vl-flash',
    
    -- ========== PDF 文件信息 ==========
    pdf_url TEXT NOT NULL,
    pdf_object_key TEXT NOT NULL,
    page_count INTEGER,
    page_image_urls TEXT[],
    
    -- ========== 提取的结构化信息 (核心字段) ==========
    project_source TEXT,
    project_contact TEXT,
    contact_info TEXT,
    project_leader TEXT,
    company_name TEXT,
    company_address TEXT,
    industry TEXT,
    core_team JSONB,
    core_product TEXT,
    core_technology TEXT,
    competition_analysis TEXT,
    market_size TEXT,
    financial_status JSONB,
    financing_status TEXT,
    keywords TEXT[],
    
    -- ========== 完整提取结果 ==========
    extracted_info JSONB,
    extracted_info_url TEXT,
    extracted_info_object_key TEXT,
    
    -- ========== 时间戳 ==========
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- ========== 错误处理 ==========
    error JSONB,
    
    -- ========== 租户信息 ==========
    user_id TEXT,
    project_id TEXT,
    source_filename TEXT,
    oss_object_prefix TEXT
);

-- ========== 创建索引 ==========
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_status ON pdf_extraction_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_industry ON pdf_extraction_tasks(industry);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_company ON pdf_extraction_tasks(company_name);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_submitted ON pdf_extraction_tasks(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_user ON pdf_extraction_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_project ON pdf_extraction_tasks(project_id);

-- ========== 添加注释 ==========
COMMENT ON TABLE pdf_extraction_tasks IS 'PDF 商业计划书智能解析任务表';
COMMENT ON COLUMN pdf_extraction_tasks.task_id IS '任务唯一标识 (UUID)';
COMMENT ON COLUMN pdf_extraction_tasks.task_status IS '任务状态: PENDING/PROCESSING/SUCCEEDED/FAILED';
COMMENT ON COLUMN pdf_extraction_tasks.model IS '使用的视觉理解模型';
COMMENT ON COLUMN pdf_extraction_tasks.pdf_url IS 'OSS 上原始 PDF 文件 URL';
COMMENT ON COLUMN pdf_extraction_tasks.page_image_urls IS 'PDF 页面图片 URL 列表';
COMMENT ON COLUMN pdf_extraction_tasks.core_team IS '核心团队成员 JSON 数组';
COMMENT ON COLUMN pdf_extraction_tasks.financial_status IS '财务状况 JSON 对象 (current/future)';
COMMENT ON COLUMN pdf_extraction_tasks.extracted_info IS '完整提取结果 JSON';
COMMENT ON COLUMN pdf_extraction_tasks.error IS '错误信息 JSON';
