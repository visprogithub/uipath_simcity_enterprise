import { create } from 'zustand';
import type {
  SimulationState,
  OverlayMode,
  SimulationMetrics,
  PlayerAction,
} from '@shared/index';
import type { ConnectionStatus } from '@/types/game';
import type {
  AfterActionReport,
  Runbook,
  CalibrationCertificate,
  ProcessTemplate,
} from '@/lib/reports';

export interface GameStore {
  // State
  simState: SimulationState | null;
  overlayMode: OverlayMode;
  selectedBuilding: string | null;
  selectedAgent: string | null;
  isPaused: boolean;
  connectionStatus: ConnectionStatus;
  tickHistory: SimulationMetrics[];

  // Actions
  setSimState: (state: SimulationState) => void;
  setOverlayMode: (mode: OverlayMode) => void;
  selectBuilding: (id: string | null) => void;
  selectAgent: (id: string | null) => void;
  togglePause: () => void;
  setConnectionStatus: (s: ConnectionStatus) => void;
  pushTickHistory: (metrics: SimulationMetrics) => void;

  // Player actions (these send to backend via WS)
  sendAction: (action: PlayerAction) => void;
  // Will be set by the websocket client
  _sendFn: ((action: PlayerAction) => void) | null;
  _setSendFn: (fn: (action: PlayerAction) => void) => void;

  // Reports state
  reportsOpen: boolean;
  activeReportTab: 'after-action' | 'runbook' | 'calibration' | 'templates';
  afterActionReport: AfterActionReport | null;
  runbook: Runbook | null;
  calibration: CalibrationCertificate | null;
  processTemplates: ProcessTemplate[] | null;
  reportsLoading: boolean;
  reportsError: string | null;

  // Reports actions
  setReportsOpen: (open: boolean) => void;
  setActiveReportTab: (tab: 'after-action' | 'runbook' | 'calibration' | 'templates') => void;
  fetchReports: () => Promise<void>;
  resetScenario: () => Promise<void>;
}

export const useGameStore = create<GameStore>((set, get) => ({
  simState: null,
  overlayMode: 'none',
  selectedBuilding: null,
  selectedAgent: null,
  isPaused: false,
  connectionStatus: 'connecting',
  tickHistory: [],
  _sendFn: null,

  // Reports initial state
  reportsOpen: false,
  activeReportTab: 'after-action',
  afterActionReport: null,
  runbook: null,
  calibration: null,
  processTemplates: null,
  reportsLoading: false,
  reportsError: null,

  setSimState: (state) =>
    set((prev) => {
      const history = prev.tickHistory;
      const newHistory =
        history.length >= 60
          ? [...history.slice(1), state.metrics]
          : [...history, state.metrics];
      return { simState: state, tickHistory: newHistory };
    }),

  setOverlayMode: (mode) => set({ overlayMode: mode }),

  selectBuilding: (id) => set({ selectedBuilding: id, selectedAgent: null }),

  selectAgent: (id) => set({ selectedAgent: id, selectedBuilding: null }),

  togglePause: () => set((s) => ({ isPaused: !s.isPaused })),

  setConnectionStatus: (s) => set({ connectionStatus: s }),

  pushTickHistory: (metrics) =>
    set((prev) => {
      const history = prev.tickHistory;
      const newHistory =
        history.length >= 60
          ? [...history.slice(1), metrics]
          : [...history, metrics];
      return { tickHistory: newHistory };
    }),

  sendAction: (action) => {
    const fn = get()._sendFn;
    if (fn) {
      fn(action);
    } else {
      console.warn('[store] sendAction called but no WS send function registered');
    }
  },

  _setSendFn: (fn) => set({ _sendFn: fn }),

  setReportsOpen: (open) => set({ reportsOpen: open }),

  setActiveReportTab: (tab) => set({ activeReportTab: tab }),

  fetchReports: async () => {
    set({ reportsLoading: true, reportsError: null });
    try {
      const [aarRes, rbRes, calRes, ptRes] = await Promise.all([
        fetch('/api/report/after-action'),
        fetch('/api/report/runbook'),
        fetch('/api/report/autonomy-calibration'),
        fetch('/api/report/process-templates'),
      ]);

      if (!aarRes.ok || !rbRes.ok || !calRes.ok || !ptRes.ok) {
        throw new Error('One or more report endpoints returned an error');
      }

      const [afterActionReport, runbook, calibration, processTemplates] = await Promise.all([
        aarRes.json(),
        rbRes.json(),
        calRes.json(),
        ptRes.json(),
      ]);

      set({ afterActionReport, runbook, calibration, processTemplates, reportsLoading: false });
    } catch (err) {
      set({
        reportsLoading: false,
        reportsError: err instanceof Error ? err.message : 'Failed to load reports',
      });
    }
  },

  resetScenario: async () => {
    try {
      await fetch('/api/scenario/reset', { method: 'POST' });
    } catch (err) {
      console.error('[store] resetScenario failed:', err);
    }
  },
}));
