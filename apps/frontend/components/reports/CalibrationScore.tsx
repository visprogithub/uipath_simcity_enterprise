'use client';

import { Download } from 'lucide-react';
import type { CalibrationCertificate, AgentCalibration } from '@/lib/reports';

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const ASSESSMENT_STYLES = {
  success: {
    banner: 'border-accent-success/50 bg-accent-success/10',
    badge: 'bg-accent-success/20 text-accent-success border-accent-success/40',
    text: 'text-accent-success',
  },
  warning: {
    banner: 'border-accent-warning/50 bg-accent-warning/10',
    badge: 'bg-accent-warning/20 text-accent-warning border-accent-warning/40',
    text: 'text-accent-warning',
  },
  danger: {
    banner: 'border-accent-danger/50 bg-accent-danger/10',
    badge: 'bg-accent-danger/20 text-accent-danger border-accent-danger/40',
    text: 'text-accent-danger',
  },
};

function AgentCard({ agent }: { agent: AgentCalibration }) {
  const levelChanged = agent.currentLevel !== agent.recommendedLevel;
  const levelUp = agent.recommendedLevel > agent.currentLevel;
  const levelDown = agent.recommendedLevel < agent.currentLevel;

  const borderClass = agent.readyForUpgrade
    ? 'border-accent-success/50 bg-accent-success/5'
    : agent.requiresDowngrade
    ? 'border-accent-orange/50 bg-accent-orange/5'
    : 'border-border-dim bg-bg-panel';

  const accuracyClamped = Math.max(0, Math.min(100, agent.accuracyPct));

  return (
    <div className={`rounded-xl border p-5 space-y-4 ${borderClass}`}>
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="font-bold text-text-primary text-sm">{agent.agentName}</div>
            <div className="text-text-dim text-xs mt-0.5">{agent.role}</div>
          </div>
          {agent.readyForUpgrade && (
            <span className="px-2 py-0.5 rounded bg-accent-success/20 text-accent-success border border-accent-success/40 text-xs font-mono font-bold shrink-0">
              READY FOR UPGRADE ▲
            </span>
          )}
          {agent.requiresDowngrade && (
            <span className="px-2 py-0.5 rounded bg-accent-orange/20 text-accent-orange border border-accent-orange/40 text-xs font-mono font-bold shrink-0">
              DOWNGRADE REQUIRED ▼
            </span>
          )}
        </div>
      </div>

      {/* Level indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-text-dim text-xs">Current Level:</span>
          <span className="font-mono text-text-primary font-bold">{agent.currentLevel}</span>
        </div>
        {levelChanged && (
          <>
            <span className="text-text-dim">→</span>
            <div className="flex items-center gap-2">
              <span className="text-text-dim text-xs">Recommended:</span>
              <span
                className={`font-mono font-bold ${levelUp ? 'text-accent-success' : 'text-accent-orange'}`}
              >
                {agent.recommendedLevel} {levelUp ? '▲' : '▼'}
              </span>
            </div>
          </>
        )}
        {!levelChanged && (
          <span className="text-text-dim text-xs">→ No change recommended</span>
        )}
      </div>

      {/* Accuracy bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-text-dim">Accuracy</span>
          <span className="font-mono font-bold text-text-primary">{agent.accuracyPct.toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full bg-bg-base overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              accuracyClamped >= 80
                ? 'bg-accent-success'
                : accuracyClamped >= 60
                ? 'bg-accent-warning'
                : 'bg-accent-danger'
            }`}
            style={{ width: `${accuracyClamped}%` }}
          />
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex flex-col gap-0.5">
          <span className="text-text-dim">Trust Score</span>
          <span className="font-mono text-text-primary font-bold">{agent.trustScore}/100</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-text-dim">Actions (effective)</span>
          <span className="font-mono text-text-primary font-bold">
            {agent.totalActions} ({agent.effectiveActions})
          </span>
        </div>
        {agent.counterproductiveActions > 0 && (
          <div className="flex flex-col gap-0.5">
            <span className="text-text-dim">Counterproductive</span>
            <span className="font-mono text-accent-danger font-bold">{agent.counterproductiveActions}</span>
          </div>
        )}
        <div className="flex flex-col gap-0.5">
          <span className="text-text-dim">Stability Contribution</span>
          <span className="font-mono text-accent-success font-bold">
            +{agent.stabilityContribution.toFixed(1)} pts
          </span>
        </div>
      </div>

      {/* Rationale */}
      {agent.rationale && (
        <blockquote className="border-l-2 border-border-bright pl-3 text-xs text-text-dim italic leading-relaxed">
          "{agent.rationale}"
        </blockquote>
      )}
    </div>
  );
}

interface Props {
  certificate: CalibrationCertificate;
}

export default function CalibrationScore({ certificate }: Props) {
  const styles = ASSESSMENT_STYLES[certificate.assessmentColor];

  return (
    <div className="space-y-6 p-6">
      {/* Download button */}
      <div className="flex justify-end">
        <button
          onClick={() =>
            downloadJson(certificate, `calibration-${certificate.certificateId}.json`)
          }
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-border-dim hover:bg-border-bright text-text-secondary hover:text-text-primary text-sm transition-colors"
        >
          <Download size={14} />
          Download JSON
        </button>
      </div>

      {/* Overall Assessment Banner */}
      <div className={`rounded-xl border p-6 ${styles.banner}`}>
        <div className="flex items-start justify-between gap-4 mb-4">
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest font-mono border ${styles.badge}`}
          >
            {certificate.assessmentLabel}
          </span>
          <span className="text-xs text-text-dim font-mono">ID: {certificate.certificateId}</span>
        </div>

        <p className="text-text-secondary text-sm leading-relaxed mb-5">
          {certificate.overallRecommendation}
        </p>

        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-base/50 border border-border-dim">
            <span className="text-text-dim text-xs">Avg Accuracy</span>
            <span className={`font-mono font-bold text-sm ${styles.text}`}>
              {certificate.averageAccuracyPct.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-base/50 border border-border-dim">
            <span className="text-text-dim text-xs">Avg Trust Score</span>
            <span className={`font-mono font-bold text-sm ${styles.text}`}>
              {certificate.averageTrustScore.toFixed(1)}/100
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-base/50 border border-border-dim">
            <span className="text-text-dim text-xs">Scenario Outcome</span>
            <span
              className={`font-mono font-bold text-sm ${
                certificate.scenarioOutcome === 'recovered' ? 'text-accent-success' : 'text-accent-danger'
              }`}
            >
              {certificate.scenarioOutcome.toUpperCase()}
            </span>
          </div>
        </div>

        {(certificate.agentsReadyForUpgrade.length > 0 || certificate.agentsRequiringDowngrade.length > 0) && (
          <div className="mt-4 flex flex-wrap gap-3 text-xs">
            {certificate.agentsReadyForUpgrade.length > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="text-accent-success font-bold">▲ Ready for upgrade:</span>
                <span className="text-accent-success">{certificate.agentsReadyForUpgrade.join(', ')}</span>
              </div>
            )}
            {certificate.agentsRequiringDowngrade.length > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="text-accent-orange font-bold">▼ Requires downgrade:</span>
                <span className="text-accent-orange">{certificate.agentsRequiringDowngrade.join(', ')}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Evidence Trail */}
      {certificate.evidenceTrail.length > 0 && (
        <div className="rounded-xl border border-border-dim bg-bg-card p-5">
          <h3 className="text-text-primary font-bold text-sm mb-3">Evidence Trail</h3>
          <div className="space-y-2">
            {certificate.evidenceTrail.map((item, i) => {
              const isPositive = !item.toLowerCase().includes('fail') &&
                !item.toLowerCase().includes('error') &&
                !item.toLowerCase().includes('miss');
              return (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className={isPositive ? 'text-accent-success' : 'text-accent-danger'}>
                    {isPositive ? '✅' : '❌'}
                  </span>
                  <span className="text-text-secondary leading-relaxed">{item}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Agent Calibration Cards */}
      <div>
        <h3 className="text-text-primary font-bold text-sm mb-4">Agent Calibrations</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {certificate.agentCalibrations.map((agent) => (
            <AgentCard key={agent.agentId} agent={agent} />
          ))}
        </div>
      </div>

      {/* Note */}
      {certificate.note && (
        <p className="text-text-dim text-xs leading-relaxed px-4 py-3 rounded-lg bg-bg-base border border-border-dim italic">
          {certificate.note}
        </p>
      )}
    </div>
  );
}
