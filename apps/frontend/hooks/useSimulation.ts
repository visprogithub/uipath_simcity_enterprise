'use client';

import { useEffect } from 'react';
import { useGameStore } from '@/lib/store';
import { gameWS } from '@/lib/websocket';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws';

export function useSimulation() {
  const simState = useGameStore((s) => s.simState);
  const connectionStatus = useGameStore((s) => s.connectionStatus);
  const setSimState = useGameStore((s) => s.setSimState);
  const setConnectionStatus = useGameStore((s) => s.setConnectionStatus);
  const _setSendFn = useGameStore((s) => s._setSendFn);

  useEffect(() => {
    // Register the send function in the store so sendAction() works
    _setSendFn((action) => gameWS.send(action));

    // Connect passing the store snapshot functions
    const storeSnapshot = useGameStore.getState();
    gameWS.connect(WS_URL, storeSnapshot);

    return () => {
      gameWS.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { simState, connectionStatus };
}
