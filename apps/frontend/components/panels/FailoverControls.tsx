'use client';

import { useState, useCallback } from 'react';
import { useGameStore } from '@/lib/store';
import clsx from 'clsx';

export default function FailoverControls() {
  const simState = useGameStore((s) => s.simState);
  const sendAction = useGameStore((s) => s.sendAction);

  const [outageBuilding, setOutageBuilding] = useState('');
  const [outageSeverity, setOutageSeverity] = useState<'partial' | 'full'>('partial');
  const [confirmOutage, setConfirmOutage] = useState(false);

  const [failoverBuilding, setFailoverBuilding] = useState('');
  const [restoreBuilding, setRestoreBuilding] = useState('');

  const [uipathProcess, setUipathProcess] = useState('');
  const [uipathSent, setUipathSent] = useState(false);

  const buildings = simState?.buildings ?? [];
  const nonOperational = buildings.filter((b) => b.status !== 'operational');

  const handleTriggerOutage = useCallback(() => {
    if (!outageBuilding) return;
    if (!confirmOutage) {
      setConfirmOutage(true);
      return;
    }
    sendAction({
      type: 'trigger_outage',
      buildingId: outageBuilding,
      severity: outageSeverity,
    });
    setConfirmOutage(false);
    setOutageBuilding('');
  }, [outageBuilding, outageSeverity, confirmOutage, sendAction]);

  const handleActivateFailover = useCallback(() => {
    if (!failoverBuilding) return;
    sendAction({ type: 'activate_failover', targetBuildingId: failoverBuilding });
    setFailoverBuilding('');
  }, [failoverBuilding, sendAction]);

  const handleRestore = useCallback(() => {
    if (!restoreBuilding) return;
    sendAction({ type: 'restore_building', buildingId: restoreBuilding });
    setRestoreBuilding('');
  }, [restoreBuilding, sendAction]);

  const handleUiPath = useCallback(() => {
    if (!uipathProcess.trim()) return;
    sendAction({
      type: 'trigger_uipath',
      processName: uipathProcess.trim(),
      inputArgs: {},
    });
    setUipathSent(true);
    setTimeout(() => setUipathSent(false), 3000);
    setUipathProcess('');
  }, [uipathProcess, sendAction]);

  const selectClass =
    'w-full bg-bg-base border border-border-dim rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-blue/60 transition-colors';

  return (
    <div className="space-y-3 p-2">
      <div className="text-xs text-text-dim uppercase tracking-widest font-semibold px-1 mb-2">
        Emergency Controls
      </div>

      {/* Trigger Outage */}
      <div className="bg-bg-card border border-accent-danger/20 rounded-lg p-2.5 space-y-2">
        <div className="text-xs font-semibold text-accent-danger">Trigger Outage</div>
        <select
          value={outageBuilding}
          onChange={(e) => {
            setOutageBuilding(e.target.value);
            setConfirmOutage(false);
          }}
          className={selectClass}
        >
          <option value="">Select building...</option>
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          {(['partial', 'full'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setOutageSeverity(sev)}
              className={clsx(
                'flex-1 py-1 rounded text-xs border transition-all',
                outageSeverity === sev
                  ? 'border-accent-danger text-accent-danger bg-accent-danger/10'
                  : 'border-border-dim text-text-dim hover:border-border-bright'
              )}
            >
              {sev.charAt(0).toUpperCase() + sev.slice(1)}
            </button>
          ))}
        </div>
        <button
          onClick={handleTriggerOutage}
          disabled={!outageBuilding}
          className={clsx(
            'w-full py-1.5 rounded text-xs font-bold transition-all border',
            confirmOutage
              ? 'bg-accent-danger text-white border-accent-danger animate-pulse'
              : 'bg-accent-danger/10 text-accent-danger border-accent-danger/40 hover:bg-accent-danger/20',
            !outageBuilding && 'opacity-40 cursor-not-allowed'
          )}
        >
          {confirmOutage ? 'CLICK AGAIN TO CONFIRM' : 'TRIGGER OUTAGE'}
        </button>
        {confirmOutage && (
          <button
            onClick={() => setConfirmOutage(false)}
            className="w-full py-1 text-xs text-text-dim hover:text-text-secondary"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Activate Failover */}
      <div className={clsx(
        'bg-bg-card border rounded-lg p-2.5 space-y-2 transition-colors',
        simState?.failoverActive ? 'border-accent-success/50' : 'border-accent-warning/20'
      )}>
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-accent-warning">Activate Failover</div>
          {simState?.failoverActive ? (
            <div className="flex items-center gap-1.5 text-xs font-bold text-accent-success">
              <span className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
              ENGAGED
            </div>
          ) : (
            <span className="text-xs text-text-dim">standby</span>
          )}
        </div>
        {simState?.failoverActive && (
          <div className="text-[10px] text-text-dim leading-snug">
            Backup carrying load · recovery capacity {Math.round(simState.recoveryCapacity ?? 0)}%
          </div>
        )}
        <select
          value={failoverBuilding}
          onChange={(e) => setFailoverBuilding(e.target.value)}
          className={selectClass}
        >
          <option value="">Select target building...</option>
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name} ({b.status})
            </option>
          ))}
        </select>
        <button
          onClick={handleActivateFailover}
          disabled={!failoverBuilding}
          className={clsx(
            'w-full py-1.5 rounded text-xs font-bold border transition-all',
            'bg-accent-warning/10 text-accent-warning border-accent-warning/40 hover:bg-accent-warning/20',
            !failoverBuilding && 'opacity-40 cursor-not-allowed'
          )}
        >
          ACTIVATE FAILOVER
        </button>
      </div>

      {/* Restore Building */}
      <div className="bg-bg-card border border-accent-success/20 rounded-lg p-2.5 space-y-2">
        <div className="text-xs font-semibold text-accent-success">Restore Building</div>
        <select
          value={restoreBuilding}
          onChange={(e) => setRestoreBuilding(e.target.value)}
          className={selectClass}
        >
          <option value="">Select building to restore...</option>
          {nonOperational.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name} ({b.status})
            </option>
          ))}
        </select>
        <button
          onClick={handleRestore}
          disabled={!restoreBuilding}
          className={clsx(
            'w-full py-1.5 rounded text-xs font-bold border transition-all',
            'bg-accent-success/10 text-accent-success border-accent-success/40 hover:bg-accent-success/20',
            !restoreBuilding && 'opacity-40 cursor-not-allowed'
          )}
        >
          RESTORE BUILDING
        </button>
      </div>

      {/* UiPath Manual Trigger */}
      <div className="bg-bg-card border border-accent-purple/20 rounded-lg p-2.5 space-y-2">
        <div className="text-xs font-semibold text-accent-purple">UiPath Manual Trigger</div>
        <input
          type="text"
          value={uipathProcess}
          onChange={(e) => setUipathProcess(e.target.value)}
          placeholder="Process name..."
          className="w-full bg-bg-base border border-border-dim rounded px-2 py-1.5 text-xs text-text-primary placeholder:text-text-dim focus:outline-none focus:border-accent-purple/60 transition-colors"
          onKeyDown={(e) => e.key === 'Enter' && handleUiPath()}
        />
        <button
          onClick={handleUiPath}
          disabled={!uipathProcess.trim()}
          className={clsx(
            'w-full py-1.5 rounded text-xs font-bold border transition-all',
            uipathSent
              ? 'bg-accent-success/20 text-accent-success border-accent-success/40'
              : 'bg-accent-purple/10 text-accent-purple border-accent-purple/40 hover:bg-accent-purple/20',
            !uipathProcess.trim() && 'opacity-40 cursor-not-allowed'
          )}
        >
          {uipathSent ? '✓ TRIGGERED' : 'TRIGGER PROCESS'}
        </button>

        {/* UiPath connection indicator */}
        <div className="flex items-center gap-1.5 text-xs">
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              simState?.uipathStatus.connected
                ? 'bg-accent-success animate-pulse'
                : 'bg-text-dim'
            )}
          />
          <span className="text-text-dim">
            UiPath {simState?.uipathStatus.connected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
    </div>
  );
}
