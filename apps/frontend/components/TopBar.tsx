'use client';

import { useGameStore } from '@/lib/store';
import GamePhaseIndicator from './panels/GamePhaseIndicator';
import OverlaySelector from './overlays/OverlaySelector';
import AgentBuilderPanel from './panels/AgentBuilderPanel';
import CodeGenModal from './CodeGenModal';
import ApprovalModal from './ApprovalModal';
import clsx from 'clsx';
import { FileText, RotateCcw, Brain, Sparkles, ShieldAlert } from 'lucide-react';

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
  const setReportsOpen = useGameStore((s) => s.setReportsOpen);
  const fetchReports = useGameStore((s) => s.fetchReports);
  const resetScenario = useGameStore((s) => s.resetScenario);
  const setAgentBuilderOpen = useGameStore((s) => s.setAgentBuilderOpen);
  const setCodeGenOpen = useGameStore((s) => s.setCodeGenOpen);
  const setApprovalsOpen = useGameStore((s) => s.setApprovalsOpen);
  const fetchApprovals = useGameStore((s) => s.fetchApprovals);
  const approvalCount = useGameStore((s) => s.approvalCount);
  const activeScenario = useGameStore((s) => s.activeScenario);
  const setScenarioSelected = useGameStore((s) => s.setScenarioSelected);

  function handleOpenReports() {
    setReportsOpen(true);
    fetchReports();
  }

  function handleResetScenario() {
    if (
      window.confirm(
        'Reset the scenario? This will restart the simulation and clear all current progress.'
      )
    ) {
      resetScenario();
    }
  }

  function handleOpenApprovals() {
    fetchApprovals();
    setApprovalsOpen(true);
  }

  return (
    <>
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

          {/* Scenario badge */}
          {activeScenario && (
            <>
              <div className="h-4 w-px bg-border-dim hidden sm:block" />
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: activeScenario.color }}
                />
                <span className="text-text-secondary text-xs font-medium hidden sm:inline">
                  {activeScenario.icon} {activeScenario.name}
                </span>
                <button
                  onClick={() => setScenarioSelected(false)}
                  className="text-xs px-2 py-0.5 rounded border border-border-dim text-text-dim hover:border-border-bright hover:text-text-secondary transition-colors"
                >
                  Change
                </button>
              </div>
            </>
          )}

          <div className="h-4 w-px bg-border-dim hidden sm:block" />

          <GamePhaseIndicator compact />

          <div className="h-4 w-px bg-border-dim hidden md:block" />

          <TickCounter />
        </div>

        {/* Center: Overlay Selector + Reports + New Buttons */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-dim hidden lg:inline">OVERLAY:</span>
            <OverlaySelector compact />
          </div>

          <div className="h-4 w-px bg-border-dim hidden sm:block" />

          <button
            onClick={handleOpenReports}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent-purple/20 border border-accent-purple/40 text-accent-purple text-sm font-medium hover:bg-accent-purple/30 transition-colors"
          >
            <FileText size={14} />
            <span className="hidden sm:inline">Reports</span>
          </button>

          {/* Agent Builder button */}
          <button
            onClick={() => setAgentBuilderOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-300 text-sm font-medium hover:bg-blue-600/30 transition-colors"
          >
            <Brain size={14} />
            <span className="hidden md:inline">Agent Builder</span>
          </button>

          {/* Coding Agent button */}
          <button
            onClick={() => setCodeGenOpen(true)}
            className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.40)',
              color: '#F59E0B',
            }}
          >
            <Sparkles size={14} />
            <span className="hidden md:inline">Coding Agent</span>
            <span
              className="absolute -top-1.5 -right-1.5 text-xs font-bold px-1 rounded"
              style={{ background: '#F59E0B', color: '#1a1a1a', fontSize: '9px', lineHeight: '14px' }}
            >
              AI
            </span>
          </button>

          {/* Approvals button */}
          <button
            onClick={handleOpenApprovals}
            className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-panel border border-border-dim text-text-secondary text-sm font-medium hover:border-border-bright hover:text-text-primary transition-colors"
          >
            <ShieldAlert size={14} />
            <span className="hidden md:inline">Approvals</span>
            {approvalCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-xs font-bold px-1">
                {approvalCount}
              </span>
            )}
          </button>
        </div>

        {/* Right: Connection + Reset + Pause */}
        <div className="flex items-center gap-3">
          <ConnectionDot />

          <button
            onClick={handleResetScenario}
            className="flex items-center gap-1.5 px-2 py-1 rounded border border-border-dim text-text-dim hover:border-accent-danger/50 hover:text-accent-danger text-xs font-mono transition-all hidden md:flex"
            title="Reset Scenario"
          >
            <RotateCcw size={12} />
            <span className="hidden lg:inline">RESET</span>
          </button>

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

      {/* Panels / Modals rendered via TopBar */}
      <AgentBuilderPanel />
      <CodeGenModal />
      <ApprovalModal />
    </>
  );
}
