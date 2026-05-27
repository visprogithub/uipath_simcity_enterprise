'use client';

import { useGameStore } from '@/lib/store';
import type { OverlayMode } from '@/types/game';
import clsx from 'clsx';

interface OverlayOption {
  mode: OverlayMode;
  label: string;
  shortLabel: string;
  color: string;
}

const OVERLAYS: OverlayOption[] = [
  { mode: 'none', label: 'None', shortLabel: 'Off', color: '#8899bb' },
  { mode: 'dependency', label: 'Dependencies', shortLabel: 'Dep', color: '#00d4ff' },
  { mode: 'congestion', label: 'Congestion', shortLabel: 'Cong', color: '#ff8800' },
  { mode: 'trust', label: 'Trust', shortLabel: 'Trust', color: '#cc44ff' },
  { mode: 'staffing', label: 'Staffing', shortLabel: 'Staff', color: '#44ff88' },
  { mode: 'outage', label: 'Outage', shortLabel: 'Out', color: '#ff4444' },
  { mode: 'orchestration', label: 'Orchestration', shortLabel: 'Orch', color: '#00ffcc' },
];

// Icon per overlay mode
const OVERLAY_ICONS: Record<OverlayMode, string> = {
  none: '◯',
  dependency: '→',
  congestion: '▣',
  trust: '◈',
  staffing: '◧',
  outage: '⚠',
  orchestration: '⟲',
};

interface OverlaySelectorProps {
  compact?: boolean;
}

export default function OverlaySelector({ compact = false }: OverlaySelectorProps) {
  const overlayMode = useGameStore((s) => s.overlayMode);
  const setOverlayMode = useGameStore((s) => s.setOverlayMode);

  return (
    <div className="flex items-center gap-1">
      {OVERLAYS.map((opt) => {
        const active = overlayMode === opt.mode;
        return (
          <button
            key={opt.mode}
            onClick={() => setOverlayMode(opt.mode)}
            title={opt.label}
            className={clsx(
              'flex items-center gap-1 rounded border transition-all font-mono',
              compact ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs',
              active
                ? 'border-current font-bold'
                : 'border-border-dim text-text-dim hover:border-border-bright hover:text-text-secondary'
            )}
            style={
              active
                ? {
                    color: opt.color,
                    borderColor: opt.color,
                    backgroundColor: `${opt.color}18`,
                  }
                : {}
            }
          >
            <span>{OVERLAY_ICONS[opt.mode]}</span>
            {!compact && <span className="hidden lg:inline">{opt.shortLabel}</span>}
          </button>
        );
      })}
    </div>
  );
}
