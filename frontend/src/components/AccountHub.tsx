import React, { useState, useRef } from 'react';
import {
  Search,
  Plus,
  ChevronRight,
  ShieldCheck,
  RefreshCw,
  Smartphone,
  ExternalLink,
  Zap,
  Settings,
  Edit3,
  Lock,
  Upload,
  FileText,
  Check,
  AlertCircle,
  ShieldAlert,
  X,
  Camera,
} from 'lucide-react';
import { Account, ProfileUpdatePayload } from '../types';
import { getAvatarGradientClass, getInitials, useTelegram } from '../hooks/useTelegram';
import {
  updateAccountAlias,
  updateTelegramProfile,
  uploadAccountAvatar,
  terminateOtherSessions,
  importSessionFile,
} from '../services/api';

interface AccountHubProps {
  accounts: Account[];
  onSelectAccount: (account: Account) => void;
  onReconnect: (accountId: string) => void;
  onRefreshAccounts?: () => void;
}

export const AccountHub: React.FC<AccountHubProps> = ({
  accounts,
  onSelectAccount,
  onReconnect,
  onRefreshAccounts,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const { triggerHaptic } = useTelegram();

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addModalTab, setAddModalTab] = useState<'phone' | 'file'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importCustomTitle, setImportCustomTitle] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Rename alias modal
  const [renamingAccount, setRenamingAccount] = useState<Account | null>(null);
  const [aliasInput, setAliasInput] = useState('');
  const [isSavingAlias, setIsSavingAlias] = useState(false);

  // Profile Studio modal
  const [studioAccount, setStudioAccount] = useState<Account | null>(null);
  const [studioFirstName, setStudioFirstName] = useState('');
  const [studioLastName, setStudioLastName] = useState('');
  const [studioAbout, setStudioAbout] = useState('');
  const [studioUsername, setStudioUsername] = useState('');
  const [studioAvatarFile, setStudioAvatarFile] = useState<File | null>(null);
  const [studioAvatarPreview, setStudioAvatarPreview] = useState<string | null>(null);
  const [isSavingStudio, setIsSavingStudio] = useState(false);
  const [studioSuccess, setStudioSuccess] = useState(false);
  const [isTerminatingSessions, setIsTerminatingSessions] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  // Sort accounts: unread messages first, then active, then banned at bottom, then alphabetical
  const sortedAccounts = [...accounts].sort((a, b) => {
    if (a.status === 'BANNED' && b.status !== 'BANNED') return 1;
    if (b.status === 'BANNED' && a.status !== 'BANNED') return -1;
    if (b.total_unread_dialogues !== a.total_unread_dialogues) {
      return b.total_unread_dialogues - a.total_unread_dialogues;
    }
    if (a.is_connected !== b.is_connected) {
      return a.is_connected ? -1 : 1;
    }
    const nameA = a.custom_title || a.title;
    const nameB = b.custom_title || b.title;
    return nameA.localeCompare(nameB);
  });

  const filteredAccounts = sortedAccounts.filter((acc) => {
    const q = searchQuery.toLowerCase();
    return (
      acc.title.toLowerCase().includes(q) ||
      (acc.custom_title && acc.custom_title.toLowerCase().includes(q)) ||
      acc.phone.includes(q) ||
      (acc.username && acc.username.toLowerCase().includes(q))
    );
  });

  const totalUnreadAcrossAll = accounts.reduce(
    (sum, acc) => sum + (acc.total_unread_dialogues || 0),
    0
  );

  const handleCardClick = (acc: Account) => {
    triggerHaptic('medium');
    onSelectAccount(acc);
  };

  const handleReconnectClick = (e: React.MouseEvent, accId: string) => {
    e.stopPropagation();
    triggerHaptic('light');
    onReconnect(accId);
  };

  // Open rename modal
  const openRenameModal = (e: React.MouseEvent, acc: Account) => {
    e.stopPropagation();
    setRenamingAccount(acc);
    setAliasInput(acc.custom_title || acc.title);
  };

  const handleSaveAlias = async () => {
    if (!renamingAccount || !aliasInput.trim()) return;
    setIsSavingAlias(true);
    try {
      await updateAccountAlias(renamingAccount.id, aliasInput.trim());
      triggerHaptic('notification');
      setRenamingAccount(null);
      if (onRefreshAccounts) onRefreshAccounts();
    } catch (err: any) {
      alert(err.message || 'Failed to update alias');
    } finally {
      setIsSavingAlias(false);
    }
  };

  // Open Profile Studio
  const openProfileStudio = (e: React.MouseEvent, acc: Account) => {
    e.stopPropagation();
    setStudioAccount(acc);
    setStudioFirstName(acc.first_name || '');
    setStudioLastName(acc.last_name || '');
    setStudioAbout(acc.about || '');
    setStudioUsername(acc.username ? `@${acc.username}` : '');
    setStudioAvatarFile(null);
    setStudioAvatarPreview(null);
    setStudioSuccess(false);
  };

  const handleSaveStudio = async () => {
    if (!studioAccount) return;
    setIsSavingStudio(true);
    try {
      const payload: ProfileUpdatePayload = {
        first_name: studioFirstName.trim(),
        last_name: studioLastName.trim(),
        about: studioAbout.trim(),
        username: studioUsername.replace('@', '').trim(),
      };
      await updateTelegramProfile(studioAccount.id, payload);

      if (studioAvatarFile) {
        await uploadAccountAvatar(studioAccount.id, studioAvatarFile);
      }

      setStudioSuccess(true);
      triggerHaptic('notification');
      setTimeout(() => {
        setStudioAccount(null);
        if (onRefreshAccounts) onRefreshAccounts();
      }, 1200);
    } catch (err: any) {
      alert(err.message || 'Failed to save profile changes');
    } finally {
      setIsSavingStudio(false);
    }
  };

  const handleTerminateOtherSessions = async () => {
    if (!studioAccount) return;
    const confirmed = window.confirm(
      'Вы уверены, что хотите завершить все другие сеансы Telegram для этого аккаунта? Все остальные подключенные устройства будут отключены.'
    );
    if (!confirmed) return;

    setIsTerminatingSessions(true);
    try {
      await terminateOtherSessions(studioAccount.id);
      triggerHaptic('notification');
      alert('Все остальные сеансы Telegram успешно завершены.');
    } catch (err: any) {
      alert(err.message || 'Не удалось завершить сеансы');
    } finally {
      setIsTerminatingSessions(false);
    }
  };

  // File import handler
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleImportSubmit = async () => {
    if (!selectedFile) return;
    setIsImporting(true);
    setImportError(null);
    try {
      await importSessionFile(selectedFile, importCustomTitle.trim() || undefined);
      triggerHaptic('notification');
      setIsAddModalOpen(false);
      setSelectedFile(null);
      setImportCustomTitle('');
      if (onRefreshAccounts) onRefreshAccounts();
    } catch (err: any) {
      setImportError(err.message || 'Ошибка при импорте файла сессии.');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#0e1621] text-white overflow-hidden select-none">
      {/* Top Header */}
      <div className="px-4 pt-5 pb-3 bg-[#17212b] border-b border-[#232e3c] flex flex-col gap-3.5 z-10 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white">
              My Telegram Accounts
            </h1>
            <span className="bg-[#202b36] border border-[#232e3c] text-[#708499] text-xs font-semibold px-2 py-0.5 rounded-full">
              {accounts.length}
            </span>
            {totalUnreadAcrossAll > 0 && (
              <span className="bg-[#3390ec] text-white text-xs font-bold px-2 py-0.5 rounded-full shadow-sm animate-pulse">
                {totalUnreadAcrossAll} new
              </span>
            )}
          </div>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#3390ec] hover:bg-[#4faeef] text-white text-xs font-semibold rounded-lg shadow transition-all active:scale-95"
          >
            <Plus size={16} />
            <span>Add Account</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search size={16} className="absolute left-3.5 top-2.5 text-[#708499]" />
          <input
            type="text"
            placeholder="Search by alias, title, phone or @username..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0e1621] text-sm text-white placeholder-[#708499] pl-9 pr-3.5 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none transition-colors"
          />
        </div>
      </div>

      {/* Account Cards Feed */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-3">
        {filteredAccounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center text-[#708499]">
            <Smartphone size={40} className="mb-2 opacity-50 text-[#3390ec]" />
            <p className="text-sm font-semibold text-white">No Telegram Accounts Found</p>
            <p className="text-xs mt-1 max-w-xs">
              {searchQuery
                ? 'No accounts match your search query.'
                : 'Connect your first Telegram account to begin managing customer dialogues.'}
            </p>
          </div>
        ) : (
          filteredAccounts.map((acc) => {
            const isBanned = acc.status === 'BANNED';
            const isFloodWait = acc.status === 'FLOOD_WAIT';
            const displayTitle = acc.custom_title || acc.title;

            return (
              <div
                key={acc.id}
                onClick={() => handleCardClick(acc)}
                className={`relative flex items-center justify-between p-3.5 md:p-4 rounded-2xl border transition-all cursor-pointer group shadow-sm ${
                  isBanned
                    ? 'bg-[#17212b]/60 border-[#e572a6]/40 hover:border-[#e572a6]'
                    : acc.total_unread_dialogues > 0
                    ? 'bg-[#17212b] border-[#3390ec]/60 hover:border-[#3390ec]'
                    : 'bg-[#17212b]/80 border-[#232e3c] hover:bg-[#17212b] hover:border-[#708499]/40'
                }`}
              >
                {/* Left: Avatar + Details */}
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="relative flex-shrink-0">
                    <div
                      className={`w-12 h-12 md:w-14 md:h-14 rounded-2xl flex items-center justify-center font-bold text-white text-base md:text-lg shadow-md ${getAvatarGradientClass(
                        acc.id
                      )}`}
                    >
                      {getInitials(displayTitle)}
                    </div>
                    {/* Status Dot */}
                    <span
                      className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-[#17212b] ${
                        isBanned
                          ? 'bg-[#ff596a]'
                          : acc.is_connected
                          ? 'bg-[#53df83]'
                          : isFloodWait
                          ? 'bg-[#ffcd6a]'
                          : 'bg-[#708499]'
                      }`}
                    />
                  </div>

                  <div className="flex flex-col min-w-0">
                    {/* Title & Alias */}
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm md:text-base text-white truncate group-hover:text-[#4faeef] transition-colors">
                        {displayTitle}
                      </span>
                      {acc.custom_title && (
                        <span className="text-xs text-[#708499] hidden sm:inline">
                          ({acc.title})
                        </span>
                      )}
                      <button
                        title="Переименовать Alias"
                        onClick={(e) => openRenameModal(e, acc)}
                        className="p-1 text-[#708499] hover:text-[#4faeef] rounded-md transition-colors opacity-70 group-hover:opacity-100"
                      >
                        <Edit3 size={13} />
                      </button>
                    </div>

                    <span className="text-xs text-[#708499] font-medium tracking-wide">
                      {acc.phone} {acc.username ? `• @${acc.username}` : ''}
                    </span>

                    {/* Meta Tags */}
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      {isBanned ? (
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#ff596a] bg-[#ff596a]/15 border border-[#ff596a]/30 px-2 py-0.5 rounded-md">
                          <Lock size={12} />
                          <span>Заблокирован (Архив)</span>
                        </div>
                      ) : acc.proxy ? (
                        <div className="flex items-center gap-1 text-[11px] text-[#708499] bg-[#0e1621] px-2 py-0.5 rounded-md border border-[#232e3c]">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#53df83]" />
                          <span>
                            {acc.proxy.protocol.toUpperCase()} • {acc.proxy.host}:{acc.proxy.port}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-[11px] text-[#708499] bg-[#0e1621] px-2 py-0.5 rounded-md border border-[#232e3c]">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#53df83]" />
                          <span>Direct Connection</span>
                        </div>
                      )}

                      {acc.device_model && (
                        <span className="text-[11px] text-[#708499] bg-[#0e1621] px-2 py-0.5 rounded-md border border-[#232e3c]">
                          {acc.device_model}
                        </span>
                      )}

                      {isFloodWait && (
                        <span className="text-[11px] text-[#ffcd6a] bg-[#ffcd6a]/15 px-2 py-0.5 rounded-md font-semibold">
                          Cooldown
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2.5 flex-shrink-0 ml-3">
                  {acc.total_unread_dialogues > 0 ? (
                    <span className="bg-[#3390ec] text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-md animate-in zoom-in-75 duration-150">
                      {acc.total_unread_dialogues} unread
                    </span>
                  ) : null}

                  {/* Profile Studio Button */}
                  <button
                    title="Profile Studio (Редактировать профиль MTProto)"
                    onClick={(e) => openProfileStudio(e, acc)}
                    className="p-2 bg-[#202b36] hover:bg-[#3390ec] text-[#708499] hover:text-white rounded-xl transition-all border border-[#232e3c]"
                  >
                    <Settings size={15} />
                  </button>

                  {!acc.is_connected && !isBanned && (
                    <button
                      title="Reconnect Session"
                      onClick={(e) => handleReconnectClick(e, acc.id)}
                      className="p-2 bg-[#202b36] hover:bg-[#2b5278] text-[#4faeef] rounded-xl transition-colors border border-[#232e3c]"
                    >
                      <RefreshCw size={15} />
                    </button>
                  )}

                  <div className="hidden sm:flex items-center gap-1 px-3 py-1.5 bg-[#202b36] group-hover:bg-[#3390ec] text-white text-xs font-semibold rounded-xl transition-all">
                    <span>{isBanned ? 'Archive' : 'Open'}</span>
                    <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                  </div>

                  <ChevronRight size={18} className="sm:hidden text-[#708499] group-hover:text-white" />
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* MODAL 1: Add Account with File Import Tab */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#17212b] border border-[#232e3c] rounded-2xl p-5 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[#232e3c]">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus size={18} className="text-[#3390ec]" />
                <span>Подключение Telegram Аккаунта</span>
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 text-[#708499] hover:text-white rounded-lg"
              >
                <X size={18} />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 mt-4 p-1 bg-[#0e1621] rounded-xl border border-[#232e3c]">
              <button
                onClick={() => setAddModalTab('file')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                  addModalTab === 'file'
                    ? 'bg-[#3390ec] text-white shadow'
                    : 'text-[#708499] hover:text-white'
                }`}
              >
                <FileText size={14} />
                <span>📁 Файл (.session / .txt)</span>
              </button>
              <button
                onClick={() => setAddModalTab('phone')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                  addModalTab === 'phone'
                    ? 'bg-[#3390ec] text-white shadow'
                    : 'text-[#708499] hover:text-white'
                }`}
              >
                <Smartphone size={14} />
                <span>📱 По номеру</span>
              </button>
            </div>

            {addModalTab === 'file' ? (
              <div className="mt-4 space-y-4">
                {/* Drag and drop zone */}
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-[#232e3c] hover:border-[#3390ec] rounded-2xl p-6 text-center cursor-pointer transition-colors bg-[#0e1621]/40 flex flex-col items-center justify-center gap-2"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".session,.txt"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                      }
                    }}
                  />
                  <Upload size={32} className="text-[#3390ec] mb-1" />
                  <span className="text-sm font-semibold text-white">
                    {selectedFile ? selectedFile.name : 'Перетащите сюда .session или .txt файл'}
                  </span>
                  <span className="text-xs text-[#708499]">
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB • Нажмите для замены`
                      : 'Поддерживаются бинарные SQLite Telethon .session и строковые StringSession'}
                  </span>
                </div>

                <div>
                  <label className="text-xs text-[#708499] block mb-1.5 font-medium">
                    Имя / Alias аккаунта (необязательно)
                  </label>
                  <input
                    type="text"
                    placeholder="Например: Отдел Продаж 1"
                    value={importCustomTitle}
                    onChange={(e) => setImportCustomTitle(e.target.value)}
                    className="w-full bg-[#0e1621] text-sm text-white px-3.5 py-2.5 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                  />
                </div>

                {importError && (
                  <div className="p-3 bg-[#ff596a]/15 border border-[#ff596a]/30 rounded-xl text-xs text-[#ff596a] flex items-center gap-2">
                    <AlertCircle size={15} className="flex-shrink-0" />
                    <span>{importError}</span>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setIsAddModalOpen(false)}
                    className="px-4 py-2 text-xs font-semibold text-[#708499] hover:text-white rounded-xl"
                  >
                    Отмена
                  </button>
                  <button
                    disabled={!selectedFile || isImporting}
                    onClick={handleImportSubmit}
                    className="px-5 py-2 text-xs font-semibold bg-[#3390ec] hover:bg-[#4faeef] disabled:opacity-50 text-white rounded-xl shadow transition-all active:scale-95"
                  >
                    {isImporting ? 'Импортирование...' : 'Импортировать сессию'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-4 p-4 text-center text-xs text-[#708499] space-y-3">
                <p>Для интерактивного входа по коду и 2FA используйте терминальный помощник:</p>
                <code className="block bg-[#0e1621] p-3 rounded-xl text-white font-mono text-[11px] border border-[#232e3c]">
                  python -m scripts.cli_login
                </code>
                <p>Сессия будет автоматически зашифрована AES-256-GCM и появится в этом списке.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 2: Rename Alias */}
      {renamingAccount && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#17212b] border border-[#232e3c] rounded-2xl p-5 max-w-sm w-full shadow-2xl animate-in zoom-in-95 duration-150">
            <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
              <Edit3 size={18} className="text-[#3390ec]" />
              <span>Изменить Alias аккаунта</span>
            </h3>
            <p className="text-xs text-[#708499] mb-4">
              Внутреннее название для операторов (не влияет на имя в Telegram).
            </p>
            <input
              type="text"
              value={aliasInput}
              onChange={(e) => setAliasInput(e.target.value)}
              placeholder="Например: Менеджер Вася"
              className="w-full bg-[#0e1621] text-sm text-white px-3.5 py-2.5 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none mb-4"
              autoFocus
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setRenamingAccount(null)}
                className="px-4 py-2 text-xs font-semibold text-[#708499] hover:text-white"
              >
                Отмена
              </button>
              <button
                disabled={isSavingAlias || !aliasInput.trim()}
                onClick={handleSaveAlias}
                className="px-5 py-2 text-xs font-semibold bg-[#3390ec] hover:bg-[#4faeef] text-white rounded-xl shadow"
              >
                {isSavingAlias ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Profile Studio (MTProto Account Settings) */}
      {studioAccount && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#17212b] border border-[#232e3c] rounded-2xl p-5 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-150 my-6">
            <div className="flex items-center justify-between pb-3 border-b border-[#232e3c]">
              <div className="flex items-center gap-2">
                <Settings size={18} className="text-[#3390ec]" />
                <h3 className="text-base font-bold text-white">Profile Studio</h3>
              </div>
              <button
                onClick={() => setStudioAccount(null)}
                className="p-1 text-[#708499] hover:text-white rounded-lg"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {/* Avatar section */}
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div
                    className={`w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-xl overflow-hidden shadow ${getAvatarGradientClass(
                      studioAccount.id
                    )}`}
                  >
                    {studioAvatarPreview ? (
                      <img src={studioAvatarPreview} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                      getInitials(studioFirstName || studioAccount.title)
                    )}
                  </div>
                  <button
                    onClick={() => avatarInputRef.current?.click()}
                    className="absolute -bottom-1 -right-1 p-1.5 bg-[#3390ec] text-white rounded-full shadow hover:bg-[#4faeef]"
                  >
                    <Camera size={14} />
                  </button>
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        const file = e.target.files[0];
                        setStudioAvatarFile(file);
                        setStudioAvatarPreview(URL.createObjectURL(file));
                      }
                    }}
                  />
                </div>
                <div>
                  <span className="text-sm font-bold text-white block">Фото профиля</span>
                  <span className="text-xs text-[#708499]">
                    {studioAvatarFile ? studioAvatarFile.name : 'Нажмите на камеру для загрузки'}
                  </span>
                </div>
              </div>

              {/* Names */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#708499] block mb-1 font-medium">Имя (First Name)</label>
                  <input
                    type="text"
                    value={studioFirstName}
                    onChange={(e) => setStudioFirstName(e.target.value)}
                    className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-[#708499] block mb-1 font-medium">Фамилия (Last Name)</label>
                  <input
                    type="text"
                    value={studioLastName}
                    onChange={(e) => setStudioLastName(e.target.value)}
                    className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                  />
                </div>
              </div>

              {/* Bio with counter */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-[#708499] font-medium">О себе (Bio)</label>
                  <span className={`text-[11px] ${studioAbout.length > 70 ? 'text-[#ff596a]' : 'text-[#708499]'}`}>
                    {studioAbout.length}/70
                  </span>
                </div>
                <textarea
                  rows={2}
                  maxLength={70}
                  value={studioAbout}
                  onChange={(e) => setStudioAbout(e.target.value)}
                  placeholder="Короткое описание профиля..."
                  className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none resize-none"
                />
              </div>

              {/* Username */}
              <div>
                <label className="text-xs text-[#708499] block mb-1 font-medium">Юзернейм (@username)</label>
                <input
                  type="text"
                  value={studioUsername}
                  onChange={(e) => setStudioUsername(e.target.value)}
                  placeholder="@my_account"
                  className="w-full bg-[#0e1621] text-sm text-white px-3 py-2 rounded-xl border border-[#232e3c] focus:border-[#3390ec] focus:outline-none"
                />
              </div>

              {/* Danger Zone: Security */}
              <div className="pt-3 border-t border-[#232e3c]">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-white block">Безопасность сессий</span>
                    <span className="text-[11px] text-[#708499]">Завершить все остальные сеансы Telegram</span>
                  </div>
                  <button
                    disabled={isTerminatingSessions}
                    onClick={handleTerminateOtherSessions}
                    className="px-3 py-1.5 bg-[#ff596a]/15 hover:bg-[#ff596a]/25 text-[#ff596a] text-xs font-semibold rounded-xl border border-[#ff596a]/30 transition-colors"
                  >
                    {isTerminatingSessions ? 'Сброс...' : 'Завершить другие'}
                  </button>
                </div>
              </div>

              {studioSuccess && (
                <div className="p-3 bg-[#53df83]/15 border border-[#53df83]/30 rounded-xl text-xs text-[#53df83] flex items-center gap-2">
                  <Check size={16} />
                  <span>Профиль Telegram успешно обновлен в облаке MTProto!</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setStudioAccount(null)}
                  className="px-4 py-2 text-xs font-semibold text-[#708499] hover:text-white rounded-xl"
                >
                  Отмена
                </button>
                <button
                  disabled={isSavingStudio}
                  onClick={handleSaveStudio}
                  className="px-5 py-2 text-xs font-semibold bg-[#3390ec] hover:bg-[#4faeef] text-white rounded-xl shadow transition-all active:scale-95"
                >
                  {isSavingStudio ? 'Синхронизация...' : 'Сохранить изменения'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
