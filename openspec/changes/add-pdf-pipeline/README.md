# PDF Pipeline - OpenSpec 变更集

本目录包含 PDF 商业计划书智能解析管道的完整 OpenSpec 文档。

## 📋 文档清单

- **[proposal.md](./proposal.md)** - 项目提案,包含背景、目标、技术方案、成本估算
- **[design.md](./design.md)** - 详细技术设计,包含架构、数据流、组件设计
- **[tasks.md](./tasks.md)** - 实施任务清单,包含 4 周的详细开发计划
- **[specs/api/spec.md](./specs/api/spec.md)** - API 行为规范,采用 BDD 格式

## 🎯 功能概述

基于 Qwen3-VL-Flash 视觉理解模型,自动从 PDF 格式的商业计划书中提取结构化信息。

### 核心能力

- ✅ PDF 批量上传与异步处理
- ✅ 基于优先级的任务队列
- ✅ 15 个结构化字段提取
- ✅ 结果持久化(OSS + PostgreSQL)
- ✅ 实时队列状态监控
- ✅ 前端展示与筛选
- ✅ 成本优化(~¥0.04-0.08/份 BP)
- ✅ 灵活的环境变量配置

### 提取字段

| 分类 | 字段 |
|------|------|
| 联系信息 | project_source, project_contact, contact_info, project_leader |
| 公司信息 | company_name, company_address, industry |
| 团队产品 | core_team, core_product, core_technology |
| 市场分析 | competition_analysis, market_size |
| 财务融资 | financial_status, financing_status |
| 其他 | keywords |

## 📊 实施计划

| 阶段 | 时长 | 交付物 |
|------|------|--------|
| **Phase 1: MVP 后端** | 2 周 | 完整的 PDF 处理管道和 API |
| **Phase 2: 前端集成** | 1 周 | 上传、展示、筛选界面 |
| **Phase 3: 生产准备** | 1 周 | 性能优化、监控、部署 |

## 🏗️ 技术栈

- **PDF 处理**: pdf2image, Pillow
- **视觉理解**: Qwen3-VL-Flash (DashScope 实时 API)
- **异步队列**: asyncio + 优先级队列
- **存储**: OSS (文件) + PostgreSQL (元数据)
- **后端**: FastAPI
- **前端**: React + TypeScript

## 💡 关键设计决策

### 为什么不使用 Batch API?

虽然阿里云提供了 Batch API (50% 成本折扣),但经过评估,**不适合我们的场景**:

| 对比项 | Batch API | 实时 API + 本地队列 |
|--------|-----------|---------------------|
| 处理时间 | 不确定,取决于调度 | 可控,< 60s |
| 用户体验 | 可能等待很久 | 相对实时反馈 |
| 成本 | 50% 折扣 | 原价,但本身很低 (~¥0.04) |
| 适用场景 | 离线批量处理 | 用户实时上传 |
| 并发控制 | 系统调度 | 本地可控 |

**结论**: 采用实时 API + asyncio 异步队列,既保证用户体验,又支持批量处理。

## 📁 目录结构

```
add-pdf-pipeline/
├── README.md                    # 本文件
├── proposal.md                  # 项目提案
├── design.md                    # 技术设计
├── tasks.md                     # 任务清单
└── specs/
    └── api/
        └── spec.md              # API 规范
```

## 🔗 相关链接

- [Qwen VL 官方文档](https://help.aliyun.com/zh/model-studio/vision)
- [pdf2image 文档](https://github.com/Belval/pdf2image)
- [长音频模块参考](../add-paraformer-long-audio/)

## 📝 变更记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2025-11-18 | v1.0 | 初始版本,完成提案和设计 |

## 👥 负责人

- **提案人**: AI Assistant
- **技术负责人**: 待定
- **产品负责人**: 待定

## ✅ 当前状态

**状态**: 提案中  
**优先级**: P1  
**预计完成**: 2025-12-01

---

## 快速开始

### 1. 阅读文档顺序

建议按以下顺序阅读:

1. **proposal.md** - 理解项目背景和目标
2. **design.md** - 了解技术架构和实现细节
3. **tasks.md** - 查看具体开发任务
4. **specs/api/spec.md** - 熟悉 API 规范

### 2. 开始实施

参考 `tasks.md` 中的任务清单,按阶段推进:

```bash
# 阶段 1: 数据库设计
cd db/
# 创建迁移文件和操作函数

# 阶段 2: PDF 处理管道
cd pipelines/
# 实现 PDF 转换、VL 提取、数据验证

# 阶段 3: API 开发
cd api/routes/
# 实现 PDF 相关路由

# 阶段 4: 前端开发
cd frontend/src/components/
# 创建上传和展示组件
```

### 3. 验收标准

完成以下验收项即可上线:

- [ ] 能成功上传并解析标准 BP PDF
- [ ] 15 个字段提取准确率 > 85%
- [ ] 单个 BP 处理时间 < 60s
- [ ] API 响应时间 < 300ms
- [ ] 前端功能完整且响应流畅
- [ ] 通过所有单元测试和集成测试
- [ ] 完成压力测试(并发 5 个任务)

---

**文档维护**: 请在实施过程中及时更新相关文档,确保文档与代码同步。
