'use client';

import { useState } from 'react';
import { useGameStore } from '@/lib/store';
import type { ScenarioInfo } from '@/lib/store';

function SkeletonCard() {
  return (
    <div
      className="rounded-2xl border border-border-dim bg-bg-card p-6 animate-pulse"
      style={{ minHeight: '260px' }}
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="w-12 h-12 rounded-xl bg-bg-hover shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-5 bg-bg-hover rounded w-2/3" />
          <div className="h-3 bg-bg-hover rounded w-1/3" />
        </div>
      </div>
      <div className="space-y-2 mb-4">
        <div className="h-3 bg-bg-hover rounded w-full" />
        <div className="h-3 bg-bg-hover rounded w-5/6" />
      </div>
      <div className="flex gap-2 mb-4">
        <div className="h-5 bg-bg-hover rounded-full w-16" />
        <div className="h-5 bg-bg-hover rounded-full w-20" />
        <div className="h-5 bg-bg-hover rounded-full w-14" />
      </div>
      <div className="flex gap-4 mb-5">
        <div className="h-4 bg-bg-hover rounded w-20" />
        <div className="h-4 bg-bg-hover rounded w-20" />
      </div>
      <div className="h-9 bg-bg-hover rounded-lg w-full" />
    </div>
  );
}

interface ScenarioCardProps {
  scenario: ScenarioInfo;
  isLoading: boolean;
  onSelect: (id: string) => void;
}

function ScenarioCard({ scenario, isLoading, onSelect }: ScenarioCardProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="rounded-2xl border bg-bg-card p-6 flex flex-col transition-all duration-200 cursor-pointer"
      style={{
        borderColor: hovered ? scenario.color : '#2a3555',
        borderLeftColor: scenario.color,
        borderLeftWidth: '3px',
        transform: hovered ? 'translateY(-4px)' : 'translateY(0)',
        boxShadow: hovered
          ? `0 8px 32px ${scenario.color}33, 0 0 0 1px ${scenario.color}22`
          : 'none',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Header row */}
      <div className="flex items-start gap-4 mb-3">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0"
          style={{ background: `${scenario.color}22`, border: `1px solid ${scenario.color}44` }}
        >
          {scenario.icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-text-primary font-bold text-lg leading-tight">{scenario.name}</h3>
          <span
            className="inline-block text-xs font-medium px-2 py-0.5 rounded-full mt-1"
            style={{ background: `${scenario.color}22`, color: scenario.color, border: `1px solid ${scenario.color}44` }}
          >
            {scenario.industry}
          </span>
        </div>
      </div>

      {/* Tagline */}
      <p className="text-text-secondary text-sm leading-relaxed mb-3 line-clamp-2 flex-1">
        {scenario.tagline}
      </p>

      {/* Compliance frameworks */}
      {scenario.complianceFrameworks.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {scenario.complianceFrameworks.map((fw) => (
            <span
              key={fw}
              className="text-xs px-2 py-0.5 rounded-full bg-bg-panel border border-border-dim text-text-dim"
            >
              {fw}
            </span>
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 mb-4 text-xs text-text-dim">
        <div className="flex items-center gap-1.5">
          <span style={{ color: scenario.color }}>⬡</span>
          <span>{scenario.buildingCount} buildings</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span style={{ color: scenario.color }}>◈</span>
          <span>{scenario.agentCount} agents</span>
        </div>
      </div>

      {/* Launch button */}
      <button
        onClick={() => onSelect(scenario.id)}
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
        style={{
          background: hovered ? `${scenario.color}22` : 'transparent',
          border: `1px solid ${hovered ? scenario.color : '#2a3555'}`,
          color: hovered ? scenario.color : '#8899bb',
        }}
      >
        {isLoading ? (
          <>
            <span className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
            Loading...
          </>
        ) : (
          <>
            Launch Simulation
            <span>→</span>
          </>
        )}
      </button>
    </div>
  );
}

export default function ScenarioSelector() {
  const availableScenarios = useGameStore((s) => s.availableScenarios);
  const scenarioLoading = useGameStore((s) => s.scenarioLoading);
  const selectScenario = useGameStore((s) => s.selectScenario);

  const [loadingId, setLoadingId] = useState<string | null>(null);

  async function handleSelect(id: string) {
    setLoadingId(id);
    await selectScenario(id);
    setLoadingId(null);
  }

  const showSkeletons = scenarioLoading && availableScenarios.length === 0;

  return (
    <div
      className="flex flex-col min-h-screen overflow-y-auto"
      style={{ background: '#0F172A' }}
    >
      {/* Header */}
      <div className="flex flex-col items-center pt-16 pb-10 px-6 text-center">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-accent-blue/20 border border-accent-blue/40 flex items-center justify-center">
            <span className="text-accent-blue text-lg font-bold">M</span>
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">Maestro City</h1>
        </div>
        <p className="text-text-secondary text-lg max-w-xl">
          Select your enterprise scenario to begin the simulation
        </p>
      </div>

      {/* Grid */}
      <div className="flex-1 px-6 pb-10 max-w-6xl mx-auto w-full">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
          {showSkeletons
            ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
            : availableScenarios.map((scenario) => (
                <ScenarioCard
                  key={scenario.id}
                  scenario={scenario}
                  isLoading={loadingId === scenario.id}
                  onSelect={handleSelect}
                />
              ))}
        </div>

        {/* Empty state (not loading, no scenarios) */}
        {!scenarioLoading && availableScenarios.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-text-dim text-lg mb-2">No scenarios available</p>
            <p className="text-text-dim text-sm">Make sure the backend is running and reachable</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="shrink-0 py-6 flex items-center justify-center border-t border-border-dim">
        <p className="text-text-dim text-sm">
          Powered by{' '}
          <span className="text-accent-orange font-semibold">UiPath Automation Platform</span>
        </p>
      </footer>
    </div>
  );
}
