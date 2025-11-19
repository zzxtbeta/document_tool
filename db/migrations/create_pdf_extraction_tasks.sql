-- ============================================================================
-- PDF 提取任务表重建脚本
-- 用于在表被意外删除后重新创建
-- ============================================================================

-- 第一步：创建表（如果不存在）
CREATE TABLE IF NOT EXISTS pdf_extraction_tasks (
    -- ========== 主键与标识 ==========
    task_id TEXT PRIMARY KEY,
    task_status TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'qwen3-vl-flash',
    
    -- ========== PDF 文件信息 ==========
    pdf_url TEXT NOT NULL,
    pdf_object_key TEXT NOT NULL,
    page_count INTEGER,
    page_image_urls TEXT[],
    
    -- ========== 提取的结构化信息 (核心字段) ==========
    project_source TEXT,
    project_name TEXT,
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
    financing_history JSONB,
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

-- 第二步：创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_status ON pdf_extraction_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_industry ON pdf_extraction_tasks(industry);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_company ON pdf_extraction_tasks(company_name);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_submitted ON pdf_extraction_tasks(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_user ON pdf_extraction_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_tasks_project ON pdf_extraction_tasks(project_id);

-- 第三步：添加表和列注释
COMMENT ON TABLE pdf_extraction_tasks IS 'PDF 商业计划书智能解析任务表';
COMMENT ON COLUMN pdf_extraction_tasks.task_id IS '任务唯一标识 (UUID)';
COMMENT ON COLUMN pdf_extraction_tasks.task_status IS '任务状态: PENDING/PROCESSING/SUCCEEDED/FAILED (有效值: PENDING, PROCESSING, SUCCEEDED, FAILED)';
COMMENT ON COLUMN pdf_extraction_tasks.model IS '使用的视觉理解模型';
COMMENT ON COLUMN pdf_extraction_tasks.pdf_url IS 'OSS 上原始 PDF 文件 URL';
COMMENT ON COLUMN pdf_extraction_tasks.pdf_object_key IS 'OSS 对象键';
COMMENT ON COLUMN pdf_extraction_tasks.page_count IS 'PDF 页数';
COMMENT ON COLUMN pdf_extraction_tasks.page_image_urls IS 'PDF 页面图片 URL 列表';
COMMENT ON COLUMN pdf_extraction_tasks.project_source IS '项目来源';
COMMENT ON COLUMN pdf_extraction_tasks.project_name IS '项目名称';
COMMENT ON COLUMN pdf_extraction_tasks.project_contact IS '项目联系人';
COMMENT ON COLUMN pdf_extraction_tasks.contact_info IS '联系方式';
COMMENT ON COLUMN pdf_extraction_tasks.project_leader IS '项目负责人';
COMMENT ON COLUMN pdf_extraction_tasks.company_name IS '公司名称';
COMMENT ON COLUMN pdf_extraction_tasks.company_address IS '公司地址';
COMMENT ON COLUMN pdf_extraction_tasks.industry IS '所属行业';
COMMENT ON COLUMN pdf_extraction_tasks.core_team IS '核心团队成员 JSON 数组';
COMMENT ON COLUMN pdf_extraction_tasks.core_product IS '核心产品描述';
COMMENT ON COLUMN pdf_extraction_tasks.core_technology IS '核心技术描述';
COMMENT ON COLUMN pdf_extraction_tasks.competition_analysis IS '竞争情况分析';
COMMENT ON COLUMN pdf_extraction_tasks.market_size IS '市场空间描述';
COMMENT ON COLUMN pdf_extraction_tasks.financial_status IS '财务状况 JSON 对象 (current/future 收入/支出等)';
COMMENT ON COLUMN pdf_extraction_tasks.financing_history IS '融资历史 JSON 对象 (轮次/金额/投资方等，结构示例: {"round": "A轮", "amount": 1000000, "investors": ["投资方1", "投资方2"]})';
COMMENT ON COLUMN pdf_extraction_tasks.keywords IS '关键词数组';
COMMENT ON COLUMN pdf_extraction_tasks.extracted_info IS '完整提取结果 JSON';
COMMENT ON COLUMN pdf_extraction_tasks.extracted_info_url IS '提取结果 JSON 的 OSS URL';
COMMENT ON COLUMN pdf_extraction_tasks.extracted_info_object_key IS '提取结果 JSON 的 OSS 对象键';
COMMENT ON COLUMN pdf_extraction_tasks.submitted_at IS '任务提交时间';
COMMENT ON COLUMN pdf_extraction_tasks.started_at IS '任务开始处理时间';
COMMENT ON COLUMN pdf_extraction_tasks.completed_at IS '任务完成时间';
COMMENT ON COLUMN pdf_extraction_tasks.updated_at IS '最后更新时间';
COMMENT ON COLUMN pdf_extraction_tasks.error IS '错误信息 JSON';
COMMENT ON COLUMN pdf_extraction_tasks.user_id IS '用户 ID';
COMMENT ON COLUMN pdf_extraction_tasks.project_id IS '项目 ID';
COMMENT ON COLUMN pdf_extraction_tasks.source_filename IS '原始文件名';
COMMENT ON COLUMN pdf_extraction_tasks.oss_object_prefix IS 'OSS 对象前缀';
