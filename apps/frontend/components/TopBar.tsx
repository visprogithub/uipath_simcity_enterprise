'use client';

import { useGameStore } from '@/lib/store';
import GamePhaseIndicator from './panels/GamePhaseIndicator';
import OverlaySelector from './overlays/OverlaySelector';
import clsx from 'clsx';

function ConnectionDot() {
  const status = useGameStore((s) => s.connectionStatus);
  const config = {
    connected: { color: 'bg-accent-success', label: 'Connected', pulse: true },
    connecting: { color: 'bg-accent-warning', label: 'Connecting', pulse: true },
    disconnected: { color: 'bg-accent-danger', label: 'Disconnected', pulse: false },
  };
  const cfg = config[status];
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={clsx(
          'w-2 h-2 rounded-full',
          cfg.color,
          cfg.pulse && 'animate-pulse'
        )}
      />
      <span className="text-xs text-text-dim hidden sm:inline">{cfg.label}</span>
    </div>
  );
}

function TickCounter() {
  const simState = useGameStore((s) => s.simState);
  if (!simState) return null;

  const elapsed = Math.floor(simState.timestamp / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return (
    <div className="flex items-center gap-3 font-mono text-xs text-text-secondary">
      <div className="flex items-center gap-1.5">
        <span className="text-text-dim">TICK</span>
        <span className="text-accent-blue font-bold">{simState.tick.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-text-dim">T+</span>
        <span className="text-text-primary">{timeStr}</span>
      </div>
    </div>
  );
}

export default function TopBar() {
  const isPaused = useGameStore((s) => s.isPaused);
  const togglePause = useGameStore((s) => s.togglePause);

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-bg-panel border-b border-border-dim shrink-0 z-30">
      {/* Left: Logo */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-accent-blue/20 border border-accent-blue/40 flex items-center justify-center">
            <span className="text-accent-blue text-xs font-bold">M</span>
          </div>
          <span className="text-text-primary font-bold text-sm tracking-widest font-mono hidden sm:inline">
            MAESTRO CITY
          </span>
        </div>

        <div className="h-4 w-px bg-border-dim hidden sm:block" />

        <GamePhaseIndicator compact />

        <div className="h-4 w-px bg-border-dim hidden md:block" />

        <TickCounter />
      </div>

      {/* Center: Overlay Selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-dim hidden lg:inline">OVERLAY:</span>
        <OverlaySelector compact />
      </div>

      {/* Right: Connection + Pause */}
      <div className="flex items-center gap-3">
        <ConnectionDot />

        <button
          onClick={togglePause}
          className={clsx(
            'flex items-center gap-1.5 px-2 py-1 rounded border text-xs font-mono font-bold transition-all',
            isPaused
              ? 'border-accent-warning text-accent-warning bg-accent-warning/10 hover:bg-accent-warning/20'
              : 'border-border-dim text-text-secondary hover:border-border-bright hover:text-text-primary'
          )}
        >
          {isPaused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>
    </header>
  );
}
