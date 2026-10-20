import React from 'react';

/**
 * Badge Component — Timber & Grain Design System
 * Sử dụng màu ngữ nghĩa độc lập từ CSS Tokens:
 * - Hết hàng / Cảnh báo = Đỏ đất (alert / red)
 * - Hoàn thành / An toàn = Xanh rêu (success / green / forest)
 * - Đã hủy = Xám ấm (canceled / gray)
 * - Ngưng bán = Nâu xám (inactive / taupe)
 * - Trợ lý AI = Vàng hổ phách mật ong (ai / amber)
 */
export const Badge = ({ children, variant = 'gray', className = '' }) => {
  const variants = {
    // 1. Cảnh báo / Hết hàng = Đỏ đất
    alert: 'bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border-[var(--semantic-alert-border)] font-semibold',
    red: 'bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border-[var(--semantic-alert-border)] font-semibold',

    // 2. Hoàn thành / An toàn = Xanh rêu
    success: 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)] font-semibold',
    green: 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)] font-semibold',
    forest: 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)] font-semibold',
    sage: 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)] font-semibold',

    // 3. Đã hủy = Xám ấm
    canceled: 'bg-[var(--semantic-canceled-bg)] text-[var(--semantic-canceled)] border-[var(--semantic-canceled-border)] font-medium',
    gray: 'bg-[var(--semantic-canceled-bg)] text-[var(--semantic-canceled)] border-[var(--semantic-canceled-border)] font-medium',

    // 4. Ngưng bán = Nâu xám
    inactive: 'bg-[var(--semantic-inactive-bg)] text-[var(--semantic-inactive)] border-[var(--semantic-inactive-border)] font-medium',
    taupe: 'bg-[var(--semantic-inactive-bg)] text-[var(--semantic-inactive)] border-[var(--semantic-inactive-border)] font-medium',

    // 5. Trợ lý AI = Tím Indigo dịu mắt
    ai: 'bg-[var(--semantic-ai-bg)] text-[var(--semantic-ai)] border-[var(--semantic-ai-border)] font-semibold',

    // 6. Cảnh báo vừa / Chờ xử lý = Xanh lam dịu (thay cho vàng chữ nâu)
    amber: 'bg-[var(--semantic-warning-bg)] text-[var(--semantic-warning)] border-[var(--semantic-warning-border)] font-semibold',

    // 7. Các nhãn trung tính & phân loại
    wood: 'bg-[var(--bg-surface-warm)] text-[var(--text-primary)] border-[var(--border-medium)] font-semibold',
    blue: 'bg-[var(--semantic-warning-bg)] text-[var(--semantic-warning)] border-[var(--semantic-warning-border)] font-medium',
    purple: 'bg-[var(--semantic-ai-bg)] text-[var(--semantic-ai)] border-[var(--semantic-ai-border)] font-semibold',
  };

  const selected = variants[variant] || variants.gray;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border tracking-tight whitespace-nowrap ${selected} ${className}`}
    >
      {children}
    </span>
  );
};

export default Badge;
