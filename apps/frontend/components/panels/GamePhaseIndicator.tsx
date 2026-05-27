'use client';

import { useGameStore } from '@/lib/store';
import type { GamePhase } from '@/types/game';
import clsx from 'clsx';

const PHASE_CONFIG: Record<
  GamePhase,
  { label: string; color: string; bgColor: string; animation: string; icon: string }
> = {
  healthy: {
    label: 'HEALTHY',
    color: 'text-accent-success',
    bgColor: 'bg-accent-success/15 border-accent-success/40',
    animation: 'animate-pulse',
    icon: '●',
  },
  degrading: {
    label: 'DEGRADING',
    color: 'text-accent-warning',
    bgColor: 'bg-accent-warning/15 border-accent-warning/40',
    animation: 'animate-pulse',
    icon: '▼',
  },
  crisis: {
    label: 'CRISIS',
    color: 'text-accent-danger',
    bgColor: 'bg-accent-danger/15 border-accent-danger/50',
    animation: 'animate-pulse-fast',
    icon: '⚠',
  },
  recovering: {
    label: 'RECOVERING',
    color: 'text-accent-blue',
    bgColor: 'bg-accent-blue/15 border-accent-blue/40',
    animation: 'animate-breathe',
    icon: '↑',
  },
  collapsed: {
    label: 'COLLAPSED',
    color: 'text-red-800',
    bgColor: 'bg-red-950/80 border-red-900',
    animation: '',
    icon: '✕',
  },
};

interface GamePhaseIndicatorProps {
  compact?: boolean;
}

export default function GamePhaseIndicator({ compact = false }: GamePhaseIndicatorProps) {
  const simState = useGameStore((s) => s.simState);

  if (!simState) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border-dim bg-bg-card">
        <div className="w-2 h-2 rounded-full bg-text-dim animate-pulse" />
        <span className="text-xs text-text-dim font-mono tracking-widest">INITIALIZING</span>
      </div>
    );
  }

  const phase = simState.phase;
  const cfg = PHASE_CONFIG[phase];

  return (
    <div
      className={clsx(
        'flex items-center gap-2 rounded border font-mono',
        cfg.bgColor,
        compact ? 'px-2 py-1' : 'px-3 py-1.5'
      )}
    >
      <span
        className={clsx(
          cfg.color,
          cfg.animation,
          compact ? 'text-xs' : 'text-sm'
        )}
      >
        {cfg.icon}
      </span>
      <span
        className={clsx(
          'font-bold tracking-widest',
          cfg.color,
          compact ? 'text-xs' : 'text-sm'
        )}
      >
        {cfg.label}
      </span>

      {/* Crisis edge flash effect via a separate element */}
      {phase === 'crisis' && !compact && (
        <div className="fixed inset-0 pointer-events-none z-50 animate-edge-flash rounded" />
      )}
    </div>
  );
}
