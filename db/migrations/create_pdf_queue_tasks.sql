-- ============================================================================
-- PDF 队列任务表和项目表创建脚本
-- 用于 PDF 处理系统与同事仓库集成
-- ============================================================================

-- 第一步：创建 projects 表（与同事仓库结构保持一致）
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(31) PRIMARY KEY,
    project_name TEXT,
    company_name TEXT,
    company_address TEXT,
    project_contact TEXT,
    contact_info TEXT,
    project_leader TEXT,
    industry TEXT,
    core_team JSONB,
    core_product TEXT,
    core_technology TEXT,
    competition_analysis TEXT,
    market_size TEXT,
    financial_status JSONB,
    financing_history JSONB,
    uploaded_by VARCHAR(31),
    status VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft','pending_acceptance','accepted','due_diligence','approved','tracking','archived')),
    keywords TEXT[],
    acceptance_at TIMESTAMP,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建 projects 表索引
CREATE INDEX IF NOT EXISTS idx_projects_uploaded_by ON projects(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_company_name ON projects(company_name);
CREATE INDEX IF NOT EXISTS idx_projects_keywords ON projects USING GIN (keywords);

-- 添加 projects 表注释
COMMENT ON TABLE projects IS '项目表 - 存储 BP 文档提取的项目信息';
COMMENT ON COLUMN projects.id IS '项目唯一标识';
COMMENT ON COLUMN projects.project_name IS '项目名称';
COMMENT ON COLUMN projects.company_name IS '公司名称';
COMMENT ON COLUMN projects.company_address IS '公司地址';
COMMENT ON COLUMN projects.project_contact IS '项目联系人';
COMMENT ON COLUMN projects.contact_info IS '联系方式';
COMMENT ON COLUMN projects.project_leader IS '项目负责人';
COMMENT ON COLUMN projects.industry IS '所属行业';
COMMENT ON COLUMN projects.core_team IS '核心团队成员 JSON 数组';
COMMENT ON COLUMN projects.core_product IS '核心产品描述';
COMMENT ON COLUMN projects.core_technology IS '核心技术描述';
COMMENT ON COLUMN projects.competition_analysis IS '竞争情况分析';
COMMENT ON COLUMN projects.market_size IS '市场空间描述';
COMMENT ON COLUMN projects.financial_status IS '财务状况 JSON 对象';
COMMENT ON COLUMN projects.financing_history IS '融资历史 JSON 对象';
COMMENT ON COLUMN projects.uploaded_by IS '上传用户 ID';
COMMENT ON COLUMN projects.status IS '项目状态';
COMMENT ON COLUMN projects.keywords IS '关键词数组';
COMMENT ON COLUMN projects.acceptance_at IS '接受时间';
COMMENT ON COLUMN projects.description IS '项目描述';
COMMENT ON COLUMN projects.created_at IS '创建时间';
COMMENT ON COLUMN projects.updated_at IS '更新时间';

-- 第二步：创建 pdf_queue_tasks 表（任务管理）
CREATE TABLE IF NOT EXISTS pdf_queue_tasks (
    -- ========== 主键与标识 ==========
    task_id TEXT PRIMARY KEY,
    task_status TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'qwen3-vl-flash',
    
    -- ========== 关联标识（非外键） ==========
    project_id VARCHAR(31) NOT NULL,
    file_id TEXT,
    
    -- ========== PDF 文件信息 ==========
    pdf_url TEXT NOT NULL,
    pdf_object_key TEXT NOT NULL,
    page_count INTEGER,
    
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
    
    -- ========== 处理配置 ==========
    retry_count INTEGER DEFAULT 0,
    high_resolution BOOLEAN DEFAULT FALSE,
    user_id TEXT,
    
    -- ========== 文件信息 ==========
    source_filename TEXT,
    oss_object_prefix TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 第三步：创建 pdf_queue_tasks 表索引
CREATE INDEX IF NOT EXISTS idx_pdf_queue_tasks_project_id ON pdf_queue_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_pdf_queue_tasks_file_id ON pdf_queue_tasks(file_id);
CREATE INDEX IF NOT EXISTS idx_pdf_queue_tasks_status ON pdf_queue_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_pdf_queue_tasks_submitted ON pdf_queue_tasks(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdf_queue_tasks_user_id ON pdf_queue_tasks(user_id);

-- 第四步：添加 pdf_queue_tasks 表注释
COMMENT ON TABLE pdf_queue_tasks IS 'PDF 处理队列任务表 - 管理 PDF 处理任务的生命周期';
COMMENT ON COLUMN pdf_queue_tasks.task_id IS '任务唯一标识 (UUID)';
COMMENT ON COLUMN pdf_queue_tasks.task_status IS '任务状态: pending/processing/completed/failed';
COMMENT ON COLUMN pdf_queue_tasks.model IS '使用的视觉理解模型';
COMMENT ON COLUMN pdf_queue_tasks.project_id IS '关联的项目 ID (FK)';
COMMENT ON COLUMN pdf_queue_tasks.file_id IS '关联的文件 ID';
COMMENT ON COLUMN pdf_queue_tasks.pdf_url IS 'OSS 上原始 PDF 文件 URL';
COMMENT ON COLUMN pdf_queue_tasks.pdf_object_key IS 'OSS 对象键';
COMMENT ON COLUMN pdf_queue_tasks.page_count IS 'PDF 页数';
COMMENT ON COLUMN pdf_queue_tasks.extracted_info IS '完整提取结果 JSON';
COMMENT ON COLUMN pdf_queue_tasks.extracted_info_url IS '提取结果 JSON 的 OSS URL';
COMMENT ON COLUMN pdf_queue_tasks.extracted_info_object_key IS '提取结果 JSON 的 OSS 对象键';
COMMENT ON COLUMN pdf_queue_tasks.submitted_at IS '任务提交时间';
COMMENT ON COLUMN pdf_queue_tasks.started_at IS '任务开始处理时间';
COMMENT ON COLUMN pdf_queue_tasks.completed_at IS '任务完成时间';
COMMENT ON COLUMN pdf_queue_tasks.updated_at IS '最后更新时间';
COMMENT ON COLUMN pdf_queue_tasks.error IS '错误信息 JSON';
COMMENT ON COLUMN pdf_queue_tasks.retry_count IS '重试次数';
COMMENT ON COLUMN pdf_queue_tasks.high_resolution IS '是否启用高分辨率模式';
COMMENT ON COLUMN pdf_queue_tasks.user_id IS '用户 ID';
COMMENT ON COLUMN pdf_queue_tasks.source_filename IS '原始文件名';
COMMENT ON COLUMN pdf_queue_tasks.oss_object_prefix IS 'OSS 对象前缀';
COMMENT ON COLUMN pdf_queue_tasks.created_at IS '记录创建时间';
