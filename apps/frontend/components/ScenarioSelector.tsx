'use client';

import { useState } from 'react';
import { useGameStore } from '@/lib/store';
import type { ScenarioInfo } from '@/lib/store';
import { api } from '@/lib/api';

const SLOT_ORDER = ['primary', 'secondary', 'infra', 'comms', 'orchestration', 'support', 'failover'] as const;
const AGENT_ROLES = ['ops_coord', 'incident_resp', 'compliance', 'comms', 'exec_strategy'] as const;
const AGENT_LABELS: Record<string, string> = {
  ops_coord: 'Operations', incident_resp: 'Incident Response', compliance: 'Compliance',
  comms: 'Communications', exec_strategy: 'Executive',
};

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

function CreateScenarioCard({ onClick }: { onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="rounded-2xl border-2 border-dashed bg-bg-card/40 p-6 flex flex-col items-center justify-center gap-3 transition-all duration-200 cursor-pointer min-h-[260px]"
      style={{
        borderColor: hovered ? '#6366F1' : '#2a3555',
        transform: hovered ? 'translateY(-4px)' : 'translateY(0)',
      }}
    >
      <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
        style={{ background: '#6366F122', border: '1px solid #6366F144' }}>
        ✨
      </div>
      <h3 className="text-text-primary font-bold text-lg">Create Custom Scenario</h3>
      <p className="text-text-dim text-sm text-center">Describe any industry — AI builds a full simulation you can review and launch.</p>
    </button>
  );
}

function CreateScenarioModal({ onClose, onLaunched }: { onClose: () => void; onLaunched: (id: string) => Promise<void> }) {
  const [stage, setStage] = useState<'input' | 'generating' | 'preview' | 'launching'>('input');
  const [description, setDescription] = useState('');
  const [spec, setSpec] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setError(null);
    setStage('generating');
    try {
      const res = await api('/api/scenario/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
      });
      if (!res.ok) {
        const t = await res.text();
        let msg = t;
        try { msg = JSON.parse(t).detail || t; } catch { /* keep raw */ }
        throw new Error(msg);
      }
      const data = await res.json();
      setSpec(data.spec);
      setStage('preview');
    } catch (e: any) {
      setError(e.message || 'Generation failed');
      setStage('input');
    }
  }

  async function launch() {
    setError(null);
    setStage('launching');
    try {
      const res = await api('/api/scenario/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spec }),
      });
      if (!res.ok) {
        const t = await res.text();
        let msg = t;
        try { msg = JSON.parse(t).detail || t; } catch { /* keep raw */ }
        throw new Error(msg);
      }
      const { id } = await res.json();
      await onLaunched(id);
    } catch (e: any) {
      setError(e.message || 'Launch failed');
      setStage('preview');
    }
  }

  const setField = (k: string, v: any) => setSpec((s: any) => ({ ...s, [k]: v }));
  const setSlot = (role: string, k: string, v: string) =>
    setSpec((s: any) => ({ ...s, slots: { ...s.slots, [role]: { ...s.slots[role], [k]: v } } }));
  const setAgent = (role: string, v: string) =>
    setSpec((s: any) => ({ ...s, agents: { ...s.agents, [role]: v } }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="bg-bg-card border border-border-dim rounded-2xl w-full max-w-2xl max-h-[88vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-text-primary">✨ Create Custom Scenario</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text-primary text-xl">✕</button>
        </div>

        {error && <div className="mb-3 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</div>}

        {(stage === 'input' || stage === 'generating') && (
          <div className="space-y-3">
            <p className="text-text-secondary text-sm">Describe the enterprise you want to simulate. The AI fleshes it into 7 systems, 5 agents, realistic compliance frameworks, and outage presets.</p>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. A busy international airport managing flights, baggage, and ground crews during a winter storm"
              rows={4}
              className="w-full rounded-lg bg-bg-panel border border-border-dim p-3 text-sm text-text-primary focus:border-accent-blue outline-none"
            />
            <button
              onClick={generate}
              disabled={stage === 'generating' || !description.trim()}
              className="w-full py-2.5 rounded-lg text-sm font-semibold bg-accent-blue/20 border border-accent-blue/50 text-accent-blue disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {stage === 'generating' ? (<><span className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />Generating…</>) : 'Generate Scenario →'}
            </button>
          </div>
        )}

        {stage !== 'input' && stage !== 'generating' && spec && (
          <div className="space-y-4">
            <div className="grid grid-cols-[auto_1fr] gap-3 items-center">
              <input value={spec.icon} onChange={(e) => setField('icon', e.target.value)} className="w-12 text-center text-2xl rounded-lg bg-bg-panel border border-border-dim p-2" />
              <input value={spec.name} onChange={(e) => setField('name', e.target.value)} className="rounded-lg bg-bg-panel border border-border-dim p-2 text-text-primary font-bold" />
            </div>
            <textarea value={spec.tagline} onChange={(e) => setField('tagline', e.target.value)} rows={2} className="w-full rounded-lg bg-bg-panel border border-border-dim p-2 text-sm text-text-secondary" />

            <div>
              <div className="text-xs uppercase text-text-dim mb-2">7 Systems</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SLOT_ORDER.map((role) => spec.slots?.[role] && (
                  <div key={role} className="flex items-center gap-2">
                    <input value={spec.slots[role].icon} onChange={(e) => setSlot(role, 'icon', e.target.value)} className="w-10 text-center rounded bg-bg-panel border border-border-dim p-1.5" />
                    <input value={spec.slots[role].name} onChange={(e) => setSlot(role, 'name', e.target.value)} className="flex-1 min-w-0 rounded bg-bg-panel border border-border-dim p-1.5 text-sm text-text-primary" />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase text-text-dim mb-2">5 Agents</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {AGENT_ROLES.map((role) => (
                  <div key={role} className="flex items-center gap-2">
                    <span className="text-xs text-text-dim w-28 shrink-0">{AGENT_LABELS[role]}</span>
                    <input value={spec.agents?.[role] ?? ''} onChange={(e) => setAgent(role, e.target.value)} className="flex-1 min-w-0 rounded bg-bg-panel border border-border-dim p-1.5 text-sm text-text-primary" />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {(spec.compliance_frameworks ?? []).map((fw: string) => (
                <span key={fw} className="text-xs px-2 py-0.5 rounded-full bg-bg-panel border border-border-dim text-text-dim">{fw}</span>
              ))}
            </div>

            <div className="flex gap-3 pt-2">
              <button onClick={() => setStage('input')} className="flex-1 py-2.5 rounded-lg text-sm font-semibold border border-border-dim text-text-secondary">↻ Regenerate</button>
              <button onClick={launch} disabled={stage === 'launching'} className="flex-1 py-2.5 rounded-lg text-sm font-semibold bg-accent-orange/20 border border-accent-orange/50 text-accent-orange disabled:opacity-50 flex items-center justify-center gap-2">
                {stage === 'launching' ? (<><span className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />Launching…</>) : 'Create & Launch →'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ScenarioSelector() {
  const availableScenarios = useGameStore((s) => s.availableScenarios);
  const scenarioLoading = useGameStore((s) => s.scenarioLoading);
  const selectScenario = useGameStore((s) => s.selectScenario);
  const fetchScenarios = useGameStore((s) => s.fetchScenarios);

  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  async function handleSelect(id: string) {
    setLoadingId(id);
    await selectScenario(id);
    setLoadingId(null);
  }

  async function handleLaunched(id: string) {
    await fetchScenarios();   // refresh so the new scenario card shows on return
    setShowCreate(false);
    await handleSelect(id);
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
        {showSkeletons && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-accent-blue/30 bg-accent-blue/10 px-4 py-3">
            <span className="mt-0.5 w-4 h-4 rounded-full border-2 border-accent-blue border-t-transparent animate-spin shrink-0" />
            <p className="text-sm text-text-secondary leading-relaxed">
              <span className="font-semibold text-text-primary">Waking up the backend…</span>{' '}
              The demo backend runs on a free tier that sleeps after inactivity, so the first load can take up to{' '}
              <span className="font-semibold text-text-primary">~50 seconds</span> to spin up. Your scenarios will appear
              here automatically — this is expected, not an error.
            </p>
          </div>
        )}
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
          {!showSkeletons && <CreateScenarioCard onClick={() => setShowCreate(true)} />}
        </div>

        {/* Empty state (not loading, no scenarios) — usually the free-tier cold start */}
        {!scenarioLoading && availableScenarios.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-text-secondary text-lg mb-2">Still waking the backend up…</p>
            <p className="text-text-dim text-sm max-w-md mb-4 leading-relaxed">
              The demo backend runs on a free tier that sleeps after inactivity and can take up to ~50 seconds to spin up
              on first load (or the request may have just timed out). Give it a moment and retry — it's waking, not broken.
            </p>
            <button
              onClick={() => fetchScenarios()}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent-blue/20 border border-accent-blue/50 text-accent-blue transition-colors hover:bg-accent-blue/30"
            >
              ↻ Retry
            </button>
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

      {showCreate && (
        <CreateScenarioModal onClose={() => setShowCreate(false)} onLaunched={handleLaunched} />
      )}
    </div>
  );
}
