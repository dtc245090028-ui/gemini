import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message, type = 'info', duration = 3500) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
    return id;
  }, [removeToast]);

  const showSuccess = useCallback((msg, duration) => showToast(msg, 'success', duration), [showToast]);
  const showError = useCallback((msg, duration) => showToast(msg, 'error', duration), [showToast]);
  const showInfo = useCallback((msg, duration) => showToast(msg, 'info', duration), [showToast]);
  const showWarning = useCallback((msg, duration) => showToast(msg, 'warning', duration), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, showSuccess, showError, showInfo, showWarning, removeToast }}>
      {children}
      {/* Container hiển thị Toast thông báo nổi ở góc trên bên phải */}
      <div
        className="fixed top-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none sm:max-w-md"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const typeConfig = {
            success: {
              icon: CheckCircle2,
              bgClass: 'bg-[var(--bg-surface)] border-l-4 border-l-[var(--semantic-success)] border-[var(--border-subtle)]',
              iconClass: 'text-[var(--semantic-success)]',
            },
            error: {
              icon: AlertCircle,
              bgClass: 'bg-[var(--bg-surface)] border-l-4 border-l-[var(--semantic-alert)] border-[var(--border-subtle)]',
              iconClass: 'text-[var(--semantic-alert)]',
            },
            warning: {
              icon: AlertTriangle,
              bgClass: 'bg-[var(--bg-surface)] border-l-4 border-l-amber-500 border-[var(--border-subtle)]',
              iconClass: 'text-amber-500',
            },
            info: {
              icon: Info,
              bgClass: 'bg-[var(--bg-surface)] border-l-4 border-l-[var(--wood-500)] border-[var(--border-subtle)]',
              iconClass: 'text-[var(--wood-500)]',
            },
          };

          const config = typeConfig[toast.type] || typeConfig.info;
          const Icon = config.icon;

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto p-4 rounded-card shadow-lg flex items-start gap-3 text-[var(--text-primary)] transition-all duration-200 transform translate-y-0 opacity-100 ${config.bgClass}`}
              role="alert"
            >
              <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${config.iconClass}`} />
              <div className="flex-1 text-xs sm:text-sm font-medium leading-relaxed">
                {toast.message}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="p-1 -mr-1 -mt-1 rounded-btn text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer shrink-0"
                title="Đóng thông báo"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
