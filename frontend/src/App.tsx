import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Account, Dialogue, Message, ReplyReference, WebSocketInboundPayload } from './types';
import {
  fetchAccounts,
  fetchDialogues,
  fetchChatHistory,
  markDialogueAsRead,
  reconnectAccount,
  uploadMedia,
} from './services/api';
import { wsClient } from './services/websocket';
import { AccountHub } from './components/AccountHub';
import { AccountSwitcher } from './components/AccountSwitcher';
import { DialogueList } from './components/DialogueList';
import { ClientsDirectory } from './components/ClientsDirectory';
import { ChatView } from './components/Chat/ChatView';
import { useTelegram } from './hooks/useTelegram';
import { MessageSquare, ArrowLeft, Users } from 'lucide-react';

export const App: React.FC = () => {
  const [view, setView] = useState<'hub' | 'client'>('hub');
  const [activeTab, setActiveTab] = useState<'chats' | 'clients'>('chats');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [activeAccount, setActiveAccount] = useState<Account | null>(null);
  const [dialogues, setDialogues] = useState<Dialogue[]>([]);
  const [selectedDialogue, setSelectedDialogue] = useState<Dialogue | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoadingDialogues, setIsLoadingDialogues] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isPeerTyping, setIsPeerTyping] = useState(false);

  const typingTimeoutRef = useRef<any>(null);
  const { startAppTarget, setBackButton, triggerHaptic } = useTelegram();

  // 1. Initial Load of Accounts & Connect WebSocket
  useEffect(() => {
    wsClient.connect();

    fetchAccounts()
      .then((accs) => {
        setAccounts(accs);
        if (accs.length > 0) {
          if (startAppTarget) {
            const targetAcc = accs.find((a) => a.id === startAppTarget.accountId) || accs[0];
            setActiveAccount(targetAcc);
            setView('client');
          } else {
            setActiveAccount(accs[0]);
          }
        }
      })
      .catch((err) => console.error('Failed fetching accounts:', err));

    return () => wsClient.disconnect();
  }, [startAppTarget]);

  // Handle native TMA back button based on view hierarchy
  useEffect(() => {
    if (view === 'client') {
      if (selectedDialogue) {
        setBackButton(true, () => setSelectedDialogue(null));
      } else {
        setBackButton(true, () => {
          triggerHaptic('light');
          setView('hub');
        });
      }
    } else {
      setBackButton(false);
    }
  }, [view, selectedDialogue, setBackButton, triggerHaptic]);

  // 2. Fetch Dialogues when Active Account changes
  const loadDialogues = useCallback(
    async (accountId: string, search?: string) => {
      setIsLoadingDialogues(true);
      try {
        const data = await fetchDialogues(accountId, search);
        setDialogues(data);

        if (startAppTarget && startAppTarget.accountId === accountId) {
          const found = data.find((d) => d.peer_id === startAppTarget.peerId);
          if (found) {
            setSelectedDialogue(found);
          }
        }
      } catch (err) {
        console.error('Error loading dialogues:', err);
      } finally {
        setIsLoadingDialogues(false);
      }
    },
    [startAppTarget]
  );

  useEffect(() => {
    if (activeAccount && view === 'client') {
      loadDialogues(activeAccount.id, searchQuery);
    }
  }, [activeAccount, view, loadDialogues]);

  // Search debounce
  useEffect(() => {
    if (!activeAccount || view !== 'client') return;
    const timer = setTimeout(() => {
      loadDialogues(activeAccount.id, searchQuery);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, activeAccount, view, loadDialogues]);

  // 3. Load Chat History & Subscribe WebSocket when dialogue is selected
  useEffect(() => {
    if (!activeAccount || !selectedDialogue) return;

    setIsLoadingMessages(true);
    setIsPeerTyping(false);
    wsClient.subscribeChat(activeAccount.id, selectedDialogue.peer_id);

    if (selectedDialogue.unread_count > 0) {
      markDialogueAsRead(activeAccount.id, selectedDialogue.peer_id).catch(() => {});
      setDialogues((prev) =>
        prev.map((d) =>
          d.peer_id === selectedDialogue.peer_id ? { ...d, unread_count: 0 } : d
        )
      );
      setAccounts((prev) =>
        prev.map((a) =>
          a.id === activeAccount.id
            ? { ...a, total_unread_dialogues: Math.max(0, a.total_unread_dialogues - 1) }
            : a
        )
      );
    }

    fetchChatHistory(activeAccount.id, selectedDialogue.peer_id)
      .then((history) => setMessages(history))
      .catch((err) => console.error('Error loading chat history:', err))
      .finally(() => setIsLoadingMessages(false));
  }, [activeAccount, selectedDialogue]);

  // 4. Handle incoming real-time WebSocket events (two-way sync)
  useEffect(() => {
    const unsubscribe = wsClient.addListener((payload: WebSocketInboundPayload) => {
      if (payload.type === 'new_message' && payload.peer_id) {
        if (selectedDialogue && selectedDialogue.peer_id === payload.peer_id) {
          const newMsg: Message = {
            id: payload.message_id || `msg_${Date.now()}`,
            account_id: payload.account_id || '',
            peer_id: payload.peer_id,
            telegram_message_id: payload.telegram_message_id,
            sender_id: payload.peer_id,
            is_outgoing: false,
            is_edited: false,
            text: payload.text,
            media_type: payload.media_type,
            media_url: payload.media_url,
            media_filename: payload.media_filename,
            media_size: payload.media_size,
            status: 'RECEIVED',
            created_at: payload.created_at || new Date().toISOString(),
          };
          setMessages((prev) => [...prev, newMsg]);

          if (activeAccount) {
            wsClient.markRead(activeAccount.id, payload.peer_id);
          }
        }

        // Update dialogue list
        setDialogues((prev) =>
          prev.map((d) => {
            if (d.peer_id === payload.peer_id) {
              const isCurrentChat = selectedDialogue?.peer_id === payload.peer_id;
              return {
                ...d,
                last_message_text: payload.text || `[${payload.media_type || 'Media'}]`,
                last_message_at: payload.created_at || new Date().toISOString(),
                unread_count: isCurrentChat ? 0 : d.unread_count + 1,
              };
            }
            return d;
          })
        );

        // Update total unread across account cards
        setAccounts((prev) =>
          prev.map((a) =>
            a.id === payload.account_id
              ? { ...a, total_unread_dialogues: (a.total_unread_dialogues || 0) + 1 }
              : a
          )
        );
      }

      if (payload.type === 'message_delivered' && payload.temp_id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.temp_id === payload.temp_id
              ? {
                  ...m,
                  id: payload.message_id || m.id,
                  telegram_message_id: payload.telegram_message_id,
                  status: 'DELIVERED',
                }
              : m
          )
        );
      }

      if (payload.type === 'message_edited' && payload.telegram_message_id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.telegram_message_id === payload.telegram_message_id
              ? { ...m, text: payload.text || payload.new_text, is_edited: true }
              : m
          )
        );
      }

      if (payload.type === 'messages_deleted' && payload.deleted_ids) {
        const deletedSet = new Set(payload.deleted_ids);
        setMessages((prev) =>
          prev.filter((m) => !m.telegram_message_id || !deletedSet.has(m.telegram_message_id))
        );
      }

      if (payload.type === 'user_typing' && selectedDialogue && payload.peer_id === selectedDialogue.peer_id) {
        setIsPeerTyping(true);
        if (typingTimeoutRef.current) {
          clearTimeout(typingTimeoutRef.current);
        }
        typingTimeoutRef.current = setTimeout(() => {
          setIsPeerTyping(false);
        }, 3500);
      }
    });

    return unsubscribe;
  }, [selectedDialogue, activeAccount]);

  // 5. Send Outbound Message (Text or Media)
  const handleSendMessage = async (
    text: string,
    replyTo?: ReplyReference | null,
    file?: File | null
  ) => {
    if (!activeAccount || !selectedDialogue) return;

    if (file) {
      try {
        const result = await uploadMedia(activeAccount.id, selectedDialogue.peer_id, file, text);
        setMessages((prev) => [...prev, result]);
      } catch (err) {
        console.error('Failed to upload and dispatch media:', err);
      }
      return;
    }

    const tempId = `temp_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const nowIso = new Date().toISOString();

    const optimisticMessage: Message = {
      id: tempId,
      temp_id: tempId,
      account_id: activeAccount.id,
      peer_id: selectedDialogue.peer_id,
      sender_id: 0,
      is_outgoing: true,
      is_edited: false,
      text,
      reply_to: replyTo,
      status: 'PENDING',
      created_at: nowIso,
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    wsClient.sendMessage(activeAccount.id, selectedDialogue.peer_id, text, tempId);

    setDialogues((prev) =>
      prev.map((d) =>
        d.peer_id === selectedDialogue.peer_id
          ? { ...d, last_message_text: text, last_message_at: nowIso }
          : d
      )
    );
  };

  const handleSaveEdit = (message: Message, newText: string) => {
    if (!activeAccount || !selectedDialogue || !message.telegram_message_id) return;
    wsClient.editMessage(
      activeAccount.id,
      selectedDialogue.peer_id,
      message.telegram_message_id,
      newText
    );
  };

  const handleDeleteMessage = (message: Message) => {
    if (!activeAccount || !selectedDialogue || !message.telegram_message_id) return;
    wsClient.deleteMessage(
      activeAccount.id,
      selectedDialogue.peer_id,
      message.telegram_message_id,
      true
    );
  };

  const handleTyping = () => {
    if (!activeAccount || !selectedDialogue) return;
    wsClient.sendTyping(activeAccount.id, selectedDialogue.peer_id);
  };

  const handleReconnect = async (accId: string) => {
    try {
      await reconnectAccount(accId);
      const updated = await fetchAccounts();
      setAccounts(updated);
    } catch (err) {
      console.error('Reconnect failed:', err);
    }
  };

  const refreshAccounts = useCallback(() => {
    fetchAccounts().then((accs) => setAccounts(accs)).catch(console.error);
  }, []);

  const handleSelectAccountFromHub = (acc: Account) => {
    setActiveAccount(acc);
    setSelectedDialogue(null);
    setMessages([]);
    setView('client');
  };

  const handleOpenClientChat = (client: any) => {
    const tgUsername = (client.telegram || '').replace('@', '').toLowerCase();
    const match = dialogues.find(
      (d) =>
        (d.peer_username && d.peer_username.toLowerCase() === tgUsername) ||
        d.peer_name.toLowerCase().includes(client.name.toLowerCase())
    );

    if (match) {
      setSelectedDialogue(match);
      setActiveTab('chats');
    } else {
      const tempDialogue: Dialogue = {
        id: `client-${client.id}`,
        account_id: activeAccount?.id || 'default',
        peer_id: client.id * 1000,
        peer_name: client.name,
        peer_username: tgUsername || null,
        unread_count: 0,
        last_message_text: `StudioCRM: ${client.contactPerson || client.name}`,
        last_message_at: client.createdAt,
      };
      setSelectedDialogue(tempDialogue);
      setActiveTab('chats');
    }
  };

  // View Mode A: Dedicated Account Hub Screen
  if (view === 'hub') {
    return (
      <AccountHub
        accounts={accounts}
        onSelectAccount={handleSelectAccountFromHub}
        onReconnect={handleReconnect}
        onRefreshAccounts={refreshAccounts}
      />
    );
  }

  // View Mode B: Telegram Web Client for the Selected Account
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0e1621] text-white">
      {/* Left Column: Client Header & Dialogue List */}
      <div
        className={`w-full md:w-[340px] lg:w-[380px] h-full flex flex-col flex-shrink-0 z-10 ${
          selectedDialogue ? 'hidden md:flex' : 'flex'
        }`}
      >
        {/* App Header with Back-to-Hub & Account Switcher */}
        <div className="h-14 bg-[#17212b] border-b border-[#232e3c] flex items-center justify-between px-3 flex-shrink-0 gap-2">
          <button
            onClick={() => {
              triggerHaptic('light');
              setView('hub');
            }}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-[#202b36] hover:bg-[#2b5278] text-[#4faeef] hover:text-white rounded-lg text-xs font-semibold transition-colors flex-shrink-0"
            title="Return to Accounts Hub"
          >
            <ArrowLeft size={15} />
            <span>All Accounts</span>
          </button>

          <AccountSwitcher
            accounts={accounts}
            activeAccount={activeAccount}
            onSelectAccount={(acc) => setActiveAccount(acc)}
            onReconnect={handleReconnect}
          />
        </div>

        {/* View Switcher: Chats <-> Clients */}
        <div className="flex items-center p-1.5 bg-[#0e1621] border-b border-[#232e3c] gap-1 flex-shrink-0">
          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveTab('chats');
            }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'chats'
                ? 'bg-[#3390ec] text-white shadow'
                : 'text-[#708499] hover:text-white'
            }`}
          >
            <MessageSquare size={13} />
            <span>💬 Чаты</span>
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveTab('clients');
            }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'clients'
                ? 'bg-[#3390ec] text-white shadow'
                : 'text-[#708499] hover:text-white'
            }`}
          >
            <Users size={13} />
            <span>👥 Клиенты</span>
          </button>
        </div>

        {/* Content Pane: Dialogue List OR Clients Directory */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'chats' ? (
            <DialogueList
              dialogues={dialogues}
              selectedDialogue={selectedDialogue}
              onSelectDialogue={(d) => setSelectedDialogue(d)}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              isLoading={isLoadingDialogues}
            />
          ) : (
            <ClientsDirectory onOpenClientChat={handleOpenClientChat} />
          )}
        </div>
      </div>

      {/* Right Column: Chat View */}
      <div
        className={`flex-1 h-full flex flex-col ${
          selectedDialogue ? 'flex' : 'hidden md:flex'
        }`}
      >
        {selectedDialogue && activeAccount ? (
          <ChatView
            dialogue={selectedDialogue}
            messages={messages}
            isPeerTyping={isPeerTyping}
            isAccountBanned={activeAccount.status === 'BANNED'}
            onSendMessage={handleSendMessage}
            onSaveEdit={handleSaveEdit}
            onDeleteMessage={handleDeleteMessage}
            onTyping={handleTyping}
            onBack={() => setSelectedDialogue(null)}
            isLoading={isLoadingMessages}
          />
        ) : (
          <div className="hidden md:flex flex-col items-center justify-center h-full bg-[#0f141c] telegram-doodle-bg text-[#708499] select-none">
            <div className="w-16 h-16 rounded-full bg-[#17212b] flex items-center justify-center mb-3 shadow-md border border-[#232e3c]">
              <MessageSquare size={30} className="text-[#3390ec]" />
            </div>
            <span className="text-base font-semibold text-white">Select a chat to start messaging</span>
            <span className="text-xs text-[#708499] mt-1 max-w-xs text-center">
              Operating as <strong className="text-white">{activeAccount?.title}</strong> ({activeAccount?.phone}).
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
