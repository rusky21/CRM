import React, { useState, useEffect } from 'react';
import {
  Search,
  Users,
  Briefcase,
  Flame,
  MessageSquare,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Building,
  Phone,
  Send,
} from 'lucide-react';
import { StudioCRMClient } from '../types';
import { fetchStudioCRMClients, trigger24hLeadSync } from '../services/api';
import { getAvatarGradientClass, getInitials, useTelegram } from '../hooks/useTelegram';

interface ClientsDirectoryProps {
  onOpenClientChat: (client: StudioCRMClient) => void;
}

export const ClientsDirectory: React.FC<ClientsDirectoryProps> = ({ onOpenClientChat }) => {
  const [clients, setClients] = useState<StudioCRMClient[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | '24h' | 'orders'>('all');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  const { triggerHaptic } = useTelegram();

  const loadClients = async () => {
    setIsLoading(true);
    try {
      const data = await fetchStudioCRMClients({
        search: searchQuery || undefined,
        filter_24h: activeFilter === '24h',
        has_orders: activeFilter === 'orders',
      });
      setClients(data);
    } catch (err) {
      console.error('Failed to load StudioCRM clients:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, [activeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadClients();
  };

  const handleSync24h = async () => {
    setIsSyncing(true);
    triggerHaptic('medium');
    try {
      const res = await trigger24hLeadSync();
      setSyncNotice(`Синхронизировано ${res.synced_leads} новых лидов из Telegram!`);
      setTimeout(() => setSyncNotice(null), 4000);
      loadClients();
    } catch (err: any) {
      alert(err.message || 'Ошибка синхронизации');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#0e1621] text-white select-none overflow-hidden">
      {/* Top Header & Search */}
      <div className="px-4 pt-4 pb-3 bg-[#17212b] border-b border-[#232e3c] flex flex-col gap-3 flex-shrink-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Users size={20} className="text-[#3390ec]" />
              <span>База клиентов StudioCRM</span>
            </h2>
            <span className="bg-[#202b36] border border-[#232e3c] text-[#708499] text-xs font-semibold px-2 py-0.5 rounded-full">
              {clients.length}
            </span>
          </div>

          <button
            disabled={isSyncing}
            onClick={handleSync24h}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#202b36] hover:bg-[#3390ec] text-[#4faeef] hover:text-white text-xs font-semibold rounded-xl border border-[#232e3c] transition-all active:scale-95 shadow-sm"
          >
            <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
            <span>{isSyncing ? 'Синхронизация...' : 'Синхр. 24ч'}</span>
          </button>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search size={16} className="absolute left-3.5 top-2.5 text-[#708499]" />
          <input
            type="text"
            placeholder="Поиск по компании, контактному лицу, телефону или @username..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0e1621] text-sm text-white placeholder-[#708499] pl-9 pr-3.5 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none transition-colors"
          />
        </form>

        {/* Filter Pills */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveFilter('all');
            }}
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
              activeFilter === 'all'
                ? 'bg-[#3390ec] text-white shadow'
                : 'bg-[#0e1621] text-[#708499] hover:text-white border border-[#232e3c]'
            }`}
          >
            Все клиенты
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveFilter('24h');
            }}
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all flex items-center gap-1 ${
              activeFilter === '24h'
                ? 'bg-[#3390ec] text-white shadow'
                : 'bg-[#0e1621] text-[#708499] hover:text-white border border-[#232e3c]'
            }`}
          >
            <Flame size={13} className="text-[#ff9800]" />
            <span>Активны за 24ч</span>
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              setActiveFilter('orders');
            }}
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all flex items-center gap-1 ${
              activeFilter === 'orders'
                ? 'bg-[#3390ec] text-white shadow'
                : 'bg-[#0e1621] text-[#708499] hover:text-white border border-[#232e3c]'
            }`}
          >
            <Briefcase size={13} className="text-[#53df83]" />
            <span>С заказами</span>
          </button>
        </div>

        {syncNotice && (
          <div className="p-2.5 bg-[#53df83]/15 border border-[#53df83]/30 rounded-xl text-xs text-[#53df83] font-medium animate-in fade-in">
            {syncNotice}
          </div>
        )}
      </div>

      {/* Clients Cards List */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-[#708499] text-xs">
            Загрузка клиентов из StudioCRM...
          </div>
        ) : clients.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-56 text-center text-[#708499]">
            <Users size={36} className="mb-2 opacity-40 text-[#3390ec]" />
            <p className="text-sm font-semibold text-white">Клиенты не найдены</p>
            <p className="text-xs mt-1 max-w-xs">
              В центральной базе StudioCRM пока нет клиентов, соответствующих выбранному фильтру.
            </p>
          </div>
        ) : (
          clients.map((c) => (
            <div
              key={c.id}
              onClick={() => {
                triggerHaptic('light');
                onOpenClientChat(c);
              }}
              className="flex items-center justify-between p-4 rounded-2xl bg-[#17212b]/80 border border-[#232e3c] hover:bg-[#17212b] hover:border-[#3390ec]/60 transition-all cursor-pointer group shadow-sm"
            >
              {/* Left: Avatar & Meta */}
              <div className="flex items-center gap-3.5 min-w-0">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-white text-base shadow flex-shrink-0 ${getAvatarGradientClass(
                    c.id
                  )}`}
                >
                  {getInitials(c.name)}
                </div>

                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm md:text-base text-white truncate group-hover:text-[#4faeef] transition-colors">
                      {c.name}
                    </span>
                    {c.contactPerson && (
                      <span className="text-xs text-[#708499] hidden sm:inline">
                        • {c.contactPerson}
                      </span>
                    )}
                  </div>

                  {/* Subtitle: Phone & Telegram */}
                  <div className="flex items-center gap-2 text-xs text-[#708499] mt-0.5 flex-wrap">
                    {c.phone && <span>{c.phone}</span>}
                    {c.telegram && (
                      <span className="text-[#4faeef] font-semibold bg-[#202b36] px-1.5 py-0.5 rounded-md text-[11px]">
                        {c.telegram.startsWith('@') ? c.telegram : `@${c.telegram}`}
                      </span>
                    )}
                  </div>

                  {/* Orders pill */}
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {c.total_orders > 0 ? (
                      <span className="text-[11px] font-semibold text-[#53df83] bg-[#53df83]/15 border border-[#53df83]/30 px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Briefcase size={11} />
                        <span>
                          {c.total_orders} зак. • {c.total_revenue.toLocaleString('ru-RU')} ₽
                          {c.active_deal ? ` • ${c.active_deal.title} (${c.active_deal.status})` : ''}
                        </span>
                      </span>
                    ) : (
                      <span className="text-[11px] text-[#708499] bg-[#0e1621] px-2 py-0.5 rounded-md border border-[#232e3c]">
                        Без активных заказов
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right: Open Chat Button */}
              <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                <div className="hidden sm:flex items-center gap-1 px-3 py-1.5 bg-[#202b36] group-hover:bg-[#3390ec] text-white text-xs font-semibold rounded-xl transition-all shadow-sm">
                  <MessageSquare size={14} />
                  <span>Чат</span>
                </div>
                <ChevronRight size={18} className="sm:hidden text-[#708499] group-hover:text-white" />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
