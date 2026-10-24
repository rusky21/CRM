import React, { useState } from 'react';
import { ChevronDown, Check, RefreshCw, Smartphone, ShieldCheck, AlertCircle } from 'lucide-react';
import { Account } from '../types';
import { getAvatarGradientClass, getInitials, useTelegram } from '../hooks/useTelegram';

interface AccountSwitcherProps {
  accounts: Account[];
  activeAccount: Account | null;
  onSelectAccount: (account: Account) => void;
  onReconnect: (accountId: string) => void;
}

export const AccountSwitcher: React.FC<AccountSwitcherProps> = ({
  accounts,
  activeAccount,
  onSelectAccount,
  onReconnect,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const { triggerHaptic } = useTelegram();

  const handleSelect = (acc: Account) => {
    triggerHaptic('light');
    onSelectAccount(acc);
    setIsOpen(false);
  };

  const handleReconnectClick = (e: React.MouseEvent, accId: string) => {
    e.stopPropagation();
    triggerHaptic('medium');
    onReconnect(accId);
  };

  return (
    <div className="relative select-none">
      {/* Trigger Bar in Header */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer hover:bg-[#202b36] transition-colors"
      >
        {activeAccount ? (
          <>
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-white text-xs shadow-sm ${getAvatarGradientClass(
                activeAccount.id
              )}`}
            >
              {getInitials(activeAccount.title)}
            </div>
            <div className="flex flex-col text-left">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-sm text-white leading-tight">
                  {activeAccount.title}
                </span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    activeAccount.is_connected ? 'bg-[#53df83]' : 'bg-[#e572a6]'
                  }`}
                  title={activeAccount.status}
                />
              </div>
              <span className="text-[12px] text-[#708499] leading-tight">
                {activeAccount.phone}
              </span>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-sm text-[#708499]">
            <span>Select Account</span>
          </div>
        )}
        <ChevronDown
          size={16}
          className={`text-[#708499] ml-1 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </div>

      {/* Telegram-style Dropdown Menu */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute left-0 mt-2 w-72 bg-[#17212b] border border-[#232e3c] rounded-xl shadow-2xl z-50 overflow-hidden py-1.5 animate-in fade-in zoom-in-95 duration-100">
            <div className="px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#708499]">
              Connected Telegram Sessions ({accounts.length})
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-[#232e3c]/40">
              {accounts.map((acc) => {
                const isActive = activeAccount?.id === acc.id;
                return (
                  <div
                    key={acc.id}
                    onClick={() => handleSelect(acc)}
                    className={`flex items-center justify-between px-3.5 py-2.5 cursor-pointer transition-colors ${
                      isActive ? 'bg-[#202b36]' : 'hover:bg-[#202b36]/60'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center font-bold text-white text-xs ${getAvatarGradientClass(
                          acc.id
                        )}`}
                      >
                        {getInitials(acc.title)}
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-sm font-medium text-white truncate">
                          {acc.title}
                        </span>
                        <div className="flex items-center gap-1.5 text-[11px] text-[#708499]">
                          <span>{acc.phone}</span>
                          {acc.device_model && (
                            <>
                              <span>•</span>
                              <span className="truncate max-w-[90px]">
                                {acc.device_model}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {acc.total_unread_dialogues > 0 && (
                        <span className="bg-[#3390ec] text-white text-[11px] font-bold px-1.5 py-0.5 rounded-full">
                          {acc.total_unread_dialogues}
                        </span>
                      )}

                      {!acc.is_connected && (
                        <button
                          title="Reconnect Account"
                          onClick={(e) => handleReconnectClick(e, acc.id)}
                          className="p-1 hover:bg-[#2b5278] rounded text-[#4faeef] transition-colors"
                        >
                          <RefreshCw size={14} />
                        </button>
                      )}

                      {isActive && <Check size={16} className="text-[#3390ec]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
