import React from 'react';

export const Badge = ({ children, variant = 'gray', className = '' }) => {
  const variants = {
    gray: 'bg-[#F5F5F0] text-charcoal border-[#E8D5B7]/70',
    blue: 'bg-[#EEF5FB] text-[#2C5282] border-[#BEE3F8]',
    green: 'bg-forest-50 text-forest-500 border-forest-200',
    amber: 'bg-wood-50 text-wood-600 border-wood-300',
    red: 'bg-rust-50 text-rust-500 border-rust-200',
    purple: 'bg-[#F7EFE8] text-wood-700 border-wood-200',
    wood: 'bg-wood-100 text-wood-800 border-wood-200',
    sage: 'bg-sage-50 text-sage-600 border-sage-200',
  };

  const selected = variants[variant] || variants.gray;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${selected} ${className}`}
    >
      {children}
    </span>
  );
};

export default Badge;
