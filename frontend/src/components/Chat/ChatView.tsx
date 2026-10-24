import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, ChevronDown, MoreVertical, Trash2, X, Lock, Briefcase, Check, Plus } from 'lucide-react';
import { Dialogue, Message, ReplyReference } from '../../types';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { getAvatarGradientClass, getInitials, useTelegram } from '../../hooks/useTelegram';
import { createInChatOrder, fetchOrdersByPeer } from '../../services/api';

interface ChatViewProps {
  dialogue: Dialogue;
  messages: Message[];
  isPeerTyping?: boolean;
  onSendMessage: (text: string, replyTo?: ReplyReference | null, file?: File | null) => void;
  onSaveEdit?: (message: Message, newText: string) => void;
  onDeleteMessage?: (message: Message) => void;
  onTyping?: () => void;
  onBack: () => void;
  isLoading: boolean;
  isAccountBanned?: boolean;
}

function formatDateSeparator(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();

  if (date.toDateString() === now.toDateString()) {
    return 'Today';
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }

  return date.toLocaleDateString([], { month: 'long', day: 'numeric' });
}

export const ChatView: React.FC<ChatViewProps> = ({
  dialogue,
  messages,
  isPeerTyping = false,
  onSendMessage,
  onSaveEdit,
  onDeleteMessage,
  onTyping,
  onBack,
  isLoading,
  isAccountBanned = false,
}) => {
  const [replyingTo, setReplyingTo] = useState<ReplyReference | null>(null);
  const [editingMessage, setEditingMessage] = useState<Message | null>(null);
  const [deletingMessage, setDeletingMessage] = useState<Message | null>(null);
  const [zoomedPhotoUrl, setZoomedPhotoUrl] = useState<string | null>(null);

  // In-Chat Order State
  const [activeDeal, setActiveDeal] = useState<any | null>(null);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [orderTitle, setOrderTitle] = useState('Разработка проекта');
  const [orderCost, setOrderCost] = useState('50000');
  const [orderDeadline, setOrderDeadline] = useState('');
  const [orderNotes, setOrderNotes] = useState('');
  const [orderStatus, setOrderStatus] = useState('New');
  const [isCreatingOrder, setIsCreatingOrder] = useState(false);
  const [orderSuccessNotice, setOrderSuccessNotice] = useState<string | null>(null);

  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const [newMessagesWhileScrolled, setNewMessagesWhileScrolled] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);
  const lastScrollTopRef = useRef<number>(0);
  const { setBackButton, triggerHaptic } = useTelegram();

  useEffect(() => {
    fetchOrdersByPeer(dialogue.peer_id, dialogue.peer_username || undefined)
      .then((orders) => {
        if (orders && orders.length > 0) {
          setActiveDeal(orders[0]);
        } else {
          setActiveDeal(null);
        }
      })
      .catch(() => setActiveDeal(null));
  }, [dialogue.peer_id, dialogue.peer_username]);

  const handleCreateOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderTitle.trim() || !orderCost) return;
    setIsCreatingOrder(true);
    triggerHaptic('medium');
    try {
      const res = await createInChatOrder({
        account_id: dialogue.account_id,
        peer_id: dialogue.peer_id,
        peer_name: dialogue.peer_name,
        peer_username: dialogue.peer_username,
        title: orderTitle.trim(),
        total_cost: parseFloat(orderCost) || 0,
        deadline: orderDeadline || undefined,
        notes: orderNotes.trim() || undefined,
        status: orderStatus,
      });

      const createdOrder = res.order || {
        orderNumber: 'ORD-2026-NEW',
        title: orderTitle.trim(),
        totalCost: parseFloat(orderCost),
        status: orderStatus,
      };

      setActiveDeal(createdOrder);
      setOrderSuccessNotice(`Заказ ${createdOrder.orderNumber} успешно создан в StudioCRM!`);
      setTimeout(() => {
        setOrderSuccessNotice(null);
        setIsOrderModalOpen(false);
      }, 1500);
    } catch (err: any) {
      alert(err.message || 'Ошибка при создании заказа');
    } finally {
      setIsCreatingOrder(false);
    }
  };

  useEffect(() => {
    setBackButton(true, onBack);
    return () => setBackButton(false);
  }, [setBackButton, onBack]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setNewMessagesWhileScrolled(0);
    }
  }, [dialogue.id]);

  useEffect(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 120;

    if (isNearBottom) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setNewMessagesWhileScrolled(0);
    } else {
      setNewMessagesWhileScrolled((prev) => prev + 1);
    }
  }, [messages]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 150;
    setShowScrollBottom(isUp);

    if (!isUp) {
      setNewMessagesWhileScrolled(0);
    }
    lastScrollTopRef.current = scrollTop;
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
      setNewMessagesWhileScrolled(0);
    }
  };

  const handleReplyMessage = (msg: Message) => {
    setReplyingTo({
      message_id: msg.telegram_message_id || msg.id,
      sender_name: msg.is_outgoing ? 'You' : dialogue.peer_name,
      text_preview: msg.text || `[${msg.media_type || 'Media'}]`,
    });
  };

  const handleConfirmDelete = () => {
    if (deletingMessage && onDeleteMessage) {
      onDeleteMessage(deletingMessage);
      setDeletingMessage(null);
    }
  };

  // Group messages by date
  const renderedItems: React.ReactNode[] = [];
  let lastDateChip: string | null = null;

  messages.forEach((msg, idx) => {
    const dateChip = formatDateSeparator(msg.created_at);
    if (dateChip !== lastDateChip) {
      renderedItems.push(
        <div key={`date-${dateChip}-${idx}`} className="flex justify-center my-3 select-none">
          <div className="bg-[#000000]/40 backdrop-blur-md text-[#ffffff]/90 text-[12px] font-medium px-2.5 py-0.5 rounded-full shadow-sm">
            {dateChip}
          </div>
        </div>
      );
      lastDateChip = dateChip;
    }

    const nextMsg = messages[idx + 1];
    const isLastInGroup = !nextMsg || nextMsg.is_outgoing !== msg.is_outgoing;

    renderedItems.push(
      <MessageBubble
        key={msg.id || msg.temp_id || idx}
        message={msg}
        isLastInGroup={isLastInGroup}
        onReply={handleReplyMessage}
        onEdit={(m) => setEditingMessage(m)}
        onDelete={(m) => setDeletingMessage(m)}
        onZoomPhoto={(url) => setZoomedPhotoUrl(url)}
      />
    );
  });

  return (
    <div className="flex flex-col h-full bg-[#0f141c] relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#17212b] border-b border-[#232e3c] z-20 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="p-1 text-[#708499] hover:text-white rounded-full hover:bg-[#202b36] md:hidden transition-colors"
          >
            <ArrowLeft size={20} />
          </button>

          <div
            className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center font-bold text-white text-sm shadow-sm ${getAvatarGradientClass(
              dialogue.peer_id
            )}`}
          >
            {getInitials(dialogue.peer_name)}
          </div>

          <div className="flex flex-col min-w-0">
            <span className="font-semibold text-sm text-white truncate leading-tight">
              {dialogue.peer_name}
            </span>

            {/* Reactive Typing Status Indicator */}
            {isPeerTyping ? (
              <div className="flex items-center gap-1 text-[12px] text-[#3390ec] font-medium leading-tight">
                <span>typing</span>
                <span className="animate-pulse">...</span>
              </div>
            ) : (
              <span className="text-[12px] text-[#708499] truncate leading-tight">
                {dialogue.peer_username ? `@${dialogue.peer_username}` : `ID: ${dialogue.peer_id}`}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {activeDeal ? (
            <button
              onClick={() => setIsOrderModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-[#53df83]/15 hover:bg-[#53df83]/25 border border-[#53df83]/40 text-[#53df83] text-xs font-semibold rounded-xl transition-all shadow-sm"
              title="Просмотреть/изменить заказ в StudioCRM"
            >
              <Briefcase size={13} />
              <span>{activeDeal.orderNumber}: {Number(activeDeal.totalCost).toLocaleString('ru-RU')} ₽</span>
            </button>
          ) : (
            <button
              onClick={() => setIsOrderModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-[#202b36] hover:bg-[#3390ec] text-[#4faeef] hover:text-white border border-[#232e3c] text-xs font-semibold rounded-xl transition-all shadow-sm"
              title="Создать заказ в StudioCRM"
            >
              <Briefcase size={13} />
              <span>Создать заказ</span>
            </button>
          )}

          <button
            className="p-2 text-[#708499] hover:text-white rounded-full hover:bg-[#202b36] transition-colors"
            title="More options"
          >
            <MoreVertical size={18} />
          </button>
        </div>
      </div>

      {/* Messages Canvas */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3.5 py-3 telegram-doodle-bg z-10 flex flex-col"
      >
        {isLoading && messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-[#708499]">
            Loading chat history...
          </div>
        ) : (
          renderedItems
        )}
      </div>

      {/* Floating Scroll to Bottom Button */}
      {showScrollBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-20 right-4 z-30 w-10 h-10 rounded-full bg-[#17212b] border border-[#232e3c] text-[#708499] hover:text-white flex items-center justify-center shadow-xl hover:bg-[#202b36] transition-all animate-in fade-in zoom-in-75 duration-150"
        >
          <ChevronDown size={20} />
          {newMessagesWhileScrolled > 0 && (
            <span className="absolute -top-1.5 -right-1.5 bg-[#3390ec] text-white text-[11px] font-bold min-w-5 h-5 px-1 rounded-full flex items-center justify-center shadow">
              {newMessagesWhileScrolled}
            </span>
          )}
        </button>
      )}

      {/* Chat Input Bar or Banned Vault Notice */}
      {isAccountBanned ? (
        <div className="p-4 bg-[#17212b] border-t border-[#232e3c] flex items-center justify-center gap-2.5 text-xs md:text-sm text-[#ff596a] font-medium text-center shadow-lg">
          <Lock size={18} className="flex-shrink-0" />
          <span>🔒 Этот аккаунт заблокирован в Telegram. Доступен режим архива (только чтение истории и контактов).</span>
        </div>
      ) : (
        <ChatInput
          onSendMessage={onSendMessage}
          onSaveEdit={onSaveEdit}
          onTyping={onTyping}
          replyingTo={replyingTo}
          editingMessage={editingMessage}
          onCancelReply={() => setReplyingTo(null)}
          onCancelEdit={() => setEditingMessage(null)}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deletingMessage && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#17212b] border border-[#232e3c] rounded-2xl p-5 max-w-sm w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-[#ff596a] mb-3">
              <div className="w-10 h-10 rounded-full bg-[#ff596a]/15 flex items-center justify-center">
                <Trash2 size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Delete Message?</h3>
            </div>
            <p className="text-xs text-[#708499] mb-5 leading-relaxed">
              This message will be deleted from Telegram cloud servers for both you and{' '}
              <strong className="text-white">{dialogue.peer_name}</strong>.
            </p>
            <div className="flex items-center justify-end gap-2.5">
              <button
                onClick={() => setDeletingMessage(null)}
                className="px-4 py-2 rounded-lg text-sm text-[#708499] hover:text-white hover:bg-[#202b36] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#ff596a] hover:bg-[#ff3b4e] text-white transition-colors shadow"
              >
                Delete for everyone
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order / Deal Creation Modal */}
      {isOrderModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#17212b] border border-[#232e3c] rounded-2xl p-5 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[#232e3c]">
              <div className="flex items-center gap-2">
                <Briefcase size={18} className="text-[#3390ec]" />
                <h3 className="text-base font-bold text-white">
                  {activeDeal ? `Заказ ${activeDeal.orderNumber}` : 'Создать заказ в StudioCRM'}
                </h3>
              </div>
              <button onClick={() => setIsOrderModalOpen(false)} className="text-[#708499] hover:text-white">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateOrderSubmit} className="mt-4 space-y-3.5">
              <div>
                <label className="text-xs text-[#708499] block mb-1 font-medium">Клиент</label>
                <div className="p-2.5 bg-[#0e1621] rounded-xl border border-[#232e3c] text-xs text-white flex items-center justify-between">
                  <span className="font-semibold">{dialogue.peer_name}</span>
                  <span className="text-[#4faeef]">
                    {dialogue.peer_username ? `@${dialogue.peer_username}` : `ID: ${dialogue.peer_id}`}
                  </span>
                </div>
              </div>

              <div>
                <label className="text-xs text-[#708499] block mb-1 font-medium">Название проекта / заказа *</label>
                <input
                  type="text"
                  required
                  value={orderTitle}
                  onChange={(e) => setOrderTitle(e.target.value)}
                  placeholder="Например: Разработка Telegram Mini App"
                  className="w-full bg-[#0e1621] text-sm text-white px-3.5 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#708499] block mb-1 font-medium">Сумма (₽) *</label>
                  <input
                    type="number"
                    required
                    min="0"
                    step="1000"
                    value={orderCost}
                    onChange={(e) => setOrderCost(e.target.value)}
                    className="w-full bg-[#0e1621] text-sm text-white px-3.5 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#708499] block mb-1 font-medium">Статус</label>
                  <select
                    value={orderStatus}
                    onChange={(e) => setOrderStatus(e.target.value)}
                    className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                  >
                    <option value="New">Новый</option>
                    <option value="InProgress">В работе</option>
                    <option value="PendingPayment">Ожидает оплаты</option>
                    <option value="Completed">Выполнен</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-[#708499] block mb-1 font-medium">Дедлайн сдачи</label>
                <input
                  type="date"
                  value={orderDeadline}
                  onChange={(e) => setOrderDeadline(e.target.value)}
                  className="w-full bg-[#0e1621] text-sm text-white px-3.5 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-[#708499] block mb-1 font-medium">Заметки / ТЗ</label>
                <textarea
                  rows={2}
                  value={orderNotes}
                  onChange={(e) => setOrderNotes(e.target.value)}
                  placeholder="Дополнительные детали заказа..."
                  className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none resize-none"
                />
              </div>

              {orderSuccessNotice && (
                <div className="p-3 bg-[#53df83]/15 border border-[#53df83]/30 rounded-xl text-xs text-[#53df83] flex items-center gap-2">
                  <Check size={16} />
                  <span>{orderSuccessNotice}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsOrderModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-[#708499] hover:text-white"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={isCreatingOrder}
                  className="px-5 py-2 text-xs font-semibold bg-[#3390ec] hover:bg-[#4faeef] text-white rounded-xl shadow transition-all active:scale-95"
                >
                  {isCreatingOrder ? 'Создание...' : 'Сохранить в StudioCRM'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Photo Zoom Modal */}
      {zoomedPhotoUrl && (
        <div
          onClick={() => setZoomedPhotoUrl(null)}
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-pointer"
        >
          <button
            onClick={() => setZoomedPhotoUrl(null)}
            className="absolute top-4 right-4 p-2 text-white/80 hover:text-white rounded-full bg-black/40"
          >
            <X size={24} />
          </button>
          <img
            src={zoomedPhotoUrl}
            alt="Enlarged"
            className="max-h-[90vh] max-w-[90vw] object-contain rounded-xl shadow-2xl animate-in zoom-in-90 duration-200"
          />
        </div>
      )}
    </div>
  );
};
