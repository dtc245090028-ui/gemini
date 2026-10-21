import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, X } from 'lucide-react';

const ConfirmContext = createContext(null);

export const ConfirmProvider = ({ children }) => {
  const [dialogState, setDialogState] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmText: 'Xác nhận',
    cancelText: 'Giữ lại',
    variant: 'danger', // 'danger' | 'warning' | 'primary'
    showReasonInput: false,
    requireReason: false,
    reasonPlaceholder: '',
  });

  const [reasonValue, setReasonValue] = useState('');
  const [reasonError, setReasonError] = useState('');
  const resolverRef = useRef(null);
  const textareaRef = useRef(null);

  const confirm = useCallback((options) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setReasonValue('');
      setReasonError('');
      setDialogState({
        isOpen: true,
        title: options.title || 'Xác nhận thao tác',
        message: options.message || '',
        confirmText: options.confirmText || 'Xác nhận',
        cancelText: options.cancelText || 'Giữ lại',
        variant: options.variant || 'danger',
        showReasonInput: !!options.showReasonInput,
        requireReason: !!options.requireReason,
        reasonPlaceholder: options.reasonPlaceholder || 'Nhập lý do thực hiện thao tác này...',
      });
    });
  }, []);

  const handleCancel = useCallback(() => {
    setDialogState((prev) => ({ ...prev, isOpen: false }));
    if (resolverRef.current) {
      resolverRef.current({ confirmed: false, reason: '' });
      resolverRef.current = null;
    }
  }, []);

  const handleConfirm = useCallback(() => {
    if (dialogState.showReasonInput && dialogState.requireReason && !reasonValue.trim()) {
      setReasonError('Vui lòng nhập lý do để tiếp tục');
      textareaRef.current?.focus();
      return;
    }

    setDialogState((prev) => ({ ...prev, isOpen: false }));
    if (resolverRef.current) {
      resolverRef.current({ confirmed: true, reason: reasonValue.trim() });
      resolverRef.current = null;
    }
  }, [dialogState.showReasonInput, dialogState.requireReason, reasonValue]);

  // Phím tắt: Escape để hủy, Ctrl+Enter để xác nhận khi đang focus textarea
  useEffect(() => {
    if (!dialogState.isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        handleCancel();
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !dialogState.showReasonInput)) {
        if (!dialogState.showReasonInput || e.ctrlKey || e.metaKey) {
          e.preventDefault();
          handleConfirm();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dialogState.isOpen, dialogState.showReasonInput, handleCancel, handleConfirm]);

  // Tự động focus vào textarea nếu có ô nhập lý do
  useEffect(() => {
    if (dialogState.isOpen && dialogState.showReasonInput) {
      const timer = setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [dialogState.isOpen, dialogState.showReasonInput]);

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}

      {/* Modal Hộp thoại xác nhận tùy chỉnh */}
      {dialogState.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop làm mờ phông nền */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-200"
            onClick={handleCancel}
          />

          {/* Khung Card Hộp thoại chuẩn Theme & Dark Mode */}
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-modal-title"
            className="relative w-full max-w-md bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded-card shadow-2xl p-6 overflow-hidden z-10 space-y-4 animate-in fade-in zoom-in-95 duration-150"
          >
            {/* Header: Icon nhận diện và Tiêu đề */}
            <div className="flex items-start gap-3.5">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-xs ${
                  dialogState.variant === 'danger'
                    ? 'bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border border-[var(--semantic-alert-border)]'
                    : dialogState.variant === 'warning'
                    ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                    : 'bg-[var(--wood-500)]/10 text-[var(--wood-500)] border border-[var(--wood-500)]/30'
                }`}
              >
                {dialogState.variant === 'danger' ? (
                  <AlertTriangle className="w-5 h-5" />
                ) : dialogState.variant === 'warning' ? (
                  <AlertCircle className="w-5 h-5" />
                ) : (
                  <CheckCircle2 className="w-5 h-5" />
                )}
              </div>

              <div className="flex-1 pr-6">
                <h3
                  id="confirm-modal-title"
                  className="font-serif text-base sm:text-lg font-bold text-[var(--text-primary)] leading-snug"
                >
                  {dialogState.title}
                </h3>
                {dialogState.message && (
                  <p className="text-xs sm:text-sm text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                    {dialogState.message}
                  </p>
                )}
              </div>

              <button
                onClick={handleCancel}
                className="absolute top-4 right-4 p-1.5 rounded-btn text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer"
                title="Đóng (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Ô nhập lý do (nếu kích hoạt) */}
            {dialogState.showReasonInput && (
              <div className="space-y-1.5 pt-1">
                <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                  Lý do {dialogState.requireReason ? (
                    <span className="text-[var(--semantic-alert)]">*</span>
                  ) : (
                    <span className="text-[var(--text-muted)] font-normal">(tùy chọn để lưu vết sổ sách)</span>
                  )}
                </label>
                <textarea
                  ref={textareaRef}
                  rows={2}
                  value={reasonValue}
                  onChange={(e) => {
                    setReasonValue(e.target.value);
                    if (reasonError) setReasonError('');
                  }}
                  placeholder={dialogState.reasonPlaceholder}
                  className="w-full text-xs p-3 rounded-input bg-[var(--bg-canvas)] border border-[var(--border-medium)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--wood-500)] focus:ring-1 focus:ring-[var(--wood-500)] transition-colors resize-none shadow-2xs"
                />
                {reasonError && (
                  <p className="text-xs text-[var(--semantic-alert)] font-medium">
                    {reasonError}
                  </p>
                )}
                <span className="text-[11px] text-[var(--text-muted)] block">
                  Mẹo: Nhấn <kbd className="px-1 py-0.5 rounded bg-[var(--bg-surface-hover)] font-mono text-[10px]">Ctrl + Enter</kbd> để xác nhận nhanh.
                </span>
              </div>
            )}

            {/* Thanh nút hành động (Buttons) */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[var(--border-subtle)]">
              <button
                type="button"
                onClick={handleCancel}
                className="btn-secondary px-4 py-2 text-xs font-semibold"
              >
                {dialogState.cancelText}
              </button>

              <button
                type="button"
                onClick={handleConfirm}
                className={`px-4 py-2 text-xs font-semibold rounded-btn transition-colors cursor-pointer shadow-xs ${
                  dialogState.variant === 'danger'
                    ? 'btn-danger bg-[var(--semantic-alert)] text-white hover:opacity-90'
                    : dialogState.variant === 'warning'
                    ? 'bg-amber-600 text-white hover:bg-amber-700'
                    : 'btn-primary'
                }`}
              >
                {dialogState.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
};

export const useConfirm = () => {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error('useConfirm must be used within a ConfirmProvider');
  }
  return context;
};
