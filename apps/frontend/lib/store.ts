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

// Scenario types
export interface OutagePreset {
  id: string;
  name: string;
  buildingId: string;
  severity: string;
  description: string;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  tagline: string;
  description: string;
  industry: string;
  icon: string;
  color: string;
  buildingCount: number;
  agentCount: number;
  complianceFrameworks: string[];
  outagePresets: OutagePreset[];
}

export interface GameStore {
  // State
  simState: SimulationState | null;
  overlayMode: OverlayMode;
  selectedBuilding: string | null;
  selectedAgent: string | null;
  isPaused: boolean;
  connectionStatus: ConnectionStatus;
  tickHistory: SimulationMetrics[];

  // Scenario state
  availableScenarios: ScenarioInfo[];
  activeScenario: ScenarioInfo | null;
  scenarioSelected: boolean;
  scenarioLoading: boolean;

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

  // Scenario actions
  fetchScenarios: () => Promise<void>;
  selectScenario: (id: string) => Promise<void>;
  setScenarioSelected: (v: boolean) => void;

  // Agent Builder state
  agentBuilderOpen: boolean;
  setAgentBuilderOpen: (v: boolean) => void;
  agentBuilderData: any;
  fetchAgentBuilder: () => Promise<void>;

  // CodeGen Modal state
  codeGenOpen: boolean;
  setCodeGenOpen: (v: boolean) => void;
  codeGenResult: any;
  codeGenLoading: boolean;

  // Approvals state
  approvalsOpen: boolean;
  setApprovalsOpen: (v: boolean) => void;
  pendingApprovals: any[];
  fetchApprovals: () => Promise<void>;
  approvalCount: number;
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

  // Scenario initial state
  availableScenarios: [],
  activeScenario: null,
  scenarioSelected: false,
  scenarioLoading: false,

  // Reports initial state
  reportsOpen: false,
  activeReportTab: 'after-action',
  afterActionReport: null,
  runbook: null,
  calibration: null,
  processTemplates: null,
  reportsLoading: false,
  reportsError: null,

  // Agent Builder initial state
  agentBuilderOpen: false,
  agentBuilderData: null,

  // CodeGen Modal initial state
  codeGenOpen: false,
  codeGenResult: null,
  codeGenLoading: false,

  // Approvals initial state
  approvalsOpen: false,
  pendingApprovals: [],
  approvalCount: 0,

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

  setAgentBuilderOpen: (v) => set({ agentBuilderOpen: v }),

  fetchAgentBuilder: async () => {
    try {
      const res = await fetch('/api/agent-builder/agents');
      if (!res.ok) throw new Error('Failed to fetch agent builder data');
      const data = await res.json();
      set({ agentBuilderData: data });
    } catch (err) {
      console.error('[store] fetchAgentBuilder failed:', err);
    }
  },

  setCodeGenOpen: (v) => set({ codeGenOpen: v }),

  setApprovalsOpen: (v) => set({ approvalsOpen: v }),

  fetchApprovals: async () => {
    try {
      const res = await fetch('/api/approvals/pending');
      if (!res.ok) throw new Error('Failed to fetch approvals');
      const data = await res.json();
      const approvals = Array.isArray(data) ? data : (data.approvals ?? []);
      set({ pendingApprovals: approvals, approvalCount: approvals.length });
    } catch (err) {
      console.error('[store] fetchApprovals failed:', err);
    }
  },

  fetchScenarios: async () => {
    set({ scenarioLoading: true });
    try {
      const res = await fetch('http://localhost:8000/api/scenarios');
      if (!res.ok) throw new Error('Failed to fetch scenarios');
      const data = await res.json();
      const scenarios: ScenarioInfo[] = data.scenarios ?? [];
      set({ availableScenarios: scenarios });

      // Also check if there's an active scenario (restore on page reload)
      try {
        const activeRes = await fetch('http://localhost:8000/api/scenario/active');
        if (activeRes.ok) {
          const activeData = await activeRes.json();
          if (activeData.scenarioId && activeData.scenario) {
            // Find the full scenario info from availableScenarios (or use returned data)
            const full = scenarios.find((s) => s.id === activeData.scenarioId) ?? null;
            if (full) {
              set({ activeScenario: full, scenarioSelected: true });
            }
          }
        }
      } catch {
        // Silently ignore — no active scenario is fine
      }
    } catch (err) {
      console.error('[store] fetchScenarios failed:', err);
    } finally {
      set({ scenarioLoading: false });
    }
  },

  selectScenario: async (id: string) => {
    set({ scenarioLoading: true });
    try {
      const res = await fetch('http://localhost:8000/api/scenario/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenarioId: id }),
      });
      if (!res.ok) throw new Error('Failed to select scenario');
      const scenarios = get().availableScenarios;
      const selected = scenarios.find((s) => s.id === id) ?? null;
      set({ activeScenario: selected, scenarioSelected: true });
      // Reset old simulation data
      await get().resetScenario();
    } catch (err) {
      console.error('[store] selectScenario failed:', err);
    } finally {
      set({ scenarioLoading: false });
    }
  },

  setScenarioSelected: (v: boolean) => set({ scenarioSelected: v }),
}));
