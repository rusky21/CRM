import React from 'react';
import { Search } from 'lucide-react';
import { Dialogue } from '../types';
import { getAvatarGradientClass, getInitials } from '../hooks/useTelegram';

interface DialogueListProps {
  dialogues: Dialogue[];
  selectedDialogue: Dialogue | null;
  onSelectDialogue: (dialogue: Dialogue) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isLoading: boolean;
}

function formatDialogTime(dateStr?: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();

  // If today: format HH:mm
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // If this week: format Mon, Tue, etc.
  const diffDays = Math.round((now.getTime() - date.getTime()) / (1000 * 3600 * 24));
  if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: 'short' });
  }

  // Otherwise format dd.MM
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
}

export const DialogueList: React.FC<DialogueListProps> = ({
  dialogues,
  selectedDialogue,
  onSelectDialogue,
  searchQuery,
  onSearchChange,
  isLoading,
}) => {
  return (
    <div className="flex flex-col h-full bg-[#0e1621] border-r border-[#232e3c]">
      {/* Search Header */}
      <div className="p-2.5 border-b border-[#232e3c]">
        <div className="relative flex items-center">
          <Search size={16} className="absolute left-3 text-[#708499]" />
          <input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-[#17212b] text-white text-sm pl-9 pr-3 py-1.5 rounded-full border border-transparent focus:border-[#3390ec] focus:outline-none placeholder-[#708499] transition-all"
          />
        </div>
      </div>

      {/* Dialogues List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && dialogues.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-[#708499]">
            Loading conversations...
          </div>
        ) : dialogues.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-[#708499] p-4 text-center">
            <span className="text-sm font-medium">No chats found</span>
            <span className="text-xs mt-1">Messages from Telegram accounts will show here.</span>
          </div>
        ) : (
          dialogues.map((dialogue) => {
            const isSelected = selectedDialogue?.peer_id === dialogue.peer_id;
            return (
              <div
                key={dialogue.id}
                onClick={() => onSelectDialogue(dialogue)}
                className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors relative ${
                  isSelected ? 'bg-[#2b5278]' : 'hover:bg-[#17212b]'
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-12 h-12 rounded-full flex-shrink-0 flex items-center justify-center font-bold text-white text-base shadow-sm ${getAvatarGradientClass(
                    dialogue.peer_id
                  )}`}
                >
                  {getInitials(dialogue.peer_name)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-semibold text-sm text-white truncate">
                      {dialogue.peer_name}
                    </span>
                    <span
                      className={`text-[12px] flex-shrink-0 ${
                        isSelected ? 'text-[#e0edfa]' : 'text-[#708499]'
                      }`}
                    >
                      {formatDialogTime(dialogue.last_message_at || dialogue.updated_at)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <p
                      className={`text-xs truncate max-w-[190px] ${
                        isSelected ? 'text-[#c6def5]' : 'text-[#708499]'
                      }`}
                    >
                      {dialogue.last_message_text || 'No messages yet'}
                    </p>

                    {dialogue.unread_count > 0 && (
                      <span className="bg-[#3390ec] text-white text-[11px] font-bold min-w-5 h-5 px-1.5 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ml-1">
                        {dialogue.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
