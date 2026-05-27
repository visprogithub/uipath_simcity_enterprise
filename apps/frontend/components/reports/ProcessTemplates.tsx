'use client';

import { useState } from 'react';
import { Download, X, Code } from 'lucide-react';
import type { ProcessTemplate } from '@/lib/reports';

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadTemplate(template: ProcessTemplate) {
  // Download Main.xaml
  downloadFile(template.xaml, `${template.processName}/Main.xaml`, 'application/xml');
  // Small delay so browser doesn't block second download
  setTimeout(() => {
    downloadFile(
      JSON.stringify(template.projectJson, null, 2),
      `${template.processName}/project.json`,
      'application/json'
    );
  }, 200);
}

function XamlViewer({ content, onClose }: { content: string; onClose: () => void }) {
  const lines = content.split('\n');
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-bg-base/90 backdrop-blur-sm p-6">
      <div
        className="flex flex-col bg-bg-panel border border-border-bright rounded-xl overflow-hidden"
        style={{ width: '80vw', maxWidth: '900px', height: '80vh' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-dim shrink-0">
          <span className="text-text-primary font-mono text-sm font-bold">Main.xaml</span>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover text-text-dim hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4 font-mono text-xs">
          {lines.map((line, i) => (
            <div key={i} className="flex gap-4 leading-relaxed hover:bg-bg-hover/20 px-2 rounded">
              <span className="text-text-dim select-none w-8 shrink-0 text-right">{i + 1}</span>
              <span className="text-text-secondary whitespace-pre">{line}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReadmeViewer({ content, onClose }: { content: string; onClose: () => void }) {
  const lines = content.split('\n');
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-bg-base/90 backdrop-blur-sm p-6">
      <div
        className="flex flex-col bg-bg-panel border border-border-bright rounded-xl overflow-hidden"
        style={{ width: '70vw', maxWidth: '800px', height: '75vh' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-dim shrink-0">
          <span className="text-text-primary font-mono text-sm font-bold">README</span>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover text-text-dim hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-5 text-sm space-y-1">
          {lines.map((line, i) => {
            if (line.startsWith('# '))
              return <div key={i} className="text-accent-blue text-base font-bold mt-3 mb-1">{line.slice(2)}</div>;
            if (line.startsWith('## '))
              return <div key={i} className="text-accent-blue text-sm font-bold mt-2 mb-1">{line.slice(3)}</div>;
            if (line.startsWith('- ') || line.startsWith('* '))
              return (
                <div key={i} className="text-text-secondary pl-4">
                  <span className="text-accent-blue mr-2">•</span>
                  {line.slice(2)}
                </div>
              );
            if (line === '') return <div key={i} className="h-2" />;
            return <div key={i} className="text-text-secondary">{line}</div>;
          })}
        </div>
      </div>
    </div>
  );
}

function ProcessCard({ template }: { template: ProcessTemplate }) {
  const [showXaml, setShowXaml] = useState(false);
  const [showReadme, setShowReadme] = useState(false);

  return (
    <>
      <div className="rounded-xl border border-border-dim bg-bg-card overflow-hidden">
        {/* Card header */}
        <div className="flex items-center justify-between px-5 py-4 bg-bg-panel border-b border-border-dim">
          <div>
            <span className="font-mono text-accent-orange font-bold text-sm">{template.processName}</span>
            <p className="text-text-dim text-xs mt-0.5">{template.description}</p>
          </div>
          <button
            onClick={() => downloadTemplate(template)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-orange/20 border border-accent-orange/40 text-accent-orange hover:bg-accent-orange/30 text-xs font-medium transition-colors shrink-0"
          >
            <Download size={12} />
            Download
          </button>
        </div>

        {/* Args */}
        <div className="p-5 space-y-4">
          {template.inputArgs.length > 0 && (
            <div>
              <div className="text-text-dim text-xs font-bold mb-2 uppercase tracking-wider">Input Args</div>
              <div className="space-y-1">
                {template.inputArgs.map((arg) => (
                  <div key={arg.name} className="flex items-start gap-2 text-xs">
                    <span className="text-text-dim">•</span>
                    <span className="font-mono text-accent-blue">{arg.name}</span>
                    <span className="text-text-dim">: {arg.type}</span>
                    {arg.description && (
                      <span className="text-text-dim italic">— {arg.description}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {template.outputArgs.length > 0 && (
            <div>
              <div className="text-text-dim text-xs font-bold mb-2 uppercase tracking-wider">Output Args</div>
              <div className="space-y-1">
                {template.outputArgs.map((arg) => (
                  <div key={arg.name} className="flex items-start gap-2 text-xs">
                    <span className="text-text-dim">•</span>
                    <span className="font-mono text-accent-teal">{arg.name}</span>
                    <span className="text-text-dim">: {arg.type}</span>
                    {arg.description && (
                      <span className="text-text-dim italic">— {arg.description}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-5 py-3 border-t border-border-dim flex items-center gap-2">
          <button
            onClick={() => setShowXaml(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-dim text-text-secondary hover:text-text-primary hover:border-border-bright text-xs transition-colors"
          >
            <Code size={12} />
            View XAML
          </button>
          <button
            onClick={() => setShowReadme(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-dim text-text-secondary hover:text-text-primary hover:border-border-bright text-xs transition-colors"
          >
            View README
          </button>
        </div>
      </div>

      {showXaml && <XamlViewer content={template.xaml} onClose={() => setShowXaml(false)} />}
      {showReadme && <ReadmeViewer content={template.readme} onClose={() => setShowReadme(false)} />}
    </>
  );
}

interface Props {
  templates: ProcessTemplate[];
}

export default function ProcessTemplates({ templates }: Props) {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="rounded-xl border border-border-dim bg-bg-card p-5">
        <div className="flex items-start gap-3">
          <span className="text-2xl">◆</span>
          <div>
            <h2 className="text-text-primary font-bold text-base mb-1">
              UiPath Studio Process Templates
            </h2>
            <p className="text-text-secondary text-sm">
              Download these templates and import them into UiPath Studio to automate the response
              procedures validated in this simulation.
            </p>
          </div>
        </div>
      </div>

      {/* Process cards */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {templates.map((t) => (
          <ProcessCard key={t.processName} template={t} />
        ))}
      </div>

      {/* Footer */}
      <div className="rounded-lg border border-border-dim bg-bg-panel px-4 py-3 text-xs text-text-dim">
        For import instructions, see{' '}
        <span className="text-accent-blue font-mono">UIPATH_PLATFORM_SETUP.md</span> in the
        repository root.
      </div>
    </div>
  );
}
