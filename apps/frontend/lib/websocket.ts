import type { PlayerAction, WsServerMessage, WsStateMessage } from '@shared/index';
import type { GameStore } from './store';

class GameWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private store: GameStore | null = null;
  private url: string = '';
  private destroyed = false;

  connect(url: string, store: GameStore): void {
    this.destroyed = false;
    this.store = store;
    this.url = url;
    this._connect();
  }

  private _connect(): void {
    if (this.destroyed) return;
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }

    this.store?.setConnectionStatus('connecting');

    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      console.error('[ws] Failed to create WebSocket:', e);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log('[ws] Connected to', this.url);
      this.reconnectDelay = 1000;
      this.store?.setConnectionStatus('connected');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as WsServerMessage;
        this.handleMessage(data);
      } catch (e) {
        console.error('[ws] Failed to parse message:', e);
      }
    };

    this.ws.onclose = () => {
      if (this.destroyed) return;
      console.log('[ws] Connection closed, scheduling reconnect...');
      this.store?.setConnectionStatus('disconnected');
      this.scheduleReconnect();
    };

    this.ws.onerror = (e) => {
      console.error('[ws] WebSocket error:', e);
      this.store?.setConnectionStatus('disconnected');
    };
  }

  disconnect(): void {
    this.destroyed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
  }

  send(action: PlayerAction): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[ws] Cannot send action - not connected');
      return;
    }
    const message = { type: 'action', payload: action };
    this.ws.send(JSON.stringify(message));
  }

  private handleMessage(data: WsServerMessage): void {
    if (!this.store) return;

    if (data.type === 'state') {
      const stateMsg = data as WsStateMessage;
      this.store.setSimState(stateMsg.payload);
    } else if (data.type === 'ack') {
      if (!data.success) {
        console.warn('[ws] Action failed:', data.error);
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.destroyed) return;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    console.log(`[ws] Reconnecting in ${this.reconnectDelay}ms...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this._connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
  }
}

export const gameWS = new GameWebSocket();
