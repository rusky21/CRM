export interface Account {
  id: string;
  phone: string;
  title: string;
  custom_title?: string | null;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  about?: string | null;
  status: 'ACTIVE' | 'CONNECTING' | 'NEEDS_AUTH' | 'OFFLINE' | 'FLOOD_WAIT' | 'BANNED';
  is_connected: boolean;
  total_unread_dialogues: number;
  proxy?: {
    id?: string;
    host: string;
    port: number;
    protocol: string;
    latency_ms?: number | null;
  } | null;
  device_model?: string | null;
  created_at?: string;
}

export interface ProfileUpdatePayload {
  first_name?: string;
  last_name?: string;
  about?: string;
  username?: string;
}

export interface StudioCRMClient {
  id: number;
  name: string;
  contactPerson?: string | null;
  phone?: string | null;
  email?: string | null;
  telegram?: string | null;
  notes?: string | null;
  createdAt?: string;
  total_orders: number;
  total_revenue: number;
  active_deal?: {
    id?: number;
    orderNumber: string;
    title: string;
    status: string;
    totalCost: number;
    deadline?: string | null;
  } | null;
  orders?: any[];
}

export interface OrderCreatePayload {
  account_id?: string;
  peer_id: number;
  peer_name: string;
  peer_username?: string | null;
  title: string;
  total_cost: number;
  deadline?: string | null;
  notes?: string | null;
  status?: string;
}

export interface Dialogue {
  id: string;
  account_id: string;
  peer_id: number;
  peer_name: string;
  peer_username?: string | null;
  unread_count: number;
  last_message_text?: string | null;
  last_message_at?: string | null;
  updated_at?: string | null;
}

export interface ReplyReference {
  message_id: string | number;
  sender_name: string;
  text_preview: string;
}

export interface MediaAttachment {
  type: 'photo' | 'document' | 'voice' | 'video' | 'audio';
  url?: string;
  filename?: string;
  size_bytes?: number;
  duration_seconds?: number;
}

export interface Message {
  id: string;
  temp_id?: string;
  dialogue_id?: string | null;
  account_id: string;
  peer_id: number;
  telegram_message_id?: number;
  sender_id: number;
  is_outgoing: boolean;
  is_edited?: boolean;
  text?: string | null;
  media_type?: string | null;
  media_url?: string | null;
  media_filename?: string | null;
  media_size?: number | null;
  media?: MediaAttachment;
  reply_to?: ReplyReference | null;
  status: 'RECEIVED' | 'PENDING' | 'DELIVERED' | 'READ';
  created_at: string;
}

export interface WebSocketInboundPayload {
  type:
    | 'new_message'
    | 'message_delivered'
    | 'read_acknowledged'
    | 'send_failed'
    | 'pong'
    | 'message_edited'
    | 'messages_deleted'
    | 'user_typing';
  temp_id?: string;
  message_id?: string;
  telegram_message_id?: number;
  account_id?: string;
  peer_id?: number;
  text?: string;
  new_text?: string;
  deleted_ids?: number[];
  is_edited?: boolean;
  action?: string;
  media_type?: string | null;
  media_url?: string | null;
  media_filename?: string | null;
  media_size?: number | null;
  status?: 'RECEIVED' | 'PENDING' | 'DELIVERED' | 'READ';
  created_at?: string;
  error?: string;
}
