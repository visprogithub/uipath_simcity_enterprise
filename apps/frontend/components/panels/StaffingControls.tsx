'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useGameStore } from '@/lib/store';
import type { Building } from '@/types/game';
import clsx from 'clsx';

function StaffingSlider({
  building,
  onStaffingChange,
}: {
  building: Building;
  onStaffingChange: (buildingId: string, level: number) => void;
}) {
  const [localLevel, setLocalLevel] = useState(building.staffingLevel);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync with server-side value when it changes significantly
  useEffect(() => {
    setLocalLevel(building.staffingLevel);
  }, [building.staffingLevel]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const level = Number(e.target.value);
      setLocalLevel(level);

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        onStaffingChange(building.id, level);
      }, 500);
    },
    [building.id, onStaffingChange]
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const getColor = (level: number) => {
    if (level >= 70) return '#44ff88';
    if (level >= 40) return '#ffaa00';
    return '#ff4444';
  };

  const color = getColor(localLevel);

  return (
    <div className="bg-bg-card border border-border-dim rounded-lg p-2.5 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-secondary truncate pr-2">{building.name}</span>
        <span className="text-xs font-mono font-bold shrink-0" style={{ color }}>
          {Math.round(localLevel)}%
        </span>
      </div>

      {/* Level indicator dots */}
      <div className="flex gap-1">
        {[20, 40, 60, 80, 100].map((mark) => (
          <div
            key={mark}
            className="flex-1 h-1 rounded-full transition-colors"
            style={{
              backgroundColor: localLevel >= mark ? color : '#1a2035',
            }}
          />
        ))}
      </div>

      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={localLevel}
        onChange={handleChange}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, ${color} ${localLevel}%, #1a2035 ${localLevel}%)`,
          accentColor: color,
        }}
      />

      {/* Status indicator */}
      <div className="flex items-center gap-1.5 text-xs">
        <div
          className={clsx(
            'w-1.5 h-1.5 rounded-full',
            building.status === 'operational'
              ? 'bg-accent-success animate-pulse'
              : building.status === 'degraded'
              ? 'bg-accent-warning'
              : 'bg-accent-danger'
          )}
        />
        <span className="text-text-dim capitalize">{building.status}</span>
      </div>
    </div>
  );
}

export default function StaffingControls() {
  const simState = useGameStore((s) => s.simState);
  const sendAction = useGameStore((s) => s.sendAction);

  const handleStaffingChange = useCallback(
    (buildingId: string, level: number) => {
      sendAction({ type: 'set_staffing', buildingId, level });
    },
    [sendAction]
  );

  if (!simState) {
    return (
      <div className="p-2 text-xs text-text-dim text-center">
        Awaiting simulation data...
      </div>
    );
  }

  return (
    <div className="space-y-1.5 p-2">
      <div className="text-xs text-text-dim uppercase tracking-widest font-semibold px-1 mb-2">
        Staffing Levels
      </div>
      {simState.buildings.map((building) => (
        <StaffingSlider
          key={building.id}
          building={building}
          onStaffingChange={handleStaffingChange}
        />
      ))}
    </div>
  );
}
