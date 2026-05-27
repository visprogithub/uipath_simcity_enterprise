'use client';

import { X, RotateCcw, Loader2 } from 'lucide-react';
import { useGameStore } from '@/lib/store';
import AfterActionReportView from './AfterActionReport';
import RunbookViewer from './RunbookViewer';
import CalibrationScore from './CalibrationScore';
import ProcessTemplates from './ProcessTemplates';

const TABS = [
  { id: 'after-action', label: 'After-Action' },
  { id: 'runbook', label: 'Runbook' },
  { id: 'calibration', label: 'Calibration' },
  { id: 'templates', label: 'Templates' },
] as const;

export default function ReportsModal() {
  const reportsOpen = useGameStore((s) => s.reportsOpen);
  const activeReportTab = useGameStore((s) => s.activeReportTab);
  const reportsLoading = useGameStore((s) => s.reportsLoading);
  const reportsError = useGameStore((s) => s.reportsError);
  const afterActionReport = useGameStore((s) => s.afterActionReport);
  const runbook = useGameStore((s) => s.runbook);
  const calibration = useGameStore((s) => s.calibration);
  const processTemplates = useGameStore((s) => s.processTemplates);
  const setReportsOpen = useGameStore((s) => s.setReportsOpen);
  const setActiveReportTab = useGameStore((s) => s.setActiveReportTab);
  const resetScenario = useGameStore((s) => s.resetScenario);

  if (!reportsOpen) return null;

  function handleReset() {
    if (
      window.confirm(
        'Reset the scenario? This will restart the simulation and clear all current progress.'
      )
    ) {
      resetScenario();
      setReportsOpen(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-stretch">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-bg-base/95 backdrop-blur-sm"
        onClick={() => setReportsOpen(false)}
      />

      {/* Modal card */}
      <div className="relative z-10 m-4 flex flex-col flex-1 bg-bg-panel border border-border-dim rounded-xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-dim shrink-0 bg-bg-card">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-accent-purple/20 border border-accent-purple/40 flex items-center justify-center">
              <span className="text-accent-purple text-xs font-bold">R</span>
            </div>
            <span className="text-text-primary font-bold text-sm tracking-widest font-mono">
              MAESTRO CITY REPORTS
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-accent-danger/40 text-accent-danger bg-accent-danger/10 hover:bg-accent-danger/20 text-xs font-medium transition-colors"
            >
              <RotateCcw size={12} />
              Reset Scenario
            </button>

            <button
              onClick={() => setReportsOpen(false)}
              className="p-1.5 rounded-lg hover:bg-bg-hover text-text-dim hover:text-text-primary transition-colors"
              aria-label="Close reports"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex items-center gap-1 px-6 py-3 border-b border-border-dim shrink-0 bg-bg-card">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveReportTab(tab.id)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeReportTab === tab.id
                  ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/40'
                  : 'text-text-dim hover:text-text-secondary hover:bg-bg-hover'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto min-h-0 relative">
          {/* Loading overlay */}
          {reportsLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg-base/80 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={32} className="text-accent-purple animate-spin" />
                <span className="text-text-secondary text-sm font-mono">Loading reports...</span>
              </div>
            </div>
          )}

          {/* Error banner */}
          {reportsError && !reportsLoading && (
            <div className="m-6 p-4 rounded-xl border border-accent-danger/50 bg-accent-danger/10 text-accent-danger text-sm">
              <span className="font-bold">Error loading reports:</span> {reportsError}
            </div>
          )}

          {/* Tab content */}
          {!reportsLoading && !reportsError && (
            <>
              {activeReportTab === 'after-action' &&
                (afterActionReport ? (
                  <AfterActionReportView report={afterActionReport} />
                ) : (
                  <EmptyState label="After-Action Report" />
                ))}

              {activeReportTab === 'runbook' &&
                (runbook ? (
                  <RunbookViewer runbook={runbook} />
                ) : (
                  <EmptyState label="Runbook" />
                ))}

              {activeReportTab === 'calibration' &&
                (calibration ? (
                  <CalibrationScore certificate={calibration} />
                ) : (
                  <EmptyState label="Calibration Certificate" />
                ))}

              {activeReportTab === 'templates' &&
                (processTemplates ? (
                  <ProcessTemplates templates={processTemplates} />
                ) : (
                  <EmptyState label="Process Templates" />
                ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-64 text-text-dim">
      <div className="text-center space-y-2">
        <div className="text-4xl opacity-30">◫</div>
        <div className="text-sm">{label} not yet loaded</div>
      </div>
    </div>
  );
}
