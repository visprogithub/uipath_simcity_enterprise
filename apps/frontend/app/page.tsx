'use client';

import { useEffect, useRef } from 'react';
import { useSimulation } from '@/hooks/useSimulation';
import TopBar from '@/components/TopBar';
import CityCanvas from '@/components/city/CityCanvas';
import BuildingTooltip from '@/components/city/BuildingTooltip';
import MetricsPanel from '@/components/panels/MetricsPanel';
import AlertFeed from '@/components/panels/AlertFeed';
import ControlsPanel from '@/components/panels/ControlsPanel';
import Timeline from '@/components/timeline/Timeline';
import ReportsModal from '@/components/reports/ReportsModal';
import ScenarioSelector from '@/components/ScenarioSelector';
import { useGameStore } from '@/lib/store';

function StuckWorkflowsBadge() {
  const simState = useGameStore((s) => s.simState);
  const setApprovalsOpen = useGameStore((s) => s.setApprovalsOpen);
  const fetchApprovals = useGameStore((s) => s.fetchApprovals);

  if (!simState) return null;

  const stuck = simState.workflows.filter(
    (w) => w.status === 'queued' || w.status === 'blocked'
  );
  if (stuck.length === 0) return null;

  // Two very different reasons a workflow is stuck — and they need different
  // actions. Awaiting-approval ones are unblocked by a human decision (opens the
  // Approvals modal); infrastructure-blocked ones are waiting on a building to
  // recover and are cleared with Failover / Restore, NOT by opening Approvals.
  const awaitingApproval = stuck.filter((w) => w.awaitingApproval);
  const infraBlocked = stuck.filter((w) => !w.awaitingApproval);

  function openApprovals() {
    fetchApprovals();
    setApprovalsOpen(true);
  }

  return (
    <div className="absolute top-2 left-2 z-10 flex items-center gap-2">
      {awaitingApproval.length > 0 && (
        <button
          onClick={openApprovals}
          title="These workflows are paused for a human decision — click to review approvals."
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold animate-pulse bg-accent-warning/15 border border-accent-warning/45 text-accent-warning hover:bg-accent-warning/25 transition-colors"
        >
          <span>&#9995;</span>
          {awaitingApproval.length} awaiting approval
        </button>
      )}
      {infraBlocked.length > 0 && (
        <div
          title="Waiting on infrastructure to recover — use Activate Failover or Restore Building to clear these."
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-accent-danger/15 border border-accent-danger/45 text-accent-danger cursor-default"
        >
          <span>&#9888;</span>
          {infraBlocked.length} blocked &middot; infrastructure
        </div>
      )}
    </div>
  );
}

export default function GamePage() {
  // Initialize WebSocket connection
  useSimulation();

  const simState = useGameStore((s) => s.simState);
  const isPaused = useGameStore((s) => s.isPaused);
  const fetchApprovals = useGameStore((s) => s.fetchApprovals);
  const setApprovalsOpen = useGameStore((s) => s.setApprovalsOpen);
  const approvalsOpen = useGameStore((s) => s.approvalsOpen);

  const scenarioSelected = useGameStore((s) => s.scenarioSelected);
  const scenarioLoading = useGameStore((s) => s.scenarioLoading);
  const availableScenarios = useGameStore((s) => s.availableScenarios);
  const fetchScenarios = useGameStore((s) => s.fetchScenarios);

  // Fetch scenarios on mount
  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  // Poll for approvals every 5 seconds when simulation is running
  useEffect(() => {
    if (isPaused) return;
    fetchApprovals();
    const id = setInterval(() => {
      fetchApprovals();
    }, 5000);
    return () => clearInterval(id);
  }, [isPaused, fetchApprovals]);

  // Auto-show approvals modal when there's an unacknowledged critical alert
  const prevCriticalRef = useRef(false);
  useEffect(() => {
    if (!simState) return;
    const hasCritical = simState.alerts.some(
      (a) => a.severity === 'critical' && !a.acknowledged
    );
    if (hasCritical && !prevCriticalRef.current && !approvalsOpen) {
      fetchApprovals();
      setApprovalsOpen(true);
    }
    prevCriticalRef.current = hasCritical;
  }, [simState, approvalsOpen, fetchApprovals, setApprovalsOpen]);

  // Show scenario selector if no scenario is selected
  if (!scenarioSelected) {
    return <ScenarioSelector />;
  }

  // Full-screen loading state while a scenario is being loaded
  if (scenarioLoading) {
    return (
      <div
        className="flex flex-col items-center justify-center h-screen"
        style={{ background: '#0F172A' }}
      >
        <div className="w-10 h-10 rounded-full border-2 border-accent-blue border-t-transparent animate-spin mb-4" />
        <p className="text-text-secondary text-lg">Loading scenario...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">
      {/* Top bar (includes AgentBuilderPanel, CodeGenModal, ApprovalModal) */}
      <TopBar />
      <ReportsModal />

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel */}
        <aside
          className="flex flex-col bg-bg-panel border-r border-border-dim overflow-y-auto"
          style={{ minWidth: '240px', width: '260px', maxWidth: '300px' }}
        >
          <MetricsPanel />
          <div className="border-t border-border-dim" />
          <AlertFeed />
        </aside>

        {/* Center: City canvas */}
        <main className="flex-1 relative min-w-0 bg-bg-base overflow-hidden">
          <CityCanvas className="w-full h-full" />
          <BuildingTooltip />
          <StuckWorkflowsBadge />
        </main>

        {/* Right panel */}
        <aside
          className="flex flex-col bg-bg-panel overflow-hidden"
          style={{ minWidth: '280px', width: '300px', maxWidth: '340px' }}
        >
          <ControlsPanel />
        </aside>
      </div>

      {/* Bottom timeline */}
      <footer
        className="border-t border-border-dim bg-bg-panel shrink-0"
        style={{ height: '96px' }}
      >
        <Timeline />
      </footer>
    </div>
  );
}
