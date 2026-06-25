'use client';

import { useState, useEffect, useRef } from 'react';
import { X, CheckCircle2, XCircle, Clock, AlertTriangle, ShieldAlert } from 'lucide-react';
import { useGameStore } from '@/lib/store';
import { api } from '@/lib/api';
import clsx from 'clsx';

function CountdownTimer({ autoEscalateAt }: { autoEscalateAt?: number }) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!autoEscalateAt) return;

    function update() {
      const secs = Math.max(0, Math.floor((autoEscalateAt! - Date.now()) / 1000));
      setRemaining(secs);
    }
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [autoEscalateAt]);

  if (remaining === null) return null;

  const urgent = remaining < 30;
  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  return (
    <div className={clsx(
      'flex items-center gap-1.5 text-xs font-mono',
      urgent ? 'text-red-400 animate-pulse' : 'text-yellow-400/70'
    )}>
      <Clock size={11} />
      <span>Auto-escalate in {timeStr}</span>
    </div>
  );
}

function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: any;
  onApprove: (id: string) => void;
  onReject: (id: string, reason: string) => void;
}) {
  const [rejectMode, setRejectMode] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const severityConfig = {
    critical: {
      bg: 'bg-red-950/40',
      border: 'border-red-500/40',
      badge: 'bg-red-500/20 text-red-300 border-red-500/30',
      icon: <ShieldAlert size={14} className="text-red-400" />,
    },
    warning: {
      bg: 'bg-yellow-950/30',
      border: 'border-yellow-500/30',
      badge: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/25',
      icon: <AlertTriangle size={14} className="text-yellow-400" />,
    },
    info: {
      bg: 'bg-white/5',
      border: 'border-white/10',
      badge: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
      icon: <Clock size={14} className="text-blue-400" />,
    },
  };

  const severity = approval.severity ?? 'info';
  const cfg = severityConfig[severity as keyof typeof severityConfig] ?? severityConfig.info;

  return (
    <div className={clsx('rounded-xl border p-4 space-y-3', cfg.bg, cfg.border)}>
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {cfg.icon}
          <span className={clsx('text-xs font-bold px-2 py-0.5 rounded-full border', cfg.badge)}>
            {severity.toUpperCase()}
          </span>
        </div>
        <CountdownTimer autoEscalateAt={approval.autoEscalateAt} />
      </div>

      <div>
        <div className="text-sm font-bold text-white">{approval.title ?? 'Approval Required'}</div>
        <div className="text-xs text-white/60 mt-1 leading-relaxed">{approval.description}</div>
      </div>

      <div className="text-xs text-white/35">
        Requested by: <span className="text-white/55 font-mono">{approval.requestedBy ?? 'VERITAS Compliance Agent'}</span>
      </div>

      {/* Actions */}
      {!rejectMode ? (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onApprove(approval.id)}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold bg-green-600/25 text-green-300 border border-green-500/40 hover:bg-green-600/40 transition-colors"
          >
            <CheckCircle2 size={15} />
            APPROVE
          </button>
          <button
            onClick={() => setRejectMode(true)}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold bg-red-600/20 text-red-300 border border-red-500/35 hover:bg-red-600/35 transition-colors"
          >
            <XCircle size={15} />
            REJECT
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Enter rejection reason..."
            rows={2}
            className="w-full rounded-lg border border-white/15 bg-white/5 text-white text-xs px-3 py-2 focus:outline-none focus:border-red-400/50 resize-none placeholder:text-white/25"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={() => onReject(approval.id, rejectReason)}
              disabled={!rejectReason.trim()}
              className="flex-1 py-2 rounded-lg text-xs font-bold bg-red-600/25 text-red-300 border border-red-500/35 hover:bg-red-600/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Confirm Rejection
            </button>
            <button
              onClick={() => { setRejectMode(false); setRejectReason(''); }}
              className="px-3 py-2 rounded-lg text-xs text-white/50 border border-white/15 hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApprovalModal() {
  const approvalsOpen = useGameStore((s) => s.approvalsOpen);
  const setApprovalsOpen = useGameStore((s) => s.setApprovalsOpen);
  const pendingApprovals = useGameStore((s) => s.pendingApprovals);
  const fetchApprovals = useGameStore((s) => s.fetchApprovals);

  const [localApprovals, setLocalApprovals] = useState<any[]>([]);

  useEffect(() => {
    setLocalApprovals(pendingApprovals);
  }, [pendingApprovals]);

  // Fetch immediately on open and poll while the modal is open so new
  // VERITAS-gated approvals appear without reopening.
  useEffect(() => {
    if (!approvalsOpen) return;
    fetchApprovals();
    const id = setInterval(fetchApprovals, 3000);
    return () => clearInterval(id);
  }, [approvalsOpen, fetchApprovals]);

  if (!approvalsOpen) return null;

  async function handleApprove(id: string) {
    try {
      await api(`/api/approvals/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approvedBy: 'Operator' }),
      });
    } catch {
      // ignore
    }
    setLocalApprovals((prev) => prev.filter((a) => a.id !== id));
    fetchApprovals();
  }

  async function handleReject(id: string, reason: string) {
    try {
      await api(`/api/approvals/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejectedBy: 'Operator', reason }),
      });
    } catch {
      // ignore
    }
    setLocalApprovals((prev) => prev.filter((a) => a.id !== id));
    fetchApprovals();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/75 backdrop-blur-sm"
        onClick={() => setApprovalsOpen(false)}
      />

      {/* Modal */}
      <div
        className="relative z-10 flex flex-col rounded-2xl shadow-2xl overflow-hidden"
        style={{
          width: '560px',
          maxWidth: '95vw',
          maxHeight: '85vh',
          background: '#0d1117',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-red-500/20 border border-red-500/30">
              <ShieldAlert size={16} className="text-red-400" />
            </div>
            <div>
              <div className="text-white font-bold">Human Approvals</div>
              <div className="text-white/40 text-xs">
                {localApprovals.length} pending{localApprovals.length !== 1 ? '' : ''}
              </div>
            </div>
          </div>
          <button
            onClick={() => setApprovalsOpen(false)}
            className="p-2 rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {localApprovals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-white/30 space-y-2">
              <CheckCircle2 size={40} className="opacity-30" />
              <div className="text-sm">No pending approvals</div>
            </div>
          ) : (
            localApprovals.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
