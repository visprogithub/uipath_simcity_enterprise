'use client';

import { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight, Loader2, Brain, Zap } from 'lucide-react';
import { useGameStore } from '@/lib/store';
import clsx from 'clsx';

const AGENT_TABS = ['ARIA', 'SENTINEL', 'VERITAS', 'ECHO', 'APEX'] as const;
type AgentTab = (typeof AGENT_TABS)[number];

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded bg-white/5',
        className
      )}
    />
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <SkeletonBlock className="h-16 w-full" />
      <SkeletonBlock className="h-6 w-1/2" />
      <SkeletonBlock className="h-24 w-full" />
      <SkeletonBlock className="h-6 w-1/3" />
      <div className="flex gap-2">
        <SkeletonBlock className="h-6 w-20" />
        <SkeletonBlock className="h-6 w-24" />
        <SkeletonBlock className="h-6 w-16" />
      </div>
      <SkeletonBlock className="h-6 w-1/3" />
      <div className="flex gap-2">
        <SkeletonBlock className="h-6 w-28" />
        <SkeletonBlock className="h-6 w-20" />
      </div>
      <SkeletonBlock className="h-8 w-full" />
    </div>
  );
}

function AutonomyBar({ level }: { level: number }) {
  const labels = ['Manual', 'Supervised', 'Semi-Auto', 'Mostly-Auto', 'Full-Auto'];
  const colors = [
    'bg-gray-400',
    'bg-blue-400',
    'bg-yellow-400',
    'bg-orange-400',
    'bg-green-400',
  ];

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={clsx(
              'flex-1 h-2 rounded-full transition-all',
              i <= level ? colors[level] : 'bg-white/10'
            )}
          />
        ))}
      </div>
      <div className="text-xs text-white/50">{labels[level] ?? `Level ${level}`}</div>
    </div>
  );
}

function AgentDetail({ agent }: { agent: any }) {
  const [systemPromptOpen, setSystemPromptOpen] = useState(false);
  const [orchestrationFlowOpen, setOrchestrationFlowOpen] = useState(false);
  const [orchFlow, setOrchFlow] = useState<any>(null);
  const [orchLoading, setOrchLoading] = useState(false);

  async function handleOrchestrationFlow() {
    if (!orchestrationFlowOpen && !orchFlow) {
      setOrchLoading(true);
      try {
        const res = await fetch('/api/agent-builder/orchestration-flow');
        if (res.ok) {
          const data = await res.json();
          setOrchFlow(data);
        }
      } catch {
        // ignore
      } finally {
        setOrchLoading(false);
      }
    }
    setOrchestrationFlowOpen((v) => !v);
  }

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-48 text-white/30 text-sm">
        Agent data unavailable
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4 overflow-y-auto flex-1">
      {/* Agent card */}
      <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1">
        <div className="font-bold text-white text-base">{agent.name ?? agent.id}</div>
        <div className="text-xs text-white/60">{agent.description ?? 'No description available.'}</div>
      </div>

      {/* Orchestrated badge */}
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
        style={{ background: 'rgba(250,70,22,0.15)', color: '#FA4616', border: '1px solid rgba(250,70,22,0.35)' }}>
        <Zap size={11} />
        Orchestrated by Maestro
      </div>

      {/* System Prompt */}
      <div>
        <button
          onClick={() => setSystemPromptOpen((v) => !v)}
          className="w-full flex items-center justify-between text-xs font-semibold text-white/70 uppercase tracking-widest py-1.5 hover:text-white transition-colors"
        >
          <span>System Prompt</span>
          {systemPromptOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        {systemPromptOpen && (
          <pre className="mt-1 text-xs text-green-300/80 bg-black/40 border border-white/10 rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono max-h-48 overflow-y-auto">
            {agent.systemPrompt ?? 'No system prompt defined.'}
          </pre>
        )}
      </div>

      {/* Tools */}
      {agent.tools && agent.tools.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-white/70 uppercase tracking-widest mb-2">Tools</div>
          <div className="space-y-1.5">
            {agent.tools.map((tool: any, i: number) => (
              <div key={i} className="flex items-start gap-2 rounded bg-white/5 border border-white/10 px-2.5 py-1.5">
                <span className="text-xs font-mono font-bold text-blue-300 shrink-0">{tool.name ?? tool}</span>
                {tool.description && (
                  <span className="text-xs text-white/40">{tool.description}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trigger Conditions */}
      {agent.triggerConditions && agent.triggerConditions.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-white/70 uppercase tracking-widest mb-2">Trigger Conditions</div>
          <div className="flex flex-wrap gap-1.5">
            {agent.triggerConditions.map((cond: string, i: number) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-xs bg-blue-500/15 text-blue-300 border border-blue-500/25"
              >
                {cond}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* UiPath Processes */}
      {agent.uipathProcesses && agent.uipathProcesses.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-white/70 uppercase tracking-widest mb-2">UiPath Processes</div>
          <div className="flex flex-wrap gap-1.5">
            {agent.uipathProcesses.map((proc: string, i: number) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-xs font-mono"
                style={{ background: 'rgba(250,70,22,0.12)', color: '#FA8050', border: '1px solid rgba(250,70,22,0.25)' }}
              >
                {proc}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Autonomy Level */}
      {agent.autonomyLevel !== undefined && (
        <div>
          <div className="text-xs font-semibold text-white/70 uppercase tracking-widest mb-2">Autonomy Level</div>
          <AutonomyBar level={agent.autonomyLevel} />
        </div>
      )}

      {/* Orchestration Flow button */}
      <div className="pt-2 border-t border-white/10">
        <button
          onClick={handleOrchestrationFlow}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-semibold transition-colors"
          style={{
            background: orchestrationFlowOpen ? 'rgba(250,70,22,0.18)' : 'rgba(250,70,22,0.08)',
            color: '#FA6030',
            border: '1px solid rgba(250,70,22,0.30)',
          }}
        >
          <span>Orchestration Flow</span>
          {orchLoading
            ? <Loader2 size={14} className="animate-spin" />
            : orchestrationFlowOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          }
        </button>

        {orchestrationFlowOpen && orchFlow && (
          <div className="mt-2 rounded-lg border border-white/10 bg-black/30 p-3 space-y-2">
            {Array.isArray(orchFlow.phases)
              ? orchFlow.phases.map((phase: any, i: number) => (
                  <div key={i} className="space-y-1">
                    <div className="text-xs font-bold text-white/70">{phase.name ?? `Phase ${i + 1}`}</div>
                    {phase.rules && phase.rules.map((rule: string, j: number) => (
                      <div key={j} className="text-xs text-white/45 pl-2 border-l border-white/10">{rule}</div>
                    ))}
                  </div>
                ))
              : (
                <pre className="text-xs text-white/50 whitespace-pre-wrap font-mono">
                  {JSON.stringify(orchFlow, null, 2)}
                </pre>
              )
            }
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentBuilderPanel() {
  const agentBuilderOpen = useGameStore((s) => s.agentBuilderOpen);
  const setAgentBuilderOpen = useGameStore((s) => s.setAgentBuilderOpen);
  const agentBuilderData = useGameStore((s) => s.agentBuilderData);
  const fetchAgentBuilder = useGameStore((s) => s.fetchAgentBuilder);

  const [activeTab, setActiveTab] = useState<AgentTab>('ARIA');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (agentBuilderOpen && !agentBuilderData) {
      setLoading(true);
      fetchAgentBuilder().finally(() => setLoading(false));
    }
  }, [agentBuilderOpen, agentBuilderData, fetchAgentBuilder]);

  if (!agentBuilderOpen) return null;

  // Find the selected agent from agentBuilderData
  const agents: any[] = agentBuilderData?.agents ?? agentBuilderData ?? [];
  const selectedAgent = Array.isArray(agents)
    ? agents.find((a: any) =>
        (a.name ?? a.id ?? '').toUpperCase().includes(activeTab)
      )
    : null;

  return (
    <div
      className="fixed top-0 right-0 h-full z-50 flex flex-col shadow-2xl"
      style={{ width: '400px', background: '#0d1117', borderLeft: '1px solid rgba(255,255,255,0.08)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 shrink-0 border-b border-white/10"
        style={{ background: 'rgba(250,70,22,0.08)' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded flex items-center justify-center font-bold text-sm"
            style={{ background: '#FA4616', color: 'white' }}
          >
            U
          </div>
          <div>
            <div className="text-white font-bold text-sm">Agent Builder</div>
            <div className="text-white/40 text-xs">UiPath Maestro</div>
          </div>
        </div>
        <button
          onClick={() => setAgentBuilderOpen(false)}
          className="p-1.5 rounded hover:bg-white/10 text-white/50 hover:text-white transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Agent tabs */}
      <div className="flex border-b border-white/10 shrink-0">
        {AGENT_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'flex-1 py-2 text-xs font-bold tracking-wide transition-all border-b-2',
              activeTab === tab
                ? 'border-[#FA4616] text-[#FA6030]'
                : 'border-transparent text-white/40 hover:text-white/70'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSkeleton />
      ) : (
        <AgentDetail agent={selectedAgent} />
      )}
    </div>
  );
}
