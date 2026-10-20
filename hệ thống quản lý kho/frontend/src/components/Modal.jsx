import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export const Modal = ({ isOpen, onClose, title, children, maxWidth = 'max-w-2xl' }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/65 backdrop-blur-xs animate-in fade-in duration-fast">
      <div
        className={`bg-[var(--bg-surface)] rounded-modal shadow-modal border border-[var(--border-strong)] w-full ${maxWidth} max-h-[92vh] flex flex-col overflow-hidden transform transition-all text-[var(--text-primary)]`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-2 px-4 sm:px-6 py-3.5 sm:py-4 border-b border-[var(--border-medium)] bg-[var(--bg-surface-warm)]">
          <h3 className="font-serif text-sm sm:text-base font-bold text-[var(--text-primary)] tracking-tight truncate">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] p-1.5 rounded-btn transition-colors cursor-pointer shrink-0"
            title="Đóng hộp thoại"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 overflow-y-auto overflow-x-hidden bg-[var(--bg-surface)] text-[var(--text-primary)]">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;
