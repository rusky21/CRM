import React, { useState } from 'react';
import {
  Check,
  CheckCheck,
  FileText,
  Play,
  Pause,
  CornerUpLeft,
  Copy,
  Pencil,
  Trash2,
  Download,
} from 'lucide-react';
import { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  isFirstInGroup?: boolean;
  isLastInGroup?: boolean;
  onReply: (message: Message) => void;
  onEdit?: (message: Message) => void;
  onDelete?: (message: Message) => void;
  onZoomPhoto?: (url: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isLastInGroup = true,
  onReply,
  onEdit,
  onDelete,
  onZoomPhoto,
}) => {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const isOutgoing = message.is_outgoing;
  const timeFormatted = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const handleCopy = () => {
    if (message.text) {
      navigator.clipboard.writeText(message.text);
    }
    setContextMenu(null);
  };

  const handleReplyClick = () => {
    onReply(message);
    setContextMenu(null);
  };

  const handleEditClick = () => {
    if (onEdit) {
      onEdit(message);
    }
    setContextMenu(null);
  };

  const handleDeleteClick = () => {
    if (onDelete) {
      onDelete(message);
    }
    setContextMenu(null);
  };

  const photoUrl = message.media_url || message.media?.url;
  const filename = message.media_filename || message.media?.filename || 'Document.bin';
  const fileSize = message.media_size || message.media?.size_bytes;

  return (
    <div
      className={`flex w-full mb-1 group relative ${isOutgoing ? 'justify-end' : 'justify-start'}`}
      onContextMenu={handleContextMenu}
    >
      <div
        className={`relative max-w-[85%] md:max-w-[70%] px-3 py-2 text-sm text-white select-text shadow-sm ${
          isOutgoing
            ? 'bg-[#2b5278] rounded-[16px] rounded-br-[4px]'
            : 'bg-[#182533] rounded-[16px] rounded-bl-[4px]'
        }`}
      >
        {/* Authentic Telegram Tail on last message in contiguous group */}
        {isLastInGroup && (
          <div className={isOutgoing ? 'bubble-tail-out' : 'bubble-tail-in'} />
        )}

        {/* Quoted Reply Block */}
        {message.reply_to && (
          <div className="flex items-center gap-2 mb-1.5 pl-2 py-0.5 border-l-[3px] border-[#4faeef] bg-black/15 rounded-r cursor-pointer hover:bg-black/25 transition-colors">
            <div className="flex flex-col text-xs min-w-0">
              <span className="font-semibold text-[#4faeef] leading-tight">
                {message.reply_to.sender_name}
              </span>
              <span className="text-[#c6def5] truncate max-w-[240px] leading-tight">
                {message.reply_to.text_preview}
              </span>
            </div>
          </div>
        )}

        {/* Media: Photo Preview */}
        {message.media_type === 'photo' && (
          <div className="mb-1 rounded-lg overflow-hidden bg-black/20 max-w-[320px] cursor-pointer">
            {photoUrl ? (
              <img
                src={photoUrl}
                alt="Attachment"
                onClick={() => onZoomPhoto && onZoomPhoto(photoUrl)}
                className="w-full h-auto object-cover rounded-lg hover:opacity-95 transition-opacity"
              />
            ) : (
              <div className="p-4 text-center text-xs text-[#708499]">
                [Telegram Photo]
              </div>
            )}
          </div>
        )}

        {/* Media: Document File */}
        {message.media_type === 'document' && (
          <div className="flex items-center gap-3 p-2 bg-black/20 rounded-lg mb-1">
            <div className="w-10 h-10 rounded-full bg-[#3390ec] flex items-center justify-center text-white flex-shrink-0">
              <FileText size={20} />
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-semibold truncate max-w-[180px]">
                {filename}
              </span>
              <span className="text-[11px] text-[#708499]">
                {fileSize ? `${Math.round(fileSize / 1024)} KB` : 'Document'}
              </span>
            </div>
            {message.media_url && (
              <a
                href={message.media_url}
                download={filename}
                className="p-1.5 text-[#708499] hover:text-[#4faeef] rounded-full hover:bg-white/10 transition-colors"
                title="Download"
              >
                <Download size={16} />
              </a>
            )}
          </div>
        )}

        {/* Media: Voice Note */}
        {message.media_type === 'voice' && (
          <div className="flex items-center gap-2.5 p-1 mb-1">
            <button
              onClick={() => setIsPlayingAudio(!isPlayingAudio)}
              className="w-9 h-9 rounded-full bg-[#3390ec] text-white flex items-center justify-center flex-shrink-0 shadow hover:bg-[#4faeef] transition-colors"
            >
              {isPlayingAudio ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
            </button>
            <div className="flex flex-col flex-1 min-w-[120px]">
              <div className="flex items-center gap-0.5 h-4">
                {[4, 8, 14, 10, 6, 12, 16, 8, 4, 10, 14, 8].map((h, i) => (
                  <div
                    key={i}
                    className="w-1 bg-[#4faeef]/70 rounded-full"
                    style={{ height: `${h}px` }}
                  />
                ))}
              </div>
              <span className="text-[11px] text-[#74a7d6] mt-0.5">
                {message.media?.duration_seconds ? `0:${message.media.duration_seconds}` : 'Voice note'}
              </span>
            </div>
          </div>
        )}

        {/* Text Content */}
        {message.text && (
          <div className="whitespace-pre-wrap break-words leading-relaxed text-[14.5px]">
            {message.text}
          </div>
        )}

        {/* Floating Meta / Timestamp / Status / Edited badge */}
        <div className="flex items-center justify-end gap-1 mt-0.5 float-right ml-2 select-none">
          {message.is_edited && (
            <span
              className={`text-[10px] italic mr-0.5 ${
                isOutgoing ? 'text-[#74a7d6]' : 'text-[#708499]'
              }`}
            >
              edited
            </span>
          )}

          <span
            className={`text-[11px] ${
              isOutgoing ? 'text-[#74a7d6]' : 'text-[#708499]'
            }`}
          >
            {timeFormatted}
          </span>

          {isOutgoing && (
            <span className="text-[#6eb9f7]">
              {message.status === 'DELIVERED' || message.status === 'READ' ? (
                <CheckCheck size={14} className="stroke-[2.5]" />
              ) : (
                <Check size={14} className="stroke-[2.5]" />
              )}
            </span>
          )}
        </div>
      </div>

      {/* Telegram-style Context Menu */}
      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setContextMenu(null)}
          />
          <div
            className="fixed z-50 bg-[#17212b] border border-[#232e3c] rounded-xl shadow-2xl py-1 w-44 text-sm text-white animate-in fade-in zoom-in-95 duration-100"
            style={{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }}
          >
            <button
              onClick={handleReplyClick}
              className="flex items-center gap-2.5 w-full px-3.5 py-1.5 hover:bg-[#202b36] text-left transition-colors"
            >
              <CornerUpLeft size={16} className="text-[#3390ec]" />
              <span>Reply</span>
            </button>

            {isOutgoing && (
              <button
                onClick={handleEditClick}
                className="flex items-center gap-2.5 w-full px-3.5 py-1.5 hover:bg-[#202b36] text-left transition-colors"
              >
                <Pencil size={16} className="text-[#4faeef]" />
                <span>Edit</span>
              </button>
            )}

            <button
              onClick={handleCopy}
              className="flex items-center gap-2.5 w-full px-3.5 py-1.5 hover:bg-[#202b36] text-left transition-colors"
            >
              <Copy size={16} className="text-[#708499]" />
              <span>Copy Text</span>
            </button>

            <div className="my-1 border-t border-[#232e3c]" />

            <button
              onClick={handleDeleteClick}
              className="flex items-center gap-2.5 w-full px-3.5 py-1.5 hover:bg-[#202b36] text-left transition-colors text-[#ff596a]"
            >
              <Trash2 size={16} />
              <span>Delete for everyone</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
};
