import { Account, Dialogue, Message } from '../types';

const API_BASE = '/api/v1';

function getAuthHeaders(): HeadersInit {
  const initData = window.Telegram?.WebApp?.initData || '';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }
  return headers;
}

export async function fetchAccounts(): Promise<Account[]> {
  const res = await fetch(`${API_BASE}/accounts`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to load accounts: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDialogues(
  accountId: string,
  search?: string,
  limit: number = 50,
  offset: number = 0
): Promise<Dialogue[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (search && search.trim()) {
    params.set('search', search.trim());
  }

  const res = await fetch(`${API_BASE}/accounts/${accountId}/dialogues?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to load dialogues: ${res.statusText}`);
  }
  return res.json();
}

export async function markDialogueAsRead(
  accountId: string,
  peerId: number
): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/dialogues/${peerId}/read`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to mark dialogue as read: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchChatHistory(
  accountId: string,
  peerId: number,
  limit: number = 50,
  beforeMsgId?: number
): Promise<Message[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
  });
  if (beforeMsgId) {
    params.set('before_msg_id', beforeMsgId.toString());
  }

  const res = await fetch(
    `${API_BASE}/accounts/${accountId}/dialogues/${peerId}/messages?${params.toString()}`,
    {
      headers: getAuthHeaders(),
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch messages: ${res.statusText}`);
  }
  return res.json();
}

export async function reconnectAccount(
  accountId: string
): Promise<{ success: boolean; status: string }> {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/reconnect`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to reconnect account: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadMedia(
  accountId: string,
  peerId: number,
  file: File,
  caption?: string
): Promise<Message> {
  const formData = new FormData();
  formData.append('file', file);
  if (caption) {
    formData.append('caption', caption);
  }

  const initData = window.Telegram?.WebApp?.initData || '';
  const headers: Record<string, string> = {};
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }

  const res = await fetch(`${API_BASE}/accounts/${accountId}/dialogues/${peerId}/media`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Failed to upload media: ${res.statusText}`);
  }
  return res.json();
}

export async function importSessionFile(
  file: File,
  customTitle?: string,
  proxyId?: string
): Promise<Account> {
  const formData = new FormData();
  formData.append('file', file);
  if (customTitle) formData.append('custom_title', customTitle);
  if (proxyId) formData.append('proxy_id', proxyId);

  const initData = window.Telegram?.WebApp?.initData || '';
  const headers: Record<string, string> = {};
  if (initData) headers['X-Telegram-Init-Data'] = initData;

  const res = await fetch(`${API_BASE}/accounts/import-file`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to import session: ${res.statusText}`);
  }
  return res.json();
}

export async function updateAccountAlias(
  accountId: string,
  customTitle: string
): Promise<{ custom_title: string }> {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/alias`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ custom_title: customTitle }),
  });
  if (!res.ok) {
    throw new Error(`Failed to update alias: ${res.statusText}`);
  }
  return res.json();
}

export async function updateTelegramProfile(
  accountId: string,
  data: { first_name?: string; last_name?: string; about?: string; username?: string }
): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/profile`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update profile: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadAccountAvatar(
  accountId: string,
  file: File
): Promise<{ status: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const initData = window.Telegram?.WebApp?.initData || '';
  const headers: Record<string, string> = {};
  if (initData) headers['X-Telegram-Init-Data'] = initData;

  const res = await fetch(`${API_BASE}/accounts/${accountId}/profile/avatar`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Failed to upload avatar: ${res.statusText}`);
  }
  return res.json();
}

export async function terminateOtherSessions(
  accountId: string
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/accounts/${accountId}/terminate-sessions`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to terminate sessions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchStudioCRMClients(params?: {
  search?: string;
  filter_24h?: boolean;
  has_orders?: boolean;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.filter_24h) query.set('filter_24h', 'true');
  if (params?.has_orders) query.set('has_orders', 'true');

  const res = await fetch(`${API_BASE}/clients?${query.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to load StudioCRM clients: ${res.statusText}`);
  }
  return res.json();
}

export async function trigger24hLeadSync(): Promise<{ synced_leads: number }> {
  const res = await fetch(`${API_BASE}/clients/sync-24h`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger 24h lead sync: ${res.statusText}`);
  }
  return res.json();
}

export async function createInChatOrder(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/orders`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create order: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchOrdersByPeer(peerId: number, username?: string): Promise<any[]> {
  const q = username ? `?username=${encodeURIComponent(username)}` : '';
  const res = await fetch(`${API_BASE}/orders/by-peer/${peerId}${q}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return [];
  }
  return res.json();
}
