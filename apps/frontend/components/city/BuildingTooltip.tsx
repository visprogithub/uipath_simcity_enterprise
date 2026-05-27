'use client';

import { useGameStore } from '@/lib/store';
import type { Building } from '@/types/game';
import clsx from 'clsx';

function StatBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <span className="text-text-primary font-mono">{Math.round(value)}%</span>
      </div>
      <div className="h-1.5 bg-bg-base rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Building['status'] }) {
  const config = {
    operational: { label: 'OPERATIONAL', cls: 'bg-accent-success/20 text-accent-success border-accent-success/40' },
    degraded: { label: 'DEGRADED', cls: 'bg-accent-warning/20 text-accent-warning border-accent-warning/40' },
    critical: { label: 'CRITICAL', cls: 'bg-accent-danger/20 text-accent-danger border-accent-danger/40 animate-pulse' },
    offline: { label: 'OFFLINE', cls: 'bg-gray-900 text-gray-400 border-gray-700' },
  };

  const { label, cls } = config[status];
  return (
    <span className={clsx('text-xs font-bold px-2 py-0.5 rounded border font-mono tracking-widest', cls)}>
      {label}
    </span>
  );
}

export default function BuildingTooltip() {
  const selectedBuildingId = useGameStore((s) => s.selectedBuilding);
  const simState = useGameStore((s) => s.simState);
  const selectBuilding = useGameStore((s) => s.selectBuilding);

  if (!selectedBuildingId || !simState) return null;

  const building = simState.buildings.find((b) => b.id === selectedBuildingId);
  if (!building) return null;

  const buildingMap = new Map(simState.buildings.map((b) => [b.id, b]));
  const deps = building.dependencies.map((id) => buildingMap.get(id)).filter(Boolean) as Building[];
  const activeWorkflows = simState.workflows.filter(
    (w) => w.sourceId === building.id || w.destId === building.id
  );

  return (
    <div className="absolute top-4 left-4 z-20 w-64 bg-bg-panel/95 backdrop-blur-sm border border-border-dim rounded-lg shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between p-3 border-b border-border-dim">
        <div className="flex-1 min-w-0">
          <div className="text-text-primary font-bold text-sm truncate">{building.name}</div>
          <div className="text-text-secondary text-xs capitalize mt-0.5">
            {building.type.replace(/_/g, ' ')}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          <StatusBadge status={building.status} />
          <button
            onClick={() => selectBuilding(null)}
            className="text-text-dim hover:text-text-secondary text-lg leading-none"
            aria-label="Close tooltip"
          >
            ×
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="p-3 space-y-2">
        <StatBar label="Health" value={building.health} color="#44ff88" />
        <StatBar label="Throughput" value={building.throughput} color="#00d4ff" />
        <StatBar label="Staffing" value={building.staffingLevel} color="#ffaa00" />
        <StatBar label="Trust" value={building.trustLevel} color="#cc44ff" />
        <StatBar label="Recovery Cap." value={building.recoveryCapacity} color="#00ffcc" />
      </div>

      {/* Queue Depth */}
      <div className="px-3 pb-3">
        <div className="flex justify-between text-xs text-text-secondary">
          <span>Queue Depth</span>
          <span
            className={clsx(
              'font-mono font-bold',
              building.queueDepth > 10
                ? 'text-accent-danger'
                : building.queueDepth > 5
                ? 'text-accent-warning'
                : 'text-accent-success'
            )}
          >
            {building.queueDepth} items
          </span>
        </div>
      </div>

      {/* Dependencies */}
      {deps.length > 0 && (
        <div className="border-t border-border-dim px-3 py-2">
          <div className="text-xs text-text-dim font-semibold mb-1.5 uppercase tracking-wider">
            Dependencies
          </div>
          <div className="space-y-1">
            {deps.map((dep) => (
              <div key={dep.id} className="flex items-center justify-between">
                <span className="text-xs text-text-secondary truncate">{dep.name}</span>
                <span
                  className={clsx(
                    'text-xs font-bold ml-2 shrink-0',
                    dep.status === 'operational'
                      ? 'text-accent-success'
                      : dep.status === 'degraded'
                      ? 'text-accent-warning'
                      : 'text-accent-danger'
                  )}
                >
                  {dep.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active workflows */}
      {activeWorkflows.length > 0 && (
        <div className="border-t border-border-dim px-3 py-2">
          <div className="text-xs text-text-dim font-semibold mb-1 uppercase tracking-wider">
            Active Workflows
          </div>
          <div className="text-xs text-text-secondary">
            {activeWorkflows.length} workflow{activeWorkflows.length !== 1 ? 's' : ''}
            {' '}({activeWorkflows.filter((w) => w.status === 'flowing').length} flowing,{' '}
            {activeWorkflows.filter((w) => w.status === 'blocked').length} blocked)
          </div>
        </div>
      )}
    </div>
  );
}
