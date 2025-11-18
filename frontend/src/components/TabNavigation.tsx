import React from 'react';

type TabType = 'audio' | 'pdf';

interface TabNavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange,
}) => {
  const tabs = [
    {
      id: 'audio' as const,
      label: '音频转写',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
      ),
      description: '会议纪要生成',
    },
    {
      id: 'pdf' as const,
      label: 'PDF 提取',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      description: '商业计划书信息提取',
    },
  ];

  return (
    <div className="border-b border-primary-200 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-3 py-4 border-b-2 transition-all
                ${
                  activeTab === tab.id
                    ? 'border-primary-900 text-primary-900'
                    : 'border-transparent text-primary-600 hover:text-primary-900 hover:border-primary-300'
                }
              `}
            >
              <div className={activeTab === tab.id ? 'text-primary-900' : 'text-primary-500'}>
                {tab.icon}
              </div>
              <div className="text-left">
                <div className="font-semibold text-sm">{tab.label}</div>
                <div className="text-xs text-primary-500">{tab.description}</div>
              </div>
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
};
