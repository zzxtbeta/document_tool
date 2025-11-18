import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { usePdfStore } from '../../store/usePdfStore';
import type { ExtractionResult } from '../../types/pdf';

// 15 个字段的配置 - 受理单样式
const FIELD_CONFIG = [
  { key: 'company_name', label: '公司名称', section: 'basic', required: true },
  { key: 'established_date', label: '成立时间', section: 'basic', required: false },
  { key: 'registered_capital', label: '注册资本', section: 'basic', required: false },
  { key: 'legal_representative', label: '法定代表人', section: 'basic', required: false },
  { key: 'business_scope', label: '经营范围', section: 'business', expandable: true },
  { key: 'main_products_services', label: '主营业务', section: 'business', expandable: true },
  { key: 'target_market', label: '目标市场', section: 'business', expandable: true },
  { key: 'competitive_advantage', label: '竞争优势', section: 'business', expandable: true },
  { key: 'revenue', label: '营业收入', section: 'financial', required: false },
  { key: 'profit', label: '利润', section: 'financial', required: false },
  { key: 'assets', label: '资产', section: 'financial', required: false },
  { key: 'liabilities', label: '负债', section: 'financial', required: false },
  { key: 'funding_amount', label: '融资金额', section: 'funding', required: false },
  { key: 'funding_purpose', label: '融资用途', section: 'funding', expandable: true },
  { key: 'team_info', label: '团队信息', section: 'team', expandable: true },
];

interface PdfExtractionResultProps {
  result: ExtractionResult | null;
  taskId?: string;
}

export const PdfExtractionResult: React.FC<PdfExtractionResultProps> = ({
  result,
  taskId,
}) => {
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const { downloadFile } = usePdfStore();

  if (!result) {
    return (
      <div className="text-center text-primary-400 py-12">
        <svg className="w-16 h-16 mx-auto mb-4 text-primary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-sm">上传 PDF 文件后，提取结果将显示在此处</p>
      </div>
    );
  }

  const toggleExpand = (key: string) => {
    const newExpanded = new Set(expandedFields);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedFields(newExpanded);
  };

  const renderFieldValue = (field: typeof FIELD_CONFIG[number]) => {
    const value = result[field.key as keyof ExtractionResult];
    const isExpanded = expandedFields.has(field.key);
    const shouldTruncate = field.expandable && typeof value === 'string' && (value as string).length > 100;

    // Treat null/undefined, empty strings, and empty arrays as "no data"
    if (
      value === null ||
      value === undefined ||
      (typeof value === 'string' && value.trim() === '') ||
      (Array.isArray(value) && value.length === 0)
    ) {
      return <span className="text-primary-400 italic text-sm">未提取到信息</span>;
    }

    if (typeof value === 'string') {
      return (
        <div className="space-y-1">
          <div
            className={`text-sm text-primary-700 prose prose-sm max-w-none ${
              shouldTruncate && !isExpanded ? 'line-clamp-2' : ''
            }`}
          >
            <ReactMarkdown>{value}</ReactMarkdown>
          </div>
          {shouldTruncate && (
            <button
              onClick={() => toggleExpand(field.key)}
              className="text-xs text-accent-blue hover:underline"
            >
              {isExpanded ? '收起' : '展开全文'}
            </button>
          )}
        </div>
      );
    }

    return (
      <pre className="text-xs bg-primary-50 p-2 rounded overflow-x-auto">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  };

  // 按部分分组字段
  const sections = [
    { key: 'basic', title: '基本信息', icon: '🏢' },
    { key: 'business', title: '业务信息', icon: '📋' },
    { key: 'financial', title: '财务信息', icon: '💰' },
    { key: 'funding', title: '融资信息', icon: '💸' },
    { key: 'team', title: '团队信息', icon: '👥' },
  ];

  return (
    <div className="space-y-6">
      {/* 受理单头部 */}
      <div className="bg-gradient-to-r from-primary-900 to-primary-800 text-white rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold mb-2">商业计划书受理单</h2>
            <p className="text-sm opacity-90">
              {result.company_name || '未知公司'}
            </p>
          </div>
          <div className="text-right">
            <div className="text-xs opacity-75 mb-1">受理编号</div>
            <div className="font-mono text-sm">{taskId?.slice(0, 8).toUpperCase()}</div>
          </div>
        </div>
      </div>

      {/* 下载按钮 */}
      <div className="flex items-center gap-3 bg-primary-50 rounded-lg p-4 border border-primary-200">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-primary-900">导出受理单</h3>
          <p className="text-xs text-primary-600">当前支持 JSON 格式下载</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => taskId && downloadFile(taskId, 'json')}
            className="px-4 py-2 bg-primary-900 text-white rounded-lg hover:bg-primary-800 text-sm font-medium transition-colors"
          >
            📄 JSON
          </button>
        </div>
      </div>

      {/* 受理单内容 - 分段展示 */}
      {sections.map((section) => {
        const sectionFields = FIELD_CONFIG.filter((f) => f.section === section.key);
        if (sectionFields.length === 0) return null;

        return (
          <div key={section.key} className="bg-white rounded-lg border border-primary-200 overflow-hidden">
            {/* 分段标题 */}
            <div className="bg-primary-50 border-b border-primary-200 px-6 py-3">
              <h3 className="text-sm font-semibold text-primary-900 flex items-center gap-2">
                <span className="text-lg">{section.icon}</span>
                {section.title}
              </h3>
            </div>

            {/* 字段列表 */}
            <div className="divide-y divide-primary-100">
              {sectionFields.map((field) => (
                <div key={field.key} className="px-6 py-4 hover:bg-primary-50 transition-colors">
                  <div className="flex items-start gap-4">
                    {/* 字段标签 */}
                    <div className="w-32 flex-shrink-0">
                      <label className="text-sm font-medium text-primary-900 flex items-center gap-1">
                        {field.label}
                        {field.required && <span className="text-red-500">*</span>}
                      </label>
                    </div>

                    {/* 字段值 */}
                    <div className="flex-1 min-w-0">
                      {renderFieldValue(field)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {/* 受理单底部 */}
      <div className="bg-primary-50 rounded-lg p-4 border border-primary-200">
        <div className="flex items-center justify-between text-xs text-primary-600">
          <div>
            <span className="font-medium">AI 提取引擎：</span> Qwen3-VL-Flash
          </div>
          <div>
            <span className="font-medium">提取时间：</span> {new Date().toLocaleString('zh-CN')}
          </div>
        </div>
      </div>
    </div>
  );
};
