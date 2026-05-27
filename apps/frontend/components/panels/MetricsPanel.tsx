'use client';

import { useGameStore } from '@/lib/store';
import type { SimulationMetrics } from '@/types/game';

// ─── Sparkline ────────────────────────────────────────────────────────────────

function Sparkline({
  data,
  color,
  height = 28,
  width = 80,
}: {
  data: number[];
  color: string;
  height?: number;
  width?: number;
}) {
  if (data.length < 2) {
    return <svg width={width} height={height} />;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(' L ')}`;

  // Area fill
  const areaD =
    `M ${(0).toFixed(1)},${height} L ${points.join(' L ')} L ${width},${height} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <linearGradient id={`sg-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path
        d={areaD}
        fill={`url(#sg-${color.replace('#', '')})`}
        stroke="none"
      />
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Circular Gauge ───────────────────────────────────────────────────────────

function CircularGauge({
  value,
  color,
  size = 56,
}: {
  value: number;
  color: string;
  size?: number;
}) {
  const r = (size - 8) / 2;
  const circumference = 2 * Math.PI * r;
  const progress = Math.max(0, Math.min(100, value)) / 100;
  const dashOffset = circumference * (1 - progress);
  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background track */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#1a2035"
        strokeWidth="6"
      />
      {/* Progress arc */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
      />
      {/* Value text */}
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fill={color}
        fontSize="12"
        fontWeight="bold"
        fontFamily="monospace"
      >
        {Math.round(value)}
      </text>
    </svg>
  );
}

// ─── Metric Card ─────────────────────────────────────────────────────────────

interface MetricConfig {
  key: keyof SimulationMetrics;
  label: string;
  color: string;
  inverted?: boolean;
}

const METRICS: MetricConfig[] = [
  { key: 'operationalStability', label: 'Op. Stability', color: '#00d4ff' },
  { key: 'humanStrain', label: 'Human Strain', color: '#ff8800', inverted: true },
  { key: 'automationConfidence', label: 'Auto. Confidence', color: '#00ffcc' },
  { key: 'serviceAvailability', label: 'Svc. Availability', color: '#44ff88' },
  { key: 'systemTrust', label: 'System Trust', color: '#cc44ff' },
  { key: 'resourceCapacity', label: 'Resource Cap.', color: '#00ffcc' },
];

function MetricCard({
  config,
  value,
  history,
}: {
  config: MetricConfig;
  value: number;
  history: number[];
}) {
  // For inverted metrics (humanStrain), visually display as 100-value for gauge fill
  const displayValue = config.inverted ? 100 - value : value;

  const getColor = () => {
    if (config.inverted) {
      // Higher strain = worse
      if (value > 70) return '#ff4444';
      if (value > 40) return '#ffaa00';
      return config.color;
    }
    if (value < 30) return '#ff4444';
    if (value < 60) return '#ffaa00';
    return config.color;
  };

  const dynamicColor = getColor();

  return (
    <div className="bg-bg-card border border-border-dim rounded-lg p-2.5 flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <CircularGauge value={displayValue} color={dynamicColor} size={52} />
        <div className="flex-1 min-w-0">
          <div className="text-text-dim text-xs uppercase tracking-wider truncate">
            {config.label}
          </div>
          <div
            className="text-xl font-bold font-mono transition-all duration-300"
            style={{ color: dynamicColor }}
          >
            {Math.round(value)}
            <span className="text-xs text-text-secondary ml-0.5">%</span>
          </div>
          {config.inverted && (
            <div className="text-xs text-text-dim">(lower is better)</div>
          )}
        </div>
      </div>
      <Sparkline data={history} color={dynamicColor} width={176} height={24} />
    </div>
  );
}

// ─── MetricsPanel ─────────────────────────────────────────────────────────────

export default function MetricsPanel() {
  const simState = useGameStore((s) => s.simState);
  const tickHistory = useGameStore((s) => s.tickHistory);

  if (!simState) {
    return (
      <div className="space-y-2 p-2">
        {METRICS.map((m) => (
          <div
            key={m.key}
            className="bg-bg-card border border-border-dim rounded-lg p-2.5 h-20 animate-pulse"
          />
        ))}
      </div>
    );
  }

  const metrics = simState.metrics;

  return (
    <div className="space-y-2 p-2">
      <div className="text-xs text-text-dim uppercase tracking-widest px-1 font-semibold">
        System Metrics
      </div>
      {METRICS.map((config) => {
        const history = tickHistory.map((t) => t[config.key]);
        const value = metrics[config.key];
        return (
          <MetricCard
            key={config.key}
            config={config}
            value={value}
            history={history.slice(-20)}
          />
        );
      })}
    </div>
  );
}
