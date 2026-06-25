'use client';

import { useCallback } from 'react';
import { useGameStore } from '@/lib/store';
import { elapsedSeconds } from '@/lib/time';
import type { Agent, AutonomyLevel } from '@/types/game';
import clsx from 'clsx';

const LEVEL_LABELS: Record<AutonomyLevel, string> = {
  0: 'Manual',
  1: 'Advisory',
  2: 'Routine',
  3: 'Dynamic',
  4: 'Full Auto',
};

const LEVEL_COLORS: Record<AutonomyLevel, string> = {
  0: '#4a5a7a',
  1: '#007acc',
  2: '#0099cc',
  3: '#00bbcc',
  4: '#44ff88',
};

const AGENT_TYPE_LABELS: Record<Agent['type'], string> = {
  operations_coordinator: 'Ops Coord',
  incident_response: 'Incident Resp',
  compliance: 'Compliance',
  communications: 'Comms',
  executive_strategy: 'Exec Strategy',
};

const STATUS_COLORS: Record<Agent['status'], string> = {
  idle: 'text-text-dim',
  analyzing: 'text-accent-blue',
  acting: 'text-accent-success',
  escalating: 'text-accent-warning',
  blocked: 'text-accent-danger',
};

function AgentAutonomyCard({
  agent,
  onAutonomyChange,
}: {
  agent: Agent;
  onAutonomyChange: (agentId: string, level: AutonomyLevel) => void;
}) {
  const color = LEVEL_COLORS[agent.autonomyLevel];

  const timeAgo = () => {
    const seconds = elapsedSeconds(agent.lastActionAt);
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m`;
  };

  return (
    <div className="bg-bg-card border border-border-dim rounded-lg p-2.5 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              agent.status === 'idle' ? 'bg-text-dim' : 'animate-pulse',
              agent.status === 'acting' ? 'bg-accent-success' :
              agent.status === 'analyzing' ? 'bg-accent-blue' :
              agent.status === 'escalating' ? 'bg-accent-warning' :
              agent.status === 'blocked' ? 'bg-accent-danger' : 'bg-text-dim'
            )}
          />
          <span className="text-xs text-text-secondary font-medium">
            {agent.name}
          </span>
        </div>
        <span className={clsx('text-xs font-mono', STATUS_COLORS[agent.status])}>
          {agent.status.toUpperCase()}
        </span>
      </div>

      {/* Trust score */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-dim">Trust:</span>
        <div className="flex-1 h-1 bg-bg-base rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${agent.trustScore}%`,
              backgroundColor: agent.trustScore > 60 ? '#cc44ff' : agent.trustScore > 30 ? '#ffaa00' : '#ff4444',
            }}
          />
        </div>
        <span className="text-xs font-mono text-text-secondary">{Math.round(agent.trustScore)}</span>
      </div>

      {/* Autonomy level buttons */}
      <div className="space-y-1">
        <div className="text-xs text-text-dim">Autonomy Level</div>
        <div className="flex gap-1">
          {([0, 1, 2, 3, 4] as AutonomyLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => onAutonomyChange(agent.id, level)}
              className={clsx(
                'flex-1 py-1 rounded text-xs font-mono transition-all border',
                agent.autonomyLevel === level
                  ? 'border-current font-bold'
                  : 'border-border-dim text-text-dim hover:border-border-bright hover:text-text-secondary'
              )}
              style={
                agent.autonomyLevel === level
                  ? { color: LEVEL_COLORS[level], borderColor: LEVEL_COLORS[level], backgroundColor: `${LEVEL_COLORS[level]}18` }
                  : {}
              }
              title={LEVEL_LABELS[level]}
            >
              {level}
            </button>
          ))}
        </div>
        <div className="text-center text-xs font-mono" style={{ color }}>
          {LEVEL_LABELS[agent.autonomyLevel]}
        </div>
      </div>

      {/* Last action */}
      {agent.lastAction && (
        <div className="border-t border-border-dim pt-1.5">
          <div className="text-xs text-text-dim leading-snug">
            <span className="text-text-secondary">{timeAgo()} ago:</span>{' '}
            {agent.lastAction.slice(0, 60)}
            {agent.lastAction.length > 60 ? '...' : ''}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AutonomyControls() {
  const simState = useGameStore((s) => s.simState);
  const sendAction = useGameStore((s) => s.sendAction);

  const handleAutonomyChange = useCallback(
    (agentId: string, level: AutonomyLevel) => {
      sendAction({ type: 'set_autonomy', agentId, level });
    },
    [sendAction]
  );

  const handleGlobalAutonomy = useCallback(
    (level: AutonomyLevel) => {
      sendAction({ type: 'set_autonomy', level });
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
        Agent Autonomy
      </div>

      {/* Global control */}
      <div className="bg-bg-panel border border-accent-blue/20 rounded-lg p-2.5 mb-3">
        <div className="text-xs text-accent-blue font-semibold mb-2">Global Override</div>
        <div className="flex gap-1">
          {([0, 1, 2, 3, 4] as AutonomyLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => handleGlobalAutonomy(level)}
              className="flex-1 py-1 rounded text-xs border border-border-dim text-text-dim hover:border-accent-blue/50 hover:text-accent-blue transition-all"
              title={`Set all agents to ${LEVEL_LABELS[level]}`}
            >
              {level}
            </button>
          ))}
        </div>
        <div className="text-xs text-text-dim mt-1 text-center">Set all agents</div>
      </div>

      {simState.agents.map((agent) => (
        <AgentAutonomyCard
          key={agent.id}
          agent={agent}
          onAutonomyChange={handleAutonomyChange}
        />
      ))}
    </div>
  );
}
