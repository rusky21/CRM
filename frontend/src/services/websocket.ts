import { WebSocketInboundPayload } from '../types';

type MessageHandler = (payload: WebSocketInboundPayload) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private url: string;
  private listeners: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private pingInterval: any = null;
  private currentSubscription: { accountId: string; peerId: number } | null = null;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const initData = window.Telegram?.WebApp?.initData || '';
    const query = initData ? `?initData=${encodeURIComponent(initData)}` : '';
    this.url = `${protocol}//${host}/api/v1/ws${query}`;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        // Resubscribe to chat if previously active
        if (this.currentSubscription) {
          this.subscribeChat(this.currentSubscription.accountId, this.currentSubscription.peerId);
        }
      };

      this.socket.onmessage = (event) => {
        try {
          const payload: WebSocketInboundPayload = JSON.parse(event.data);
          this.listeners.forEach((listener) => listener(payload));
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      this.socket.onclose = () => {
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.socket.onerror = (err) => {
        console.error('WebSocket encountered error:', err);
      };
    } catch (err) {
      console.error('Failed to establish WebSocket:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('Max WebSocket reconnect attempts reached.');
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000);
    this.reconnectAttempts++;
    setTimeout(() => this.connect(), delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ action: 'ping' }));
      }
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  public subscribeChat(accountId: string, peerId: number): void {
    this.currentSubscription = { accountId, peerId };
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'subscribe_chat',
          account_id: accountId,
          peer_id: peerId,
        })
      );
    }
  }

  public sendMessage(
    accountId: string,
    peerId: number,
    text: string,
    tempId: string
  ): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'send_message',
          account_id: accountId,
          peer_id: peerId,
          text,
          temp_id: tempId,
        })
      );
    } else {
      console.error('WebSocket not connected. Unable to send message.');
    }
  }

  public markRead(accountId: string, peerId: number): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'mark_read',
          account_id: accountId,
          peer_id: peerId,
        })
      );
    }
  }

  public sendTyping(accountId: string, peerId: number): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'send_typing',
          account_id: accountId,
          peer_id: peerId,
        })
      );
    }
  }

  public editMessage(
    accountId: string,
    peerId: number,
    telegramMessageId: number,
    newText: string
  ): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'edit_message',
          account_id: accountId,
          peer_id: peerId,
          telegram_message_id: telegramMessageId,
          new_text: newText,
        })
      );
    }
  }

  public deleteMessage(
    accountId: string,
    peerId: number,
    telegramMessageId: number,
    revoke: boolean = true
  ): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          action: 'delete_message',
          account_id: accountId,
          peer_id: peerId,
          telegram_message_id: telegramMessageId,
          revoke,
        })
      );
    }
  }

  public addListener(listener: MessageHandler): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  public disconnect(): void {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const wsClient = new WebSocketClient();
