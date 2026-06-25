'use client';

import { useState } from 'react';
import { useGameStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { UiPathJob, UiPathApproval } from '@/types/game';
import clsx from 'clsx';

function OrchestrationModeSwitch({
  mode,
  caseProcess,
  connected,
}: {
  mode: 'direct' | 'maestro';
  caseProcess?: string;
  connected: boolean;
}) {
  const [pending, setPending] = useState<'direct' | 'maestro' | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function selectMode(next: 'direct' | 'maestro') {
    if (next === mode || pending) return;
    setPending(next);
    setError(null);
    try {
      const res = await api('/api/orchestration/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: next }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      // The next simulation state push reflects the new mode.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch mode');
    } finally {
      setPending(null);
    }
  }

  const options: { id: 'direct' | 'maestro'; label: string; hint: string }[] = [
    { id: 'direct', label: 'Direct', hint: 'Agents fire individual Orchestrator jobs' },
    { id: 'maestro', label: 'Maestro Case', hint: `Routed through ${caseProcess || 'the Maestro Case'}` },
  ];

  return (
    <div className="bg-bg-card border border-border-dim rounded-lg p-2.5 space-y-2">
      <div className="text-xs text-text-dim font-semibold">Orchestration Mode</div>
      <div className="grid grid-cols-2 gap-1 p-0.5 bg-bg-base rounded-md border border-border-dim">
        {options.map((opt) => {
          const active = mode === opt.id;
          const loading = pending === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => selectMode(opt.id)}
              disabled={!connected || !!pending}
              className={clsx(
                'rounded px-2 py-1.5 text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                active
                  ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40'
                  : 'text-text-dim hover:text-text-primary border border-transparent'
              )}
            >
              {loading ? '…' : opt.label}
            </button>
          );
        })}
      </div>
      <div className="text-xs text-text-dim leading-snug">
        {options.find((o) => o.id === mode)?.hint}
      </div>
      {!connected && (
        <div className="text-xs text-accent-warning">
          Connect UiPath to switch modes.
        </div>
      )}
      {error && <div className="text-xs text-accent-danger">{error}</div>}
    </div>
  );
}

function JobStateTag({ state }: { state: UiPathJob['state'] }) {
  const config = {
    Pending: { cls: 'bg-text-dim/20 text-text-dim', dot: 'bg-text-dim' },
    Running: { cls: 'bg-accent-blue/20 text-accent-blue animate-pulse', dot: 'bg-accent-blue animate-pulse' },
    Successful: { cls: 'bg-accent-success/20 text-accent-success', dot: 'bg-accent-success' },
    Faulted: { cls: 'bg-accent-danger/20 text-accent-danger', dot: 'bg-accent-danger' },
    Stopped: { cls: 'bg-accent-warning/20 text-accent-warning', dot: 'bg-accent-warning' },
  };
  const cfg = config[state] ?? config.Stopped;
  return (
    <span className={clsx('flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-mono', cfg.cls)}>
      <div className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {state}
    </span>
  );
}

function JobCard({ job }: { job: UiPathJob }) {
  const elapsed = Math.floor((Date.now() - job.startedAt) / 1000);
  const elapsedStr =
    elapsed < 60
      ? `${elapsed}s`
      : elapsed < 3600
      ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
      : `${Math.floor(elapsed / 3600)}h`;

  return (
    <div className="bg-bg-base border border-border-dim rounded p-2 space-y-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-text-primary font-mono truncate">{job.processName}</span>
        <JobStateTag state={job.state} />
      </div>
      <div className="flex items-center justify-between text-xs text-text-dim">
        <span>{job.simulationContext}</span>
        <span className="font-mono">{elapsedStr}</span>
      </div>
    </div>
  );
}

function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: UiPathApproval;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const severityConfig = {
    critical: 'border-accent-danger/40 bg-accent-danger/5',
    warning: 'border-accent-warning/30 bg-accent-warning/5',
    info: 'border-border-dim bg-bg-base',
  };

  return (
    <div className={clsx('rounded border p-2 space-y-1.5', severityConfig[approval.severity])}>
      <div>
        <div className="text-xs text-text-primary font-semibold">{approval.title}</div>
        <div className="text-xs text-text-secondary mt-0.5">{approval.description}</div>
        <div className="text-xs text-text-dim mt-0.5">— {approval.requestedBy}</div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onApprove(approval.id)}
          className="flex-1 py-1 rounded text-xs font-bold bg-accent-success/10 text-accent-success border border-accent-success/30 hover:bg-accent-success/20 transition-colors"
        >
          APPROVE
        </button>
        <button
          onClick={() => onReject(approval.id)}
          className="flex-1 py-1 rounded text-xs font-bold bg-accent-danger/10 text-accent-danger border border-accent-danger/30 hover:bg-accent-danger/20 transition-colors"
        >
          REJECT
        </button>
      </div>
    </div>
  );
}

export default function UiPathStatusPanel() {
  const simState = useGameStore((s) => s.simState);
  const sendAction = useGameStore((s) => s.sendAction);

  const uipath = simState?.uipathStatus;

  const handleApprove = (id: string) => {
    // Approval grants the pending workflow
    sendAction({ type: 'acknowledge_alert', alertId: id });
  };

  const handleReject = (id: string) => {
    sendAction({ type: 'acknowledge_alert', alertId: id });
  };

  const lastSyncStr = uipath?.lastSync
    ? (() => {
        const seconds = Math.floor((Date.now() - uipath.lastSync) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        return `${Math.floor(seconds / 60)}m ago`;
      })()
    : 'Never';

  return (
    <div className="space-y-3 p-2">
      <div className="text-xs text-text-dim uppercase tracking-widest font-semibold px-1">
        UiPath Integration
      </div>

      {/* Connection status */}
      <div className="bg-bg-card border border-border-dim rounded-lg p-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={clsx(
                'w-3 h-3 rounded-full',
                uipath?.connected
                  ? 'bg-accent-success shadow-lg animate-pulse'
                  : 'bg-text-dim'
              )}
              style={uipath?.connected ? { boxShadow: '0 0 8px #44ff88' } : {}}
            />
            <span className="text-sm font-bold text-text-primary">
              {uipath?.connected ? 'Connected' : 'Offline'}
            </span>
          </div>
          <span className="text-xs text-text-dim font-mono">Sync: {lastSyncStr}</span>
        </div>
      </div>

      {/* Orchestration mode switch */}
      <OrchestrationModeSwitch
        mode={uipath?.orchestrationMode ?? 'direct'}
        caseProcess={uipath?.maestroCaseProcess}
        connected={!!uipath?.connected}
      />

      {/* Active Jobs */}
      <div className="space-y-1.5">
        <div className="text-xs text-text-dim font-semibold px-1 flex items-center justify-between">
          <span>Active Jobs</span>
          <span className="text-accent-blue font-mono">{uipath?.activeJobs.length ?? 0}</span>
        </div>
        {(uipath?.activeJobs.length ?? 0) === 0 ? (
          <div className="text-xs text-text-dim text-center py-3 bg-bg-card rounded border border-border-dim">
            No active jobs
          </div>
        ) : (
          <div className="space-y-1">
            {uipath!.activeJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>

      {/* Pending Approvals */}
      <div className="space-y-1.5">
        <div className="text-xs text-text-dim font-semibold px-1 flex items-center justify-between">
          <span>Pending Approvals</span>
          {(uipath?.pendingApprovals.length ?? 0) > 0 && (
            <span className="text-accent-danger font-mono animate-pulse">
              {uipath!.pendingApprovals.length} pending
            </span>
          )}
        </div>
        {(uipath?.pendingApprovals.length ?? 0) === 0 ? (
          <div className="text-xs text-text-dim text-center py-3 bg-bg-card rounded border border-border-dim">
            No pending approvals
          </div>
        ) : (
          <div className="space-y-1.5">
            {uipath!.pendingApprovals.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
