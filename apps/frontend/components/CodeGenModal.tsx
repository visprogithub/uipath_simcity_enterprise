'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Sparkles, Download, Copy, Bug, CheckCircle2, Loader2 } from 'lucide-react';
import { useGameStore } from '@/lib/store';
import { api } from '@/lib/api';
import clsx from 'clsx';

const PROCESS_OPTIONS = [
  'Incident_Escalation',
  'Approval_Chain',
  'Crisis_Response',
  'Emergency_Staffing',
  'Trust_Recovery_Protocol',
];

const LOADING_MESSAGES = [
  'Analyzing simulation context...',
  'Generating XAML sequence...',
  'Validating automation logic...',
  'Preparing output...',
];

function CyclingText({ active }: { active: boolean }) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!active) return;
    const interval = setInterval(() => {
      setIdx((i) => (i + 1) % LOADING_MESSAGES.length);
    }, 1200);
    return () => clearInterval(interval);
  }, [active]);

  return (
    <span className="text-sm text-white/60 font-mono transition-all">{LOADING_MESSAGES[idx]}</span>
  );
}

function XamlBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleDownload() {
    const blob = new Blob([code], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'workflow.xaml';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600/20 text-blue-300 border border-blue-500/30 hover:bg-blue-600/30 transition-colors"
        >
          <Download size={12} />
          Download XAML
        </button>
        <button
          onClick={handleCopy}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors',
            copied
              ? 'bg-green-600/20 text-green-300 border-green-500/30'
              : 'bg-white/5 text-white/60 border-white/15 hover:bg-white/10'
          )}
        >
          {copied ? <CheckCircle2 size={12} /> : <Copy size={12} />}
          {copied ? 'Copied!' : 'Copy to Clipboard'}
        </button>
      </div>
      <pre className="text-xs text-green-300/85 bg-black/50 border border-white/10 rounded-lg p-4 overflow-auto max-h-96 font-mono leading-relaxed whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  );
}

export default function CodeGenModal() {
  const codeGenOpen = useGameStore((s) => s.codeGenOpen);
  const setCodeGenOpen = useGameStore((s) => s.setCodeGenOpen);
  const codeGenResult = useGameStore((s) => s.codeGenResult);
  const codeGenLoading = useGameStore((s) => s.codeGenLoading);
  const simState = useGameStore((s) => s.simState);

  const [selectedProcess, setSelectedProcess] = useState(PROCESS_OPTIONS[0]);
  const [activeTab, setActiveTab] = useState<'generate' | 'debug'>('generate');
  const [localResult, setLocalResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorDesc, setErrorDesc] = useState('');
  const [debugResult, setDebugResult] = useState<any>(null);
  const [debugLoading, setDebugLoading] = useState(false);

  useEffect(() => {
    if (!codeGenOpen) {
      setLocalResult(null);
      setLoading(false);
      setDebugResult(null);
      setErrorDesc('');
    }
  }, [codeGenOpen]);

  async function handleGenerate() {
    setLoading(true);
    setLocalResult(null);
    try {
      const res = await api('/api/coding-agent/generate-workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          processType: selectedProcess,
          context: simState
            ? {
                phase: simState.phase,
                tick: simState.tick,
                metrics: simState.metrics,
              }
            : {},
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLocalResult(data);
    } catch (err) {
      setLocalResult({ error: err instanceof Error ? err.message : 'Generation failed' });
    } finally {
      setLoading(false);
    }
  }

  async function handleDebug() {
    if (!errorDesc.trim()) return;
    setDebugLoading(true);
    setDebugResult(null);
    try {
      const res = await api('/api/coding-agent/debug-workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: selectedProcess,
          error_description: errorDesc,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDebugResult(data);
    } catch (err) {
      setDebugResult({ error: err instanceof Error ? err.message : 'Debug failed' });
    } finally {
      setDebugLoading(false);
    }
  }

  if (!codeGenOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/85 backdrop-blur-sm"
        onClick={() => setCodeGenOpen(false)}
      />

      {/* Modal */}
      <div
        className="relative z-10 flex flex-col rounded-2xl shadow-2xl overflow-hidden"
        style={{
          width: '720px',
          maxWidth: '95vw',
          maxHeight: '90vh',
          background: '#0d1117',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        {/* BONUS FEATURE banner */}
        <div
          className="flex items-center justify-center gap-2 py-2 text-xs font-bold tracking-widest"
          style={{ background: '#B45309', color: '#FEF3C7' }}
        >
          <Sparkles size={12} />
          BONUS FEATURE: Coding Agents
          <Sparkles size={12} />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-yellow-400" />
              <span className="text-white font-bold text-lg">Coding Agent</span>
            </div>
            <div className="text-white/40 text-xs mt-0.5">Powered by gpt-4.1-mini · UiPath LLM Gateway</div>
          </div>
          <button
            onClick={() => setCodeGenOpen(false)}
            className="p-2 rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10 shrink-0 px-6">
          {(['generate', 'debug'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'px-4 py-2.5 text-sm font-semibold transition-colors border-b-2 capitalize',
                activeTab === tab
                  ? 'border-yellow-400 text-yellow-300'
                  : 'border-transparent text-white/40 hover:text-white/70'
              )}
            >
              {tab === 'debug' ? (
                <span className="flex items-center gap-1.5">
                  <Bug size={13} /> Debug Workflow
                </span>
              ) : (
                'Generate Workflow'
              )}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {activeTab === 'generate' && (
            <>
              {/* Process selector */}
              <div className="space-y-2">
                <label className="text-xs text-white/50 uppercase tracking-widest font-semibold">
                  Select Process
                </label>
                <select
                  value={selectedProcess}
                  onChange={(e) => setSelectedProcess(e.target.value)}
                  className="w-full rounded-lg border border-white/15 bg-white/5 text-white text-sm px-3 py-2.5 focus:outline-none focus:border-yellow-400/50 appearance-none cursor-pointer"
                >
                  {PROCESS_OPTIONS.map((p) => (
                    <option key={p} value={p} style={{ background: '#0d1117', color: 'white' }}>
                      {p.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={loading}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold transition-all',
                  loading
                    ? 'opacity-60 cursor-not-allowed bg-purple-700/40 text-purple-300'
                    : 'bg-purple-700 hover:bg-purple-600 text-white shadow-lg hover:shadow-purple-900/50'
                )}
              >
                {loading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Sparkles size={16} />
                )}
                {loading ? 'Generating...' : 'Generate Workflow'}
              </button>

              {/* Loading state */}
              {loading && (
                <div className="flex flex-col items-center gap-3 py-6">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-2 border-purple-500/30" />
                    <div className="absolute inset-0 w-12 h-12 rounded-full border-t-2 border-purple-400 animate-spin" />
                  </div>
                  <div className="text-white/60 text-sm font-mono">Generating your UiPath workflow on the robot...</div>
                  <CyclingText active={loading} />
                </div>
              )}

              {/* Result */}
              {!loading && localResult && !localResult.error && (
                <div className="space-y-4">
                  {/* Badge */}
                  <div className="flex items-center gap-2">
                    <span
                      className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold"
                      style={{ background: 'rgba(34,197,94,0.15)', color: '#4ade80', border: '1px solid rgba(34,197,94,0.3)' }}
                    >
                      <CheckCircle2 size={12} />
                      GENERATED BY CODING AGENT
                    </span>
                    {localResult.generationTimeMs && (
                      <span className="text-xs text-white/30 font-mono">
                        {localResult.generationTimeMs}ms
                      </span>
                    )}
                  </div>

                  {/* Generation context */}
                  {localResult.generationContext && (
                    <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1.5">
                      <div className="text-xs text-white/50 uppercase tracking-widest font-semibold mb-2">
                        Generation Context
                      </div>
                      {localResult.generationContext.phase && (
                        <div className="flex justify-between text-xs">
                          <span className="text-white/40">Phase</span>
                          <span className="text-white/80 font-mono">{localResult.generationContext.phase}</span>
                        </div>
                      )}
                      {localResult.generationContext.buildings_down !== undefined && (
                        <div className="flex justify-between text-xs">
                          <span className="text-white/40">Buildings Down</span>
                          <span className="text-white/80 font-mono">{localResult.generationContext.buildings_down}</span>
                        </div>
                      )}
                      {localResult.generationContext.metrics && (
                        <div className="mt-1 pt-1 border-t border-white/10">
                          <div className="text-xs text-white/40 mb-1">Metrics snapshot</div>
                          <pre className="text-xs text-white/50 font-mono">
                            {JSON.stringify(localResult.generationContext.metrics, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* XAML viewer */}
                  {localResult.xaml && <XamlBlock code={localResult.xaml} />}
                </div>
              )}

              {/* Error */}
              {!loading && localResult?.error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">
                  {localResult.error}
                </div>
              )}
            </>
          )}

          {activeTab === 'debug' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-white/50 uppercase tracking-widest font-semibold">
                  Error Description
                </label>
                <textarea
                  value={errorDesc}
                  onChange={(e) => setErrorDesc(e.target.value)}
                  placeholder="Paste the error message or describe the issue..."
                  rows={4}
                  className="w-full rounded-lg border border-white/15 bg-white/5 text-white text-sm px-3 py-2.5 focus:outline-none focus:border-yellow-400/50 resize-none placeholder:text-white/25"
                />
              </div>

              <button
                onClick={handleDebug}
                disabled={debugLoading || !errorDesc.trim()}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold transition-all',
                  debugLoading || !errorDesc.trim()
                    ? 'opacity-50 cursor-not-allowed bg-orange-700/30 text-orange-300'
                    : 'bg-orange-600 hover:bg-orange-500 text-white'
                )}
              >
                {debugLoading ? <Loader2 size={16} className="animate-spin" /> : <Bug size={16} />}
                {debugLoading ? 'Debugging...' : 'Debug Workflow'}
              </button>

              {debugResult && !debugResult.error && (
                <div className="space-y-3">
                  {debugResult.diagnosis && (
                    <div className="rounded-lg border border-orange-500/25 bg-orange-500/10 p-3">
                      <div className="text-xs text-orange-300/70 uppercase tracking-widest font-semibold mb-1.5">Diagnosis</div>
                      <div className="text-sm text-white/80">{debugResult.diagnosis}</div>
                    </div>
                  )}
                  {debugResult.xamlPatch && (
                    <div className="space-y-1.5">
                      <div className="text-xs text-white/50 uppercase tracking-widest font-semibold">XAML Patch</div>
                      <XamlBlock code={debugResult.xamlPatch} />
                    </div>
                  )}
                </div>
              )}

              {debugResult?.error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">
                  {debugResult.error}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
