'use client';

import { useSimulation } from '@/hooks/useSimulation';
import TopBar from '@/components/TopBar';
import CityCanvas from '@/components/city/CityCanvas';
import BuildingTooltip from '@/components/city/BuildingTooltip';
import MetricsPanel from '@/components/panels/MetricsPanel';
import AlertFeed from '@/components/panels/AlertFeed';
import ControlsPanel from '@/components/panels/ControlsPanel';
import Timeline from '@/components/timeline/Timeline';
import ReportsModal from '@/components/reports/ReportsModal';

export default function GamePage() {
  // Initialize WebSocket connection
  useSimulation();

  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">
      {/* Top bar */}
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
