-- Ensure schema
CREATE SCHEMA IF NOT EXISTS gold;

-- 1) organizations
CREATE TABLE IF NOT EXISTS gold.organizations (
  id   VARCHAR(31) PRIMARY KEY,
  organization_name VARCHAR(200) NOT NULL,
  organization_code VARCHAR(50),
  organization_type VARCHAR(50),
  description       TEXT,
  contact_person    VARCHAR(50),
  contact_email     VARCHAR(100),
  status            VARCHAR(20) DEFAULT 'active',
  created_at        TIMESTAMP DEFAULT NOW(),
  updated_at        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_organizations_code   ON gold.organizations(organization_code);
CREATE INDEX IF NOT EXISTS idx_organizations_status ON gold.organizations(status);

-- 2) users
CREATE TABLE IF NOT EXISTS gold.users (
  id          VARCHAR(31) PRIMARY KEY,
  username         VARCHAR(50) NOT NULL UNIQUE,
  email            VARCHAR(100) UNIQUE,
  phone            VARCHAR(20) NOT NULL,
  password_hash    VARCHAR(255),
  real_name        VARCHAR(50) NOT NULL,
  avatar_url       VARCHAR(500),
  organization_id  VARCHAR(31) REFERENCES gold.organizations(id),
  role             VARCHAR(20) DEFAULT 'user',
  status           VARCHAR(20) DEFAULT 'active',
  last_login_at    TIMESTAMP,
  created_at       TIMESTAMP DEFAULT NOW(),
  updated_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_org    ON gold.users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON gold.users(status);

-- 3) projects
CREATE TABLE IF NOT EXISTS gold.projects (
  id         VARCHAR(31) PRIMARY KEY,
  project_name       TEXT,
  company_name       TEXT,
  company_address    TEXT,
  project_contact    TEXT,
  contact_info       TEXT,
  industry           TEXT,
  core_team          JSONB,
  core_product       TEXT,
  core_technology    TEXT,
  competition_analysis  TEXT,
  market_size           TEXT,
  financial_status   JSONB,
  financing_history  JSONB,
  uploaded_by         VARCHAR(31) NOT NULL REFERENCES gold.users(id),
  status             VARCHAR(20) DEFAULT 'draft'
                     CHECK (status IN ('draft','pending_acceptance','accepted','due_diligence','approved','tracking','archived')),
  keywords           TEXT[],
  acceptance_at      TIMESTAMP,
  description        TEXT,
  created_at         TIMESTAMP DEFAULT NOW(),
  updated_at         TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_projects_uploaded_by   ON gold.projects(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_projects_status       ON gold.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_company_name ON gold.projects(company_name);
CREATE INDEX IF NOT EXISTS idx_projects_keywords ON gold.projects USING GIN (keywords);

-- 4) project_files
CREATE TABLE IF NOT EXISTS gold.project_files (
  id              VARCHAR(32) PRIMARY KEY,
  project_id           VARCHAR(31) NOT NULL REFERENCES gold.projects(id) ON DELETE CASCADE,
  file_name            VARCHAR(500) NOT NULL,
  file_type            VARCHAR(50),
  file_size            BIGINT,
  file_hash            VARCHAR(64),
  doc_type             VARCHAR(50) NOT NULL,
  bronze_path          VARCHAR(500),
  silver_markdown_path VARCHAR(500),
  file_card            JSONB,
  uploaded_by          VARCHAR(31) NOT NULL REFERENCES gold.users(id),
  uploaded_at          TIMESTAMP DEFAULT NOW(),
  last_modified_by     VARCHAR(31),
  last_modified_at     TIMESTAMP,
  status               VARCHAR(20) DEFAULT 'uploaded'
);
CREATE INDEX IF NOT EXISTS idx_project_files_project      ON gold.project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_uploaded_by  ON gold.project_files(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_project_files_status       ON gold.project_files(status);
CREATE INDEX IF NOT EXISTS idx_project_files_uploaded_at  ON gold.project_files(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_project_files_file_hash    ON gold.project_files(file_hash);

-- 5) project_permissions
CREATE TABLE IF NOT EXISTS gold.project_permissions (
  id               BIGSERIAL PRIMARY KEY,
  project_id       VARCHAR(31) NOT NULL REFERENCES gold.projects(id) ON DELETE CASCADE,
  user_id          VARCHAR(31) REFERENCES gold.users(id) ON DELETE CASCADE,
  permission_type  VARCHAR(20) NOT NULL CHECK (permission_type IN ('read','write','admin')),
  granted_by       VARCHAR(31),
  granted_at       TIMESTAMP DEFAULT NOW(),
);
CREATE INDEX IF NOT EXISTS idx_pp_project ON gold.project_permissions(project_id);
CREATE INDEX IF NOT EXISTS idx_pp_user    ON gold.project_permissions(user_id);

-- 6) data_lineage
CREATE TABLE IF NOT EXISTS gold.data_lineage (
  id             VARCHAR(31) PRIMARY KEY,
  parent_lineage_id      VARCHAR(31) REFERENCES gold.data_lineage(id) ON DELETE SET NULL,
  layer                  VARCHAR(20) NOT NULL CHECK (layer IN ('bronze','silver','gold')),
  source_entity_type     VARCHAR(50),
  source_entity_id       VARCHAR(200),
  source_path            TEXT,
  transformation_type    VARCHAR(50),
  transformation_logic   TEXT,
  flow_name              VARCHAR(200),
  flow_run_id            VARCHAR(200),
  task_name              VARCHAR(200),
  processed_at           TIMESTAMP NOT NULL,
  created_at             TIMESTAMP DEFAULT NOW(),
  meta_data              JSONB,
  source_file_id         VARCHAR(32) REFERENCES gold.project_files(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_dl_parent        ON gold.data_lineage(parent_lineage_id);
CREATE INDEX IF NOT EXISTS idx_dl_layer         ON gold.data_lineage(layer);
CREATE INDEX IF NOT EXISTS idx_dl_flow_run      ON gold.data_lineage(flow_run_id);
CREATE INDEX IF NOT EXISTS idx_dl_source_entity ON gold.data_lineage(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_dl_source_file   ON gold.data_lineage(source_file_id);
CREATE INDEX IF NOT EXISTS idx_dl_processed_at  ON gold.data_lineage(processed_at);

-- 7) project_notes（富文本笔记）
CREATE TABLE IF NOT EXISTS gold.project_notes (
  id       TEXT PRIMARY KEY,
  project_id    VARCHAR(31) NOT NULL REFERENCES gold.projects(id) ON DELETE CASCADE,
  author_id     VARCHAR(31) NOT NULL REFERENCES gold.users(id) ON DELETE SET NULL,
  note_type     TEXT,                    -- meeting/interview/analysis/memo
  content_md    TEXT,                    -- Markdown/HTML
  attachments   JSONB,                   -- [{type:'file', file_id:'...'}]
  visibility    VARCHAR(20) DEFAULT 'project',  -- private/org/project
  version       INT DEFAULT 1,
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pn_project   ON gold.project_notes(project_id);
CREATE INDEX IF NOT EXISTS idx_pn_author    ON gold.project_notes(author_id);
CREATE INDEX IF NOT EXISTS idx_pn_created   ON gold.project_notes(created_at);

-- 8) project_workflow_logs（台账/时间线）
CREATE TABLE IF NOT EXISTS gold.project_workflow_logs (
  id            BIGSERIAL PRIMARY KEY,
  project_id    VARCHAR(31) NOT NULL REFERENCES gold.projects(id) ON DELETE CASCADE,
  event_type    TEXT NOT NULL,           -- upload/intake/acceptance/due_diligence/note/followup/status_change/...
  event_status  TEXT,
  payload       JSONB,                   -- 变更详情（旧/新状态、文件ID、受理单号等）
  acted_by      VARCHAR(31) REFERENCES gold.users(id) ON DELETE SET NULL,
  acted_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pwl_project    ON gold.project_workflow_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_pwl_event      ON gold.project_workflow_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_pwl_acted_at   ON gold.project_workflow_logs(acted_at);

-- 9) roles（业务层 RBAC 角色）
CREATE TABLE IF NOT EXISTS gold.roles (
  id          SERIAL PRIMARY KEY,
  role_name   VARCHAR(50) UNIQUE NOT NULL,  -- admin/manager/analyst/guest ...
  description TEXT,
  created_at  TIMESTAMP DEFAULT NOW(),
  updated_at  TIMESTAMP DEFAULT NOW()
);

-- 10) user_roles（用户-角色关联）
CREATE TABLE IF NOT EXISTS gold.user_roles (
  id                     SERIAL PRIMARY KEY,
  user_id                VARCHAR(31) NOT NULL REFERENCES gold.users(id) ON DELETE CASCADE,
  role_id                INTEGER NOT NULL REFERENCES gold.roles(id) ON DELETE CASCADE,
  scope_organization_id  VARCHAR(31) REFERENCES gold.organizations(id),
  assigned_by            VARCHAR(31),
  assigned_at            TIMESTAMP DEFAULT NOW(),
  UNIQUE (user_id, role_id, scope_organization_id)
);
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON gold.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON gold.user_roles(role_id);