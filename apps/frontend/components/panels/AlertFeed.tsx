'use client';

import { useEffect, useRef } from 'react';
import { useGameStore } from '@/lib/store';
import type { Alert } from '@/types/game';
import clsx from 'clsx';

function AlertItem({
  alert,
  onAcknowledge,
}: {
  alert: Alert;
  onAcknowledge: (id: string) => void;
}) {
  const timeAgo = () => {
    const seconds = Math.floor((Date.now() - alert.timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  };

  const severityConfig = {
    critical: {
      bg: 'bg-accent-danger/10',
      border: 'border-accent-danger/40',
      dot: 'bg-accent-danger',
      text: 'text-accent-danger',
      pulse: true,
    },
    warning: {
      bg: 'bg-accent-warning/10',
      border: 'border-accent-warning/30',
      dot: 'bg-accent-warning',
      text: 'text-accent-warning',
      pulse: false,
    },
    info: {
      bg: 'bg-bg-card',
      border: 'border-border-dim',
      dot: 'bg-text-dim',
      text: 'text-text-secondary',
      pulse: false,
    },
  };

  const cfg = severityConfig[alert.severity];

  return (
    <div
      className={clsx(
        'rounded-lg border p-2.5 transition-all duration-200',
        cfg.bg,
        cfg.border,
        alert.acknowledged && 'opacity-40'
      )}
    >
      <div className="flex items-start gap-2">
        <div className="mt-1 shrink-0">
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              cfg.dot,
              cfg.pulse && !alert.acknowledged && 'animate-pulse'
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className={clsx('text-xs font-medium leading-snug', cfg.text)}>
            {alert.message}
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-text-dim">{timeAgo()}</span>
            {!alert.acknowledged && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="text-xs text-text-dim hover:text-text-secondary border border-border-dim hover:border-border-bright rounded px-1.5 py-0.5 transition-colors"
              >
                ACK
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AlertFeed() {
  const simState = useGameStore((s) => s.simState);
  const sendAction = useGameStore((s) => s.sendAction);
  const scrollRef = useRef<HTMLDivElement>(null);

  const alerts = simState?.alerts ?? [];
  const displayAlerts = alerts.slice(0, 20).reverse();

  // Auto-scroll to top (newest) when new alerts arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [alerts.length]);

  const handleAcknowledge = (alertId: string) => {
    sendAction({ type: 'acknowledge_alert', alertId });
  };

  return (
    <div className="flex flex-col min-h-0 p-2">
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="text-xs text-text-dim uppercase tracking-widest font-semibold">
          Alert Feed
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'text-xs font-mono px-1.5 py-0.5 rounded',
              alerts.filter((a) => a.severity === 'critical' && !a.acknowledged).length > 0
                ? 'bg-accent-danger/20 text-accent-danger animate-pulse'
                : 'bg-bg-card text-text-dim'
            )}
          >
            {alerts.filter((a) => !a.acknowledged).length} active
          </span>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-1.5 scrollbar-thin scrollbar-thumb-border-dim scrollbar-track-transparent pr-0.5"
        style={{ maxHeight: '280px' }}
      >
        {displayAlerts.length === 0 ? (
          <div className="text-center text-text-dim text-xs py-6">
            No active alerts
          </div>
        ) : (
          displayAlerts.map((alert) => (
            <AlertItem
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledge}
            />
          ))
        )}
      </div>
    </div>
  );
}
