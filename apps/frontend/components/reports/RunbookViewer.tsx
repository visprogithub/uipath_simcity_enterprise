'use client';

import { useState } from 'react';
import { Download, CheckCircle, AlertTriangle } from 'lucide-react';
import type { Runbook, RunbookStep } from '@/lib/reports';

function downloadBlob(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'border-accent-danger/60 text-accent-danger bg-accent-danger/10',
  HIGH: 'border-accent-warning/60 text-accent-warning bg-accent-warning/10',
  MEDIUM: 'border-accent-blue/60 text-accent-blue bg-accent-blue/10',
  LOW: 'border-border-bright text-text-secondary bg-bg-panel',
};

const URGENCY_COLORS: Record<string, string> = {
  IMMEDIATE: 'bg-accent-danger/20 text-accent-danger border border-accent-danger/40',
  SHORT_TERM: 'bg-accent-warning/20 text-accent-warning border border-accent-warning/40',
  RECOVERY: 'bg-accent-success/20 text-accent-success border border-accent-success/40',
};

function StepCard({ step }: { step: RunbookStep }) {
  return (
    <div className="rounded-lg border border-border-dim bg-bg-panel p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-text-dim font-bold">
            [{String(step.stepNumber).padStart(2, '0')}]
          </span>
          <span className="text-text-primary font-medium text-sm">{step.action}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${URGENCY_COLORS[step.urgency]}`}>
            {step.urgency.replace('_', ' ')}
          </span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-mono ${
              step.performedBy === 'automated'
                ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/40'
                : 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40'
            }`}
          >
            {step.performedBy}
          </span>
        </div>
      </div>

      {step.detail && (
        <p className="text-text-dim text-xs leading-relaxed pl-8">{step.detail}</p>
      )}

      <div className="flex flex-wrap gap-3 pl-8 text-xs">
        {step.targetSystem && (
          <span className="text-text-secondary">
            <span className="text-text-dim">Target:</span> <span className="font-mono">{step.targetSystem}</span>
          </span>
        )}
        {step.uipathProcess && (
          <span className="text-text-secondary">
            <span className="text-text-dim">UiPath:</span>{' '}
            <span className="font-mono text-accent-orange">{step.uipathProcess}</span>
          </span>
        )}
        {step.automatingAgent && (
          <span className="text-text-secondary">
            <span className="text-text-dim">Agent:</span> <span className="font-mono text-accent-purple">{step.automatingAgent}</span>
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-3 pl-8 text-xs">
        <span className="text-text-secondary">
          <span className="text-text-dim">Effect:</span> {step.expectedEffect}
        </span>
        <span className="text-text-secondary">
          <span className="text-text-dim">Time window:</span>{' '}
          <span className="font-mono">{step.timeWindowMinutes} min</span>
        </span>
        {step.validatedInSimulation && (
          <span className="text-accent-success flex items-center gap-1">
            <CheckCircle size={10} />
            Sim-validated
          </span>
        )}
      </div>
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split('\n');

  return (
    <div className="rounded-lg bg-bg-base border border-border-dim p-4 font-mono text-xs leading-relaxed overflow-x-auto">
      {lines.map((line, i) => {
        if (line.startsWith('# ')) {
          return (
            <div key={i} className="text-accent-blue text-base font-bold mt-4 mb-2">
              {line.slice(2)}
            </div>
          );
        }
        if (line.startsWith('## ')) {
          return (
            <div key={i} className="text-accent-blue text-sm font-bold mt-3 mb-1">
              {line.slice(3)}
            </div>
          );
        }
        if (line.startsWith('### ')) {
          return (
            <div key={i} className="text-accent-teal text-xs font-bold mt-2 mb-1">
              {line.slice(4)}
            </div>
          );
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={i} className="text-text-secondary pl-4">
              <span className="text-accent-blue mr-2">•</span>
              {line.slice(2)}
            </div>
          );
        }
        if (/^\d+\. /.test(line)) {
          const match = line.match(/^(\d+)\. (.*)$/);
          if (match) {
            return (
              <div key={i} className="text-text-secondary pl-4">
                <span className="text-accent-orange mr-2">{match[1]}.</span>
                {match[2]}
              </div>
            );
          }
        }
        if (line.startsWith('```') || line.startsWith('---')) {
          return <div key={i} className="text-border-bright">{line}</div>;
        }
        if (line === '') {
          return <div key={i} className="h-2" />;
        }
        // Inline backtick substitution
        const parts = line.split(/(`[^`]+`)/g);
        return (
          <div key={i} className="text-text-secondary">
            {parts.map((part, j) =>
              part.startsWith('`') && part.endsWith('`') ? (
                <span key={j} className="text-accent-blue bg-accent-blue/10 px-1 rounded">
                  {part.slice(1, -1)}
                </span>
              ) : (
                part
              )
            )}
          </div>
        );
      })}
    </div>
  );
}

interface Props {
  runbook: Runbook;
}

export default function RunbookViewer({ runbook }: Props) {
  const [viewMode, setViewMode] = useState<'structured' | 'markdown'>('structured');

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-text-primary font-bold text-lg">{runbook.title}</h2>
            {runbook.validated ? (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-accent-success/20 text-accent-success border border-accent-success/40 text-xs">
                <CheckCircle size={10} />
                SIMULATION VALIDATED
              </span>
            ) : (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-accent-warning/20 text-accent-warning border border-accent-warning/40 text-xs">
                <AlertTriangle size={10} />
                PARTIAL
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-text-dim font-mono">
            <span>Scenario: {runbook.scenarioId}</span>
            <span>Est. Recovery: {runbook.estimatedRecoveryMinutes} min</span>
            <span>ID: {runbook.runbookId}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() =>
              downloadBlob(runbook.markdownContent, `runbook-${runbook.runbookId}.md`, 'text/markdown')
            }
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-border-dim hover:bg-border-bright text-text-secondary hover:text-text-primary text-xs transition-colors"
          >
            <Download size={12} />
            Markdown
          </button>
          <button
            onClick={() =>
              downloadBlob(
                JSON.stringify(runbook, null, 2),
                `runbook-${runbook.runbookId}.json`,
                'application/json'
              )
            }
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-border-dim hover:bg-border-bright text-text-secondary hover:text-text-primary text-xs transition-colors"
          >
            <Download size={12} />
            JSON
          </button>
        </div>
      </div>

      {/* Sub-nav */}
      <div className="flex gap-1 p-1 rounded-lg bg-bg-base border border-border-dim w-fit">
        {(['structured', 'markdown'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-4 py-1.5 rounded text-xs font-medium capitalize transition-colors ${
              viewMode === mode
                ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40'
                : 'text-text-dim hover:text-text-secondary'
            }`}
          >
            {mode}
          </button>
        ))}
      </div>

      {viewMode === 'markdown' ? (
        <MarkdownRenderer content={runbook.markdownContent} />
      ) : (
        <div className="space-y-6">
          {/* Trigger Conditions */}
          {runbook.triggerConditions.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-4">Trigger Conditions</h3>
              <div className="flex flex-wrap gap-3">
                {runbook.triggerConditions.map((tc, i) => (
                  <div
                    key={i}
                    className={`rounded-lg border p-3 min-w-[160px] ${SEVERITY_COLORS[tc.severity] ?? SEVERITY_COLORS['LOW']}`}
                  >
                    <div className="font-mono text-xs font-bold mb-1">{tc.metric}</div>
                    <div className="text-xs">
                      Threshold: <span className="font-mono">{tc.threshold}</span>
                    </div>
                    <div className="text-xs">
                      Observed: <span className="font-mono font-bold">{tc.observedValue}</span>
                    </div>
                    <div className="text-xs mt-1 font-bold uppercase">{tc.severity}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Escalation Chain */}
          {runbook.escalationChain.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-4">Escalation Chain</h3>
              <div className="space-y-0">
                {runbook.escalationChain.map((level, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-3 h-3 rounded-full bg-accent-orange border-2 border-accent-orange/50 shrink-0 mt-1" />
                      {i < runbook.escalationChain.length - 1 && (
                        <div className="w-0.5 flex-1 bg-border-dim my-1" />
                      )}
                    </div>
                    <div className="pb-4 min-w-0">
                      <div className="text-text-primary font-medium text-sm">
                        Level {level.level}: {level.triggerCondition}
                      </div>
                      <div className="text-xs text-text-dim mt-1 space-y-0.5">
                        <div>
                          ↓ UiPath:{' '}
                          <span className="text-accent-orange font-mono">{level.uipathProcess}</span>
                        </div>
                        <div>
                          ↓ Automated by:{' '}
                          <span className="text-accent-purple font-mono">{level.automatedBy}</span>
                        </div>
                        <div className="text-text-secondary">{level.action}</div>
                        {level.outcome && (
                          <div className="text-accent-success text-xs italic">{level.outcome}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Response Steps */}
          {runbook.immediateActions.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-3 flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-accent-danger/20 text-accent-danger border border-accent-danger/40 text-xs font-mono">
                  IMMEDIATE
                </span>
                Immediate Actions
              </h3>
              <div className="space-y-2">
                {runbook.immediateActions.map((s) => (
                  <StepCard key={s.stepNumber} step={s} />
                ))}
              </div>
            </div>
          )}

          {runbook.shortTermActions.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-3 flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-accent-warning/20 text-accent-warning border border-accent-warning/40 text-xs font-mono">
                  SHORT TERM
                </span>
                Short Term Actions
              </h3>
              <div className="space-y-2">
                {runbook.shortTermActions.map((s) => (
                  <StepCard key={s.stepNumber} step={s} />
                ))}
              </div>
            </div>
          )}

          {runbook.recoveryActions.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-3 flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-accent-success/20 text-accent-success border border-accent-success/40 text-xs font-mono">
                  RECOVERY
                </span>
                Recovery Actions
              </h3>
              <div className="space-y-2">
                {runbook.recoveryActions.map((s) => (
                  <StepCard key={s.stepNumber} step={s} />
                ))}
              </div>
            </div>
          )}

          {/* Recovery Milestones */}
          {runbook.recoveryMilestones.length > 0 && (
            <div className="rounded-xl border border-border-dim bg-bg-card p-5">
              <h3 className="text-text-primary font-bold text-sm mb-4">Recovery Milestones</h3>
              <div className="space-y-2">
                {runbook.recoveryMilestones.map((m, i) => (
                  <div
                    key={i}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      m.status === 'achieved'
                        ? 'border-accent-success/30 bg-accent-success/5'
                        : 'border-border-dim bg-bg-panel'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`text-sm ${m.status === 'achieved' ? 'text-accent-success' : 'text-text-dim'}`}>
                        {m.status === 'achieved' ? '✓' : '○'}
                      </span>
                      <span className="text-text-secondary text-sm">{m.milestone}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="text-text-dim">Target: {m.targetMinutes} min</span>
                      {m.achievedTick !== null && (
                        <span className="text-accent-success">Tick {m.achievedTick}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
