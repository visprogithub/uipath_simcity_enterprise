'use client';

import { useState } from 'react';
import StaffingControls from './StaffingControls';
import AutonomyControls from './AutonomyControls';
import FailoverControls from './FailoverControls';
import UiPathStatusPanel from './UiPathStatusPanel';
import clsx from 'clsx';

type TabId = 'staffing' | 'autonomy' | 'failover' | 'uipath';

const TABS: { id: TabId; label: string; shortLabel: string }[] = [
  { id: 'staffing', label: 'Staffing', shortLabel: 'Staff' },
  { id: 'autonomy', label: 'Autonomy', shortLabel: 'Auto' },
  { id: 'failover', label: 'Failover', shortLabel: 'Fail' },
  { id: 'uipath', label: 'UiPath', shortLabel: 'UiP' },
];

export default function ControlsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('staffing');

  return (
    <div className="flex flex-col h-full bg-bg-panel border-l border-border-dim">
      {/* Tab bar */}
      <div className="flex border-b border-border-dim shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex-1 py-2 text-xs font-semibold tracking-wide transition-all border-b-2',
              activeTab === tab.id
                ? 'border-accent-blue text-accent-blue bg-accent-blue/5'
                : 'border-transparent text-text-dim hover:text-text-secondary hover:bg-bg-hover'
            )}
          >
            <span className="hidden sm:inline">{tab.label}</span>
            <span className="sm:hidden">{tab.shortLabel}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'staffing' && <StaffingControls />}
        {activeTab === 'autonomy' && <AutonomyControls />}
        {activeTab === 'failover' && <FailoverControls />}
        {activeTab === 'uipath' && <UiPathStatusPanel />}
      </div>
    </div>
  );
}
