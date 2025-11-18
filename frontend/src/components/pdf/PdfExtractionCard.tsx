import type { ExtractionResult } from '../../types/pdf';

interface Props {
  extractionResult?: ExtractionResult | null;
  error?: string | null;
}

export const PdfExtractionCard = ({
  extractionResult,
  error,
}: Props) => {
  if (error) {
    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-rose-600">提取失败</h4>
        <p className="text-xs text-rose-500 whitespace-pre-wrap">{error}</p>
      </div>
    );
  }

  if (!extractionResult) {
    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-primary-900">投资受理单</h4>
        <p className="text-xs text-primary-500">信息提取中，请稍后刷新查看。</p>
      </div>
    );
  }

  const formatArray = (arr?: string[]) => arr?.join(', ') || '未提供';

  return (
    <div className="space-y-4">
      <h4 className="text-lg font-bold text-primary-900">投资受理单</h4>

      {/* 基本信息 */}
      <section className="rounded-lg border border-primary-100 bg-primary-50/60 p-4 space-y-3">
        <h5 className="text-sm font-semibold text-primary-900 border-b border-primary-200 pb-2">
          基本信息
        </h5>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-primary-500">公司名称</p>
            <p className="text-sm font-semibold text-primary-900">
              {extractionResult.company_name || '未提供'}
            </p>
          </div>
          <div>
            <p className="text-xs text-primary-500">所属行业</p>
            <p className="text-sm font-semibold text-primary-900">
              {extractionResult.industry || '未提供'}
            </p>
          </div>
          <div>
            <p className="text-xs text-primary-500">项目联系人</p>
            <p className="text-sm text-primary-800">
              {extractionResult.project_contact || '未提供'}
            </p>
          </div>
          <div>
            <p className="text-xs text-primary-500">项目负责人</p>
            <p className="text-sm text-primary-800">
              {extractionResult.project_leader || '未提供'}
            </p>
          </div>
          {extractionResult.contact_info && (
            <div className="col-span-2">
              <p className="text-xs text-primary-500">联系方式</p>
              <p className="text-sm text-primary-800">{extractionResult.contact_info}</p>
            </div>
          )}
          {extractionResult.company_address && (
            <div className="col-span-2">
              <p className="text-xs text-primary-500">公司地址</p>
              <p className="text-sm text-primary-800">{extractionResult.company_address}</p>
            </div>
          )}
        </div>
      </section>

      {/* 核心团队 */}
      {extractionResult.core_team && extractionResult.core_team.length > 0 && (
        <section className="rounded-lg border border-blue-100 bg-blue-50/60 p-4 space-y-3">
          <h5 className="text-sm font-semibold text-blue-900 border-b border-blue-200 pb-2">
            核心团队
          </h5>
          <div className="space-y-3">
            {extractionResult.core_team.map((member, index) => (
              <div key={index} className="bg-white/80 rounded p-3 space-y-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-blue-900">{member.name}</p>
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                    {member.role}
                  </span>
                </div>
                <p className="text-xs text-blue-800 whitespace-pre-wrap">{member.background}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 产品与技术 */}
      <section className="rounded-lg border border-purple-100 bg-purple-50/60 p-4 space-y-3">
        <h5 className="text-sm font-semibold text-purple-900 border-b border-purple-200 pb-2">
          产品与技术
        </h5>
        {extractionResult.core_product && (
          <div>
            <p className="text-xs text-purple-500 mb-1">核心产品</p>
            <p className="text-sm text-purple-800 whitespace-pre-wrap">
              {extractionResult.core_product}
            </p>
          </div>
        )}
        {extractionResult.core_technology && (
          <div>
            <p className="text-xs text-purple-500 mb-1">核心技术</p>
            <p className="text-sm text-purple-800 whitespace-pre-wrap">
              {extractionResult.core_technology}
            </p>
          </div>
        )}
      </section>

      {/* 市场与竞争 */}
      <section className="rounded-lg border border-orange-100 bg-orange-50/60 p-4 space-y-3">
        <h5 className="text-sm font-semibold text-orange-900 border-b border-orange-200 pb-2">
          市场与竞争
        </h5>
        {extractionResult.market_size && (
          <div>
            <p className="text-xs text-orange-500 mb-1">市场规模</p>
            <p className="text-sm text-orange-800 whitespace-pre-wrap">
              {extractionResult.market_size}
            </p>
          </div>
        )}
        {extractionResult.competition_analysis && (
          <div>
            <p className="text-xs text-orange-500 mb-1">竞争分析</p>
            <p className="text-sm text-orange-800 whitespace-pre-wrap">
              {extractionResult.competition_analysis}
            </p>
          </div>
        )}
      </section>

      {/* 财务状况 */}
      {extractionResult.financial_status && (
        <section className="rounded-lg border border-green-100 bg-green-50/60 p-4 space-y-3">
          <h5 className="text-sm font-semibold text-green-900 border-b border-green-200 pb-2">
            财务状况
          </h5>
          {extractionResult.financial_status.current && (
            <div>
              <p className="text-xs text-green-500 mb-1">当前状况</p>
              <p className="text-sm text-green-800 whitespace-pre-wrap">
                {extractionResult.financial_status.current}
              </p>
            </div>
          )}
          {extractionResult.financial_status.future && (
            <div>
              <p className="text-xs text-green-500 mb-1">未来展望</p>
              <p className="text-sm text-green-800 whitespace-pre-wrap">
                {extractionResult.financial_status.future}
              </p>
            </div>
          )}
        </section>
      )}

      {/* 融资信息 */}
      {extractionResult.financing_status && (
        <section className="rounded-lg border border-rose-100 bg-rose-50/60 p-4 space-y-3">
          <h5 className="text-sm font-semibold text-rose-900 border-b border-rose-200 pb-2">
            融资信息
          </h5>
          
          {extractionResult.financing_status.completed_rounds && 
           extractionResult.financing_status.completed_rounds.length > 0 && (
            <div>
              <p className="text-xs text-rose-500 mb-2">已完成轮次</p>
              <div className="space-y-2">
                {extractionResult.financing_status.completed_rounds.map((round, index) => (
                  <div key={index} className="bg-white/80 rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-rose-900">{round.round}</span>
                      <span className="text-sm text-rose-700">{round.amount}</span>
                    </div>
                    <p className="text-xs text-rose-600">
                      投资方：{formatArray(round.investors)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {extractionResult.financing_status.current_round && (
            <div>
              <p className="text-xs text-rose-500 mb-1">当前融资</p>
              <div className="bg-white/80 rounded p-2 space-y-1">
                <p className="text-sm text-rose-800">
                  <span className="font-semibold">轮次：</span>
                  {extractionResult.financing_status.current_round.round}
                </p>
                <p className="text-sm text-rose-800">
                  <span className="font-semibold">目标金额：</span>
                  {extractionResult.financing_status.current_round.target_amount}
                </p>
                <p className="text-sm text-rose-800">
                  <span className="font-semibold">状态：</span>
                  {extractionResult.financing_status.current_round.status}
                </p>
              </div>
            </div>
          )}

          {extractionResult.financing_status.funding_need && (
            <div>
              <p className="text-xs text-rose-500 mb-1">资金需求</p>
              <p className="text-sm text-rose-800">{extractionResult.financing_status.funding_need}</p>
            </div>
          )}

          {extractionResult.financing_status.use_of_funds && 
           extractionResult.financing_status.use_of_funds.length > 0 && (
            <div>
              <p className="text-xs text-rose-500 mb-1">资金用途</p>
              <ul className="text-sm list-disc pl-4 space-y-1">
                {extractionResult.financing_status.use_of_funds.map((use, index) => (
                  <li key={index} className="text-rose-800">{use}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* 关键词 */}
      {extractionResult.keywords && extractionResult.keywords.length > 0 && (
        <section className="rounded-lg border border-primary-100 bg-primary-50/60 p-4 space-y-2">
          <h5 className="text-sm font-semibold text-primary-900">关键词</h5>
          <div className="flex flex-wrap gap-2">
            {extractionResult.keywords.map((keyword, index) => (
              <span
                key={index}
                className="inline-flex items-center rounded-full border border-primary-200 bg-white/80 px-3 py-1 text-xs text-primary-700 font-medium"
              >
                {keyword}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* 项目来源 */}
      {extractionResult.project_source && (
        <div className="text-xs text-primary-500">
          项目来源：{extractionResult.project_source}
        </div>
      )}
    </div>
  );
};
