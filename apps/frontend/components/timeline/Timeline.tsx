'use client';

import { useRef, useEffect } from 'react';
import { useGameStore } from '@/lib/store';
import type { SimulationEvent, SimulationEventType } from '@/types/game';
import clsx from 'clsx';

const EVENT_COLORS: Record<SimulationEventType, string> = {
  outage_started: '#ff4444',
  outage_recovered: '#44ff88',
  escalation_triggered: '#ff8800',
  approval_required: '#ffaa00',
  approval_granted: '#44ff88',
  agent_action: '#00ffff',
  player_action: '#ffff00',
  failover_activated: '#ff8800',
  trust_drop: '#cc44ff',
  staffing_overload: '#ff8800',
  uipath_job_started: '#cc44ff',
  uipath_job_completed: '#cc44ff',
  cascade_propagated: '#ff2222',
};

const EVENT_LABELS: Record<SimulationEventType, string> = {
  outage_started: 'Outage',
  outage_recovered: 'Recovery',
  escalation_triggered: 'Escalation',
  approval_required: 'Approval Req',
  approval_granted: 'Approved',
  agent_action: 'Agent Act',
  player_action: 'Player',
  failover_activated: 'Failover',
  trust_drop: 'Trust Drop',
  staffing_overload: 'Staffing OL',
  uipath_job_started: 'UiP Start',
  uipath_job_completed: 'UiP Done',
  cascade_propagated: 'Cascade',
};

function EventDot({
  event,
  onClick,
  selected,
}: {
  event: SimulationEvent;
  onClick: () => void;
  selected: boolean;
}) {
  const color = EVENT_COLORS[event.type] ?? '#888';
  const label = EVENT_LABELS[event.type] ?? event.type;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex flex-col items-center gap-1 min-w-[60px] group transition-all',
        selected && 'scale-110'
      )}
      title={`Tick ${event.tick}: ${label}`}
    >
      {/* Tick label */}
      <span
        className={clsx(
          'text-xs font-mono transition-colors',
          selected ? 'text-text-primary' : 'text-text-dim group-hover:text-text-secondary'
        )}
      >
        T{event.tick}
      </span>

      {/* Dot */}
      <div className="relative">
        <div
          className={clsx(
            'w-3 h-3 rounded-full border-2 transition-all',
            selected ? 'scale-125' : 'group-hover:scale-110'
          )}
          style={{
            backgroundColor: `${color}44`,
            borderColor: color,
            boxShadow: selected ? `0 0 8px ${color}` : undefined,
          }}
        />
      </div>

      {/* Event label */}
      <span
        className={clsx(
          'text-xs leading-tight text-center transition-colors w-14 truncate',
          selected ? 'font-semibold' : 'text-text-dim group-hover:text-text-secondary'
        )}
        style={{ color: selected ? color : undefined }}
      >
        {label}
      </span>
    </button>
  );
}

export default function Timeline() {
  const simState = useGameStore((s) => s.simState);
  const selectBuilding = useGameStore((s) => s.selectBuilding);
  const scrollRef = useRef<HTMLDivElement>(null);
  const selectedEventRef = useRef<string | null>(null);

  const events = simState?.recentEvents?.slice(-50) ?? [];

  // Auto-scroll to the end (latest events) when new events come in
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [events.length]);

  const handleEventClick = (event: SimulationEvent) => {
    selectedEventRef.current = event.id;
    // Highlight the affected building if there is one
    const buildingId = event.data?.buildingId as string | undefined;
    if (buildingId) {
      selectBuilding(buildingId);
    }
  };

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-dim text-xs">
        No events yet — simulation initializing...
      </div>
    );
  }

  // Group events by tick for x-axis
  const tickGroups = new Map<number, SimulationEvent[]>();
  for (const event of events) {
    if (!tickGroups.has(event.tick)) tickGroups.set(event.tick, []);
    tickGroups.get(event.tick)!.push(event);
  }

  return (
    <div className="flex h-full">
      {/* Legend */}
      <div className="shrink-0 border-r border-border-dim px-3 flex flex-col justify-center gap-1 min-w-[80px]">
        <div className="text-xs text-text-dim font-semibold uppercase tracking-widest">Events</div>
        <div className="text-xs font-mono text-text-secondary">
          Last {events.length}
        </div>
      </div>

      {/* Scrollable timeline */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-x-auto overflow-y-hidden"
      >
        <div className="flex items-center gap-4 h-full px-4 min-w-max">
          {/* Horizontal connector line */}
          <div className="relative flex items-center gap-2 h-full">
            {/* Base line */}
            <div className="absolute top-1/2 left-0 right-0 h-px bg-border-dim -translate-y-1/2" />

            {/* Events */}
            {events.map((event) => (
              <EventDot
                key={event.id}
                event={event}
                onClick={() => handleEventClick(event)}
                selected={selectedEventRef.current === event.id}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Current tick indicator */}
      {simState && (
        <div className="shrink-0 border-l border-border-dim px-3 flex flex-col justify-center">
          <div className="text-xs text-text-dim">Now</div>
          <div className="text-sm font-bold font-mono text-accent-blue">
            T{simState.tick}
          </div>
        </div>
      )}
    </div>
  );
}
