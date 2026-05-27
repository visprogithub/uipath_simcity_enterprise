'use client';

import { Download } from 'lucide-react';
import type { AfterActionReport } from '@/lib/reports';

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function recommendationIcon(text: string): string {
  const lower = text.toLowerCase();
  if (lower.includes('autonom') || lower.includes('agent')) return '⚡';
  if (lower.includes('staff') || lower.includes('team') || lower.includes('human')) return '👥';
  return '🔄';
}

const METRIC_LABELS: Record<string, string> = {
  operationalStability: 'Operational Stability',
  humanStrain: 'Human Strain',
  systemLoad: 'System Load',
  citizenSatisfaction: 'Citizen Satisfaction',
  infrastructureHealth: 'Infrastructure Health',
  automationCoverage: 'Automation Coverage',
};

// For these metrics, lower is better (inverted)
const INVERTED_METRICS = new Set(['humanStrain', 'systemLoad']);

function metricColor(key: string, value: number): string {
  const isInverted = INVERTED_METRICS.has(key);
  const isGood = isInverted ? value < 50 : value >= 60;
  const isBad = isInverted ? value >= 70 : value < 30;
  if (isGood) return 'text-accent-success';
  if (isBad) return 'text-accent-danger';
  return 'text-accent-warning';
}

interface Props {
  report: AfterActionReport;
}

export default function AfterActionReportView({ report }: Props) {
  const allMetricKeys = Object.keys(report.metrics.start);

  return (
    <div className="space-y-6 p-6">
      {/* Download button */}
      <div className="flex justify-end">
        <button
          onClick={() => downloadJson(report, `after-action-${report.reportId}.json`)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-border-dim hover:bg-border-bright text-text-secondary hover:text-text-primary text-sm transition-colors"
        >
          <Download size={14} />
          Download JSON
        </button>
      </div>

      {/* 1. Executive Summary Banner */}
      <div className="rounded-xl border border-border-dim bg-bg-card p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div
            className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest font-mono ${
              report.outcomeStatus === 'recovered'
                ? 'bg-accent-success/20 text-accent-success border border-accent-success/40'
                : 'bg-accent-danger/20 text-accent-danger border border-accent-danger/40'
            }`}
          >
            {report.outcomeStatus === 'recovered' ? '✓ RECOVERED' : '✗ DEGRADED'}
          </div>
          <span className="text-xs text-text-dim font-mono">
            ID: {report.reportId}
          </span>
        </div>

        <p className="text-text-primary text-base leading-relaxed mb-5">
          {report.executiveSummary}
        </p>

        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-panel border border-border-dim">
            <span className="text-text-dim text-xs">Crisis Duration</span>
            <span className="text-accent-blue font-mono font-bold text-sm">
              {report.critisTicks} ticks
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-panel border border-border-dim">
            <span className="text-text-dim text-xs">Automation Contribution</span>
            <span className="text-accent-purple font-mono font-bold text-sm">
              {report.automationContributionPct.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-panel border border-border-dim">
            <span className="text-text-dim text-xs">Recovery Rate</span>
            <span className="text-accent-success font-mono font-bold text-sm">
              +{report.metrics.recoveryRatePerTick.toFixed(2)}/tick
            </span>
          </div>
        </div>
      </div>

      {/* 2. Metric Comparison Table */}
      <div className="rounded-xl border border-border-dim bg-bg-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border-dim">
          <h3 className="text-text-primary font-bold text-sm">Metric Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-dim">
                <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">METRIC</th>
                <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">AT START</th>
                <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">WORST</th>
                <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">AT END</th>
                <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">ΔEND</th>
              </tr>
            </thead>
            <tbody>
              {allMetricKeys.map((key) => {
                const start = report.metrics.start[key] ?? 0;
                const worst = report.metrics.worst[key] ?? 0;
                const end = report.metrics.end[key] ?? 0;
                const delta = end - start;
                const isInverted = INVERTED_METRICS.has(key);
                const deltaGood = isInverted ? delta < 0 : delta > 0;
                return (
                  <tr key={key} className="border-b border-border-dim/50 hover:bg-bg-hover/30">
                    <td className="px-4 py-2 text-text-secondary">
                      {METRIC_LABELS[key] ?? key}
                    </td>
                    <td className={`px-4 py-2 text-right font-mono ${metricColor(key, start)}`}>
                      {start.toFixed(1)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-accent-danger">
                      {worst.toFixed(1)}
                    </td>
                    <td className={`px-4 py-2 text-right font-mono ${metricColor(key, end)}`}>
                      {end.toFixed(1)}
                    </td>
                    <td className={`px-4 py-2 text-right font-mono font-bold ${deltaGood ? 'text-accent-success' : 'text-accent-danger'}`}>
                      {deltaGood ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Automation vs Manual */}
      <div className="rounded-xl border border-border-dim bg-bg-card p-5">
        <h3 className="text-text-primary font-bold text-sm mb-4">Automation vs Manual Breakdown</h3>

        <div className="space-y-3 mb-4">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-accent-purple">Automation</span>
              <span className="text-accent-purple font-mono font-bold">
                {report.automationContributionPct.toFixed(1)}%
              </span>
            </div>
            <div className="h-3 rounded-full bg-bg-panel overflow-hidden">
              <div
                className="h-full rounded-full bg-accent-purple transition-all"
                style={{ width: `${report.automationContributionPct}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-accent-blue">Manual</span>
              <span className="text-accent-blue font-mono font-bold">
                {(100 - report.automationContributionPct).toFixed(1)}%
              </span>
            </div>
            <div className="h-3 rounded-full bg-bg-panel overflow-hidden">
              <div
                className="h-full rounded-full bg-accent-blue transition-all"
                style={{ width: `${100 - report.automationContributionPct}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-purple" />
            <span className="text-text-dim">Agent interventions:</span>
            <span className="text-text-primary font-mono font-bold">{report.agentInterventionCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-blue" />
            <span className="text-text-dim">Player interventions:</span>
            <span className="text-text-primary font-mono font-bold">{report.playerInterventionCount}</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 rounded bg-accent-success/10 border border-accent-success/30">
            <span className="text-accent-success font-bold">
              {report.estimatedCrisisWithoutAutomation - report.critisTicks} crisis ticks avoided by automation
            </span>
          </div>
        </div>
      </div>

      {/* 4. Most Affected Buildings */}
      {report.mostAffectedBuildings.length > 0 && (
        <div className="rounded-xl border border-border-dim bg-bg-card p-5">
          <h3 className="text-text-primary font-bold text-sm mb-4">Most Affected Buildings</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {report.mostAffectedBuildings.map((b) => {
              const recovered = b.recoveryTick !== null;
              return (
                <div
                  key={b.buildingId}
                  className={`rounded-lg border p-3 ${recovered ? 'border-accent-success/30 bg-accent-success/5' : 'border-accent-danger/30 bg-accent-danger/5'}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-text-primary font-medium text-sm">{b.name}</span>
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded ${
                        recovered
                          ? 'text-accent-success bg-accent-success/10'
                          : 'text-accent-danger bg-accent-danger/10'
                      }`}
                    >
                      {recovered ? `Recovered T${b.recoveryTick}` : 'Not Recovered'}
                    </span>
                  </div>
                  <div className="text-xs text-text-dim mb-2">
                    Min health: {b.minHealth.toFixed(0)} → Current: {b.currentHealth.toFixed(0)}
                  </div>
                  <div className="h-2 rounded-full bg-bg-panel overflow-hidden">
                    <div className="h-full flex">
                      <div
                        className="bg-accent-danger/70 h-full"
                        style={{ width: `${b.minHealth}%` }}
                      />
                      <div
                        className={`h-full ${recovered ? 'bg-accent-success' : 'bg-accent-warning'}`}
                        style={{ width: `${Math.max(0, b.currentHealth - b.minHealth)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Effective Interventions */}
      {report.effectiveInterventions.length > 0 && (
        <div className="rounded-xl border border-border-dim bg-bg-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border-dim">
            <h3 className="text-text-primary font-bold text-sm">Effective Interventions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-dim">
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">TICK</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">SOURCE</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">ACTION</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">DESCRIPTION</th>
                  <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">ΔSTAB</th>
                </tr>
              </thead>
              <tbody>
                {report.effectiveInterventions.map((iv, i) => (
                  <tr key={i} className="border-b border-border-dim/50 hover:bg-bg-hover/30">
                    <td className="px-4 py-2 font-mono text-text-secondary">{iv.tick}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                          iv.source === 'player' || iv.source === 'human'
                            ? 'bg-accent-warning/20 text-accent-warning border border-accent-warning/30'
                            : 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                        }`}
                      >
                        {iv.source}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-text-secondary font-mono text-xs">{iv.actionType}</td>
                    <td className="px-4 py-2 text-text-dim text-xs">{iv.description}</td>
                    <td className="px-4 py-2 text-right font-mono font-bold text-accent-success">
                      +{iv.stabilityDelta.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 6. UiPath Jobs */}
      {report.uipathJobs.length > 0 && (
        <div className="rounded-xl border border-border-dim bg-bg-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border-dim flex items-center gap-2">
            <span className="text-accent-orange text-xs">◆</span>
            <h3 className="text-text-primary font-bold text-sm">UiPath Jobs Triggered</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-dim">
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">PROCESS</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">TRIGGERED BY</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">AT TICK</th>
                  <th className="text-left px-4 py-2 text-text-dim font-mono text-xs">STATE</th>
                  <th className="text-right px-4 py-2 text-text-dim font-mono text-xs">IMPACT</th>
                </tr>
              </thead>
              <tbody>
                {report.uipathJobs.map((job) => (
                  <tr key={job.jobId} className="border-b border-border-dim/50 hover:bg-bg-hover/30">
                    <td className="px-4 py-2 text-accent-orange font-mono text-xs">{job.processName}</td>
                    <td className="px-4 py-2 text-text-secondary text-xs">{job.triggeredBy}</td>
                    <td className="px-4 py-2 text-text-dim font-mono text-xs">{job.triggeredAtTick}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-mono ${
                          job.state === 'Successful'
                            ? 'text-accent-success bg-accent-success/10'
                            : job.state === 'Faulted'
                            ? 'text-accent-danger bg-accent-danger/10'
                            : 'text-accent-warning bg-accent-warning/10'
                        }`}
                      >
                        {job.state}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-mono font-bold text-accent-success text-xs">
                      +{job.stabilityImpact.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 7. Recommendations */}
      {report.recommendations.length > 0 && (
        <div className="rounded-xl border border-border-dim bg-bg-card p-5">
          <h3 className="text-text-primary font-bold text-sm mb-4">Recommendations</h3>
          <div className="space-y-3">
            {report.recommendations.map((rec, i) => (
              <div
                key={i}
                className="flex items-start gap-3 px-4 py-3 rounded-lg bg-bg-panel border border-border-dim"
              >
                <span className="text-lg shrink-0 mt-0.5">{recommendationIcon(rec)}</span>
                <div className="flex items-start gap-3">
                  <span className="text-text-dim font-mono text-xs font-bold mt-0.5 shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <p className="text-text-secondary text-sm leading-relaxed">{rec}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
