import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, Send, X, CornerUpLeft, Pencil, FileText, Check } from 'lucide-react';
import { ReplyReference, Message } from '../../types';
import { useTelegram } from '../../hooks/useTelegram';

interface ChatInputProps {
  onSendMessage: (text: string, replyTo?: ReplyReference | null, file?: File | null) => void;
  onSaveEdit?: (message: Message, newText: string) => void;
  onTyping?: () => void;
  replyingTo: ReplyReference | null;
  editingMessage: Message | null;
  onCancelReply: () => void;
  onCancelEdit: () => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onSaveEdit,
  onTyping,
  replyingTo,
  editingMessage,
  onCancelReply,
  onCancelEdit,
  disabled = false,
}) => {
  const [text, setText] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastTypingTimeRef = useRef<number>(0);
  const { triggerHaptic } = useTelegram();

  // Populate text if editing a message
  useEffect(() => {
    if (editingMessage) {
      setText(editingMessage.text || '');
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [editingMessage]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  // Clean up object URL
  useEffect(() => {
    return () => {
      if (filePreviewUrl) {
        URL.revokeObjectURL(filePreviewUrl);
      }
    };
  }, [filePreviewUrl]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);

    // Debounce outbound typing notification (every 3 seconds)
    const now = Date.now();
    if (now - lastTypingTimeRef.current > 3000) {
      lastTypingTimeRef.current = now;
      if (onTyping) {
        onTyping();
      }
    }
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAttachedFile(file);
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setFilePreviewUrl(url);
    } else {
      setFilePreviewUrl(null);
    }

    // Reset input value so same file can be re-selected if needed
    e.target.value = '';
  };

  const handleRemoveAttachment = () => {
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl);
    }
    setAttachedFile(null);
    setFilePreviewUrl(null);
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if ((!trimmed && !attachedFile) || disabled) return;

    triggerHaptic('medium');

    if (editingMessage && onSaveEdit) {
      onSaveEdit(editingMessage, trimmed);
      setText('');
      onCancelEdit();
    } else {
      onSendMessage(trimmed, replyingTo, attachedFile);
      setText('');
      handleRemoveAttachment();
      onCancelReply();
    }

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEditing = !!editingMessage;

  return (
    <div className="flex flex-col bg-[#17212b] border-t border-[#232e3c] w-full relative z-20">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelected}
        className="hidden"
        accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.zip,.txt"
      />

      {/* Editing Banner */}
      {isEditing && (
        <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#17212b] border-b border-[#232e3c]/60 animate-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center gap-2.5 min-w-0">
            <Pencil size={16} className="text-[#4faeef] flex-shrink-0" />
            <div className="flex flex-col border-l-[3px] border-[#4faeef] pl-2 min-w-0">
              <span className="text-xs font-semibold text-[#4faeef] leading-tight">
                Edit message
              </span>
              <span className="text-xs text-[#708499] truncate max-w-sm leading-tight">
                {editingMessage.text}
              </span>
            </div>
          </div>
          <button
            onClick={onCancelEdit}
            className="p-1 text-[#708499] hover:text-white rounded-full hover:bg-[#202b36] transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Reply Preview Bar */}
      {!isEditing && replyingTo && (
        <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#17212b] border-b border-[#232e3c]/60 animate-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center gap-2.5 min-w-0">
            <CornerUpLeft size={16} className="text-[#3390ec] flex-shrink-0" />
            <div className="flex flex-col border-l-[3px] border-[#3390ec] pl-2 min-w-0">
              <span className="text-xs font-semibold text-[#3390ec] leading-tight">
                Reply to {replyingTo.sender_name}
              </span>
              <span className="text-xs text-[#708499] truncate max-w-sm leading-tight">
                {replyingTo.text_preview}
              </span>
            </div>
          </div>
          <button
            onClick={onCancelReply}
            className="p-1 text-[#708499] hover:text-white rounded-full hover:bg-[#202b36] transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Attachment Preview Bar */}
      {attachedFile && (
        <div className="flex items-center justify-between px-3.5 py-2 bg-[#202b36]/60 border-b border-[#232e3c]/40">
          <div className="flex items-center gap-3 min-w-0">
            {filePreviewUrl ? (
              <img
                src={filePreviewUrl}
                alt="Upload preview"
                className="w-10 h-10 object-cover rounded-lg border border-[#232e3c]"
              />
            ) : (
              <div className="w-10 h-10 rounded-lg bg-[#3390ec] flex items-center justify-center text-white">
                <FileText size={20} />
              </div>
            )}
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-white truncate max-w-xs">
                {attachedFile.name}
              </span>
              <span className="text-[11px] text-[#708499]">
                {Math.round(attachedFile.size / 1024)} KB
              </span>
            </div>
          </div>
          <button
            onClick={handleRemoveAttachment}
            className="p-1 text-[#708499] hover:text-[#ff596a] transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main Input Row */}
      <div className="flex items-end gap-2 px-3 py-2">
        {/* Paperclip Attachment Button */}
        {!isEditing && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-[#708499] hover:text-[#3390ec] rounded-full hover:bg-[#202b36] transition-colors flex-shrink-0 mb-0.5"
            title="Attach media or file"
          >
            <Paperclip size={20} />
          </button>
        )}

        {/* Text Area */}
        <div className="flex-1 min-w-0">
          <textarea
            ref={textareaRef}
            rows={1}
            disabled={disabled}
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={isEditing ? 'Edit message...' : 'Write a message...'}
            className="w-full bg-transparent text-white placeholder-[#708499] text-sm py-2 px-1 focus:outline-none resize-none max-h-36 overflow-y-auto leading-relaxed"
          />
        </div>

        {/* Action Button: Send or Save Edit */}
        <button
          type="button"
          onClick={handleSend}
          disabled={(!text.trim() && !attachedFile) || disabled}
          className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 mb-0.5 transition-all shadow-md ${
            (text.trim() || attachedFile) && !disabled
              ? isEditing
                ? 'bg-[#4faeef] text-white hover:bg-[#3390ec] scale-100'
                : 'bg-[#3390ec] text-white hover:bg-[#4faeef] scale-100'
              : 'bg-[#202b36] text-[#708499] opacity-60 scale-95 cursor-not-allowed'
          }`}
          title={isEditing ? 'Save edit' : 'Send'}
        >
          {isEditing ? <Check size={18} /> : <Send size={17} className="ml-0.5" />}
        </button>
      </div>
    </div>
  );
};
