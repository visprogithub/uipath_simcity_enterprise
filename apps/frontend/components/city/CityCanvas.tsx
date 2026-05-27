'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useGameStore } from '@/lib/store';
import { CityRenderer, CANVAS_W, CANVAS_H } from '@/simulation/CityRenderer';
import type { SimulationState } from '@/types/game';

interface CityCanvasProps {
  className?: string;
}

export default function CityCanvas({ className }: CityCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<CityRenderer | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const simState = useGameStore((s) => s.simState);
  const overlayMode = useGameStore((s) => s.overlayMode);
  const connectionStatus = useGameStore((s) => s.connectionStatus);
  const selectBuilding = useGameStore((s) => s.selectBuilding);
  const selectAgent = useGameStore((s) => s.selectAgent);

  // Initialize PixiJS renderer once canvas is available
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new CityRenderer(canvas);
    renderer.init();
    rendererRef.current = renderer;

    renderer.onBuildingClick((id) => {
      selectBuilding(id);
    });

    renderer.onAgentClick((id) => {
      selectAgent(id);
    });

    return () => {
      renderer.destroy();
      rendererRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update renderer whenever state changes
  useEffect(() => {
    if (!simState || !rendererRef.current) return;
    rendererRef.current.update(simState, overlayMode);
  }, [simState, overlayMode]);

  return (
    <div
      ref={containerRef}
      className={`relative flex items-center justify-center bg-bg-base overflow-hidden ${className ?? ''}`}
    >
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        style={{
          display: 'block',
          maxWidth: '100%',
          maxHeight: '100%',
          imageRendering: 'pixelated',
        }}
      />

      {/* Reconnecting overlay */}
      {connectionStatus !== 'connected' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg-base/80 backdrop-blur-sm z-10">
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-2 border-accent-blue/30" />
              <div className="absolute inset-0 w-16 h-16 rounded-full border-t-2 border-accent-blue animate-spin" />
            </div>
            <div className="text-center">
              <div className="text-accent-blue font-bold text-lg font-mono tracking-widest">
                {connectionStatus === 'connecting' ? 'CONNECTING' : 'RECONNECTING'}
              </div>
              <div className="text-text-secondary text-sm mt-1">
                Establishing link to simulation server...
              </div>
            </div>
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-accent-blue animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Initial state - no data yet */}
      {connectionStatus === 'connected' && !simState && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-text-secondary text-sm">Awaiting simulation data...</div>
        </div>
      )}
    </div>
  );
}
