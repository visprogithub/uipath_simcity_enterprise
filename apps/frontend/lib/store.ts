import { create } from 'zustand';
import type {
  SimulationState,
  OverlayMode,
  SimulationMetrics,
  PlayerAction,
} from '@shared/index';
import type { ConnectionStatus } from '@/types/game';

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
}));
