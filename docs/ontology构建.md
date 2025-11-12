新的字段设计
A. 核心实体（Core Entities）
Company（公司）
用途/说明：全流程的锚点实体；围绕公司展开的池构建、可比、监测、估值等均依赖它。
最小字段（MVP 必备）
id：全局唯一标识，建议“命名空间 + 法定ID/统一社会信用代码”，便于跨源对齐。
legalName：法定名称，作为主显示名与主键参与对齐。
altName[]：别名/英文名/历史名，消歧与检索友好。
country/region：国家/地区，便于监管口径与估值口径区分。
foundedDate：成立日期，阶段判断与对比基线。
stage：发展阶段（Seed/Pre-A/A/B/…/上市），用于筛选与估值分组。
inSegment[]：所属赛道/细分（→ TagConcept），用于召回与策略化筛选。
usesTechnology[]：采用/关联技术（→ Technology），用于技术画像与可比。
website?：官网，便于校验与回溯。
sourceOfTruth：主数据来源（公开/私有/混合），解决冲突优先级。
provenance[]：证据链（来源、链接、时间、抽取器版本、置信度等），满足审计与回滚。
说明：诸如“股东/实控人/上下游/团队/竞品”等复杂信息不直接冗余在公司对象内，而通过关系/事件表达，降低写入复杂度、提升一致性。
常用动作
align_to_id：对齐外部ID（工商、第三方库），完成实体消歧。
normalize_names：标准化名称与别名。
attach_tag / attach_technology：挂载赛道标签与技术标签。
create_card / update_card：生成/更新公司卡（画像+证据）。
add_to_collection：加入候选池/可比池。
subscribe_updates：订阅公司相关事件/信号（监测）。
Person（人物/团队成员）
任职经历 如何作为信号或者关系关联人物（时序关系）？
用途/说明：创始人/高管/核心研发，支撑团队画像、背调与风险识别。
最小字段
id：全局唯一标识。
name：姓名。
aka[]：别名/英文名，支撑消歧。
education[]：教育背景（学校/专业/学位/时间），技术关联与校友网络分析的基础。
positions[]：任职经历（组织/头衔/起止），用于组织关系与路径。
works[]：代表成果（paper/patent/project 引用），用于技术权威度判断。
provenance[]：证据链，确保可追溯。
常用动作
disambiguate_person：人名消歧（结合组织/时间/作品）。
link_company：建立任职/持股关系（→ Position/Ownership）。
create_card：人物卡。
find_relation_path：多跳关联路径发现（→ GraphPath）。
Technology（技术/概念）
Paper是否要作为实体？关联技术和人
用途/说明：赛道主题、可比因子与上下游定位的核心语义对象；与 SKOS 兼容。
最小字段
id：全局唯一标识。
prefLabel：主标签（标准名）。
altLabel[]：别名/缩写（如“BCI”“柔性电极”）。
broader / narrower：上下位层级关系，支持“行业 → 领域 → 技术路线 → 元器件/材料”。
representativeWorks[]：代表性论文/专利/开源仓库，体现成熟度与生态。
scopeNote：口径/定义说明，便于统一认知与可比口径。
provenance[]：证据链。
常用动作
attach_to_company / attach_to_person：挂载到公司或人物（使用/研究/贡献）。
map_upstream_downstream：技术上下游概念映射（与标签/公司联动）。
generate_card：技术卡（原理/应用/代表公司与人才）。
TagConcept（赛道/细分标签）
用途/说明：统一命名与层级，支撑策略、召回与对比；以 SKOS 管理词库与治理流程。
最小字段
id：全局唯一标识。
prefLabel：主标签。
altLabel[]：别名。
broader / narrower：上下位层级。
scopeNote：口径/适用范围说明。
provenance[]：证据链。
常用动作
propose_tag → review_tag → commit_tag：标签治理工作流（提案/审核/入库）。
attach_to(company/tech/report)：标签挂载到公司/技术/报告等对象。
B. 事件与信号（Events & Signals）
Event（事件基类）
用途/说明：新闻/政策/论文/专利/融资/招聘/工商变更等的统一外壳，便于抽取、去重、合并、回溯与推理。
最小字段
id：全局唯一标识。
eventType：类型枚举（News/Policy/Patent/Paper/Financing/Hiring/Registration …）。
occurredAt：发生时间。
sourceUrl：来源链接（可空）。
credibility：来源可信度（0–1）。
dedupeFingerprint：去重指纹（标题+时间窗+主体等）。
subjects[]：受体/关联主体（Company/Person/Technology）。
summary：结构化摘要（“发生了什么—影响谁—为什么重要”）。
provenance[]：证据链（内容片段、抽取器版本、时间）。
常见子类扩展字段
FinancingEvent：roundType（轮次）、amount/currency（金额/币种）、valuation（估值）、investors[]（投资方与角色）。
HiringEvent：roles[]（岗位）、count（数量）、functionMix（职能分布）。
PolicyEvent：jurisdiction（辖区）、topic（主题）。
Patent：office（专利局）、number（专利号）、assignees[]（权利人）。
Paper：venue（期刊/会议）、doi、authors[]（作者）。
Registration：regChangeType（工商变更类型）、before/after（变更前后要点）。
常用动作
detect_event / extract_entities：事件识别与实体抽取。
merge_events：时间窗合并与去重。
update_datahub：更新至数据枢纽（入湖/入图）。
attach_evidence：追加证据。
promote_to_signal：升级为统计信号（见下）。



