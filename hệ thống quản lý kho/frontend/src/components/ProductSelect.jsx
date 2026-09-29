import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check, X } from 'lucide-react';

/**
 * Loại bỏ dấu tiếng Việt để tìm kiếm không phân biệt dấu
 */
export const removeVietnameseDiacritics = (str) => {
  if (!str) return '';
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim();
};

/**
 * Lấy các chữ cái đầu của từng từ (Viết tắt / Acronym)
 * Ví dụ: "Bàn Làm Việc Gỗ Sồi" -> "blvgs"
 */
export const getInitials = (str) => {
  const normalized = removeVietnameseDiacritics(str);
  return normalized
    .split(/[\s\-_]+/)
    .filter(Boolean)
    .map((word) => word[0])
    .join('');
};

/**
 * Kiểm tra sản phẩm có khớp với từ khóa tìm kiếm hay không:
 * 1. Khớp chuỗi con trong tên (có dấu hoặc không dấu, ví dụ: "bàn" hoặc "ban")
 * 2. Khớp theo chữ cái đầu các từ (ví dụ: "blv" cho "Bàn Làm Việc")
 * 3. Khớp tiền tố của bất kỳ từ nào (ví dụ: gõ "soi" khớp "Gỗ Sồi")
 */
export const matchProduct = (product, query) => {
  if (!query || !query.trim()) return true;
  const qClean = removeVietnameseDiacritics(query);
  const nameClean = removeVietnameseDiacritics(product.name || '');

  // 1. Khớp chuỗi con trực tiếp
  if (nameClean.includes(qClean)) return true;

  // 2. Khớp chữ cái đầu từng từ (Initials / Viết tắt)
  const initials = getInitials(product.name || '');
  if (initials.includes(qClean)) return true;

  // 3. Khớp tiền tố của bất kỳ từ đơn nào trong tên
  const words = nameClean.split(/[\s\-_]+/).filter(Boolean);
  if (words.some((w) => w.startsWith(qClean))) return true;

  return false;
};

export const ProductSelect = ({
  products = [],
  value,
  onChange,
  placeholder = 'Gõ tên hoặc chữ cái đầu (VD: blv)...',
  disabled = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const selectedProduct = products.find((p) => p.id === Number(value));

  // Lọc danh sách sản phẩm theo từ khóa (nếu người dùng đang gõ tìm kiếm)
  const filteredProducts = isTyping
    ? products.filter((p) => matchProduct(p, searchQuery))
    : products;

  // Đồng bộ giá trị hiển thị trên ô nhập với sản phẩm đã chọn
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery(selectedProduct ? selectedProduct.name : '');
      setIsTyping(false);
    }
  }, [value, selectedProduct, isOpen]);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
        setIsTyping(false);
        setSearchQuery(selectedProduct ? selectedProduct.name : '');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [selectedProduct]);

  // Tự động cuộn theo phần tử đang được highlight bằng bàn phím
  useEffect(() => {
    if (isOpen && listRef.current && listRef.current.children[highlightedIndex]) {
      listRef.current.children[highlightedIndex].scrollIntoView({
        block: 'nearest',
      });
    }
  }, [highlightedIndex, isOpen]);

  const handleFocus = () => {
    if (disabled) return;
    setIsOpen(true);
    // Bôi đen toàn bộ chữ hiện tại để người dùng có thể gõ đè ngay lập tức
    if (inputRef.current) {
      inputRef.current.select();
    }
  };

  const handleInputChange = (e) => {
    setSearchQuery(e.target.value);
    setIsTyping(true);
    setIsOpen(true);
    setHighlightedIndex(0);
  };

  const handleSelect = (product) => {
    onChange(product.id);
    setSearchQuery(product.name);
    setIsTyping(false);
    setIsOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    setSearchQuery('');
    setIsTyping(true);
    setIsOpen(true);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < filteredProducts.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredProducts.length - 1
      );
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredProducts[highlightedIndex]) {
        handleSelect(filteredProducts[highlightedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setIsTyping(false);
      setSearchQuery(selectedProduct ? selectedProduct.name : '');
    }
  };

  return (
    <div ref={containerRef} className={`relative flex-1 ${className}`}>
      <div className="relative flex items-center">
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input pl-3 pr-12 py-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] focus:ring-1 focus:ring-[var(--wood-500)] placeholder:text-[var(--text-muted)] transition-colors"
          autoComplete="off"
        />

        <div className="absolute right-1.5 flex items-center gap-0.5">
          {searchQuery && isOpen && (
            <button
              type="button"
              tabIndex={-1}
              onClick={handleClear}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 rounded-btn cursor-pointer"
              title="Xóa tìm kiếm"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="button"
            tabIndex={-1}
            onClick={() => {
              if (isOpen) {
                setIsOpen(false);
              } else {
                inputRef.current?.focus();
              }
            }}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 cursor-pointer rounded-btn"
            title="Mở danh sách hàng hóa"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform duration-fast ${
                isOpen ? 'rotate-180 text-[var(--wood-500)]' : ''
              }`}
            />
          </button>
        </div>
      </div>

      {/* Danh sách Dropdown xổ xuống */}
      {isOpen && (
        <div
          ref={listRef}
          className="absolute left-0 right-0 top-full mt-1.5 bg-[var(--bg-surface)] border border-[var(--border-strong)] rounded-card shadow-lg z-50 max-h-56 overflow-y-auto divide-y divide-[var(--border-subtle)]"
        >
          {filteredProducts.length === 0 ? (
            <div className="p-3.5 text-center text-xs text-[var(--text-muted)] italic">
              Không tìm thấy hàng hóa (thử gõ chữ cái đầu hoặc từ khóa khác)
            </div>
          ) : (
            filteredProducts.map((p, index) => {
              const isSelected = p.id === Number(value);
              const isHighlighted = index === highlightedIndex;

              return (
                <div
                  key={p.id}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSelect(p);
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`flex items-center justify-between px-3.5 py-2.5 cursor-pointer text-xs transition-colors ${
                    isHighlighted
                      ? 'bg-[var(--bg-surface-hover)] text-[var(--text-primary)]'
                      : isSelected
                      ? 'bg-[var(--bg-surface-warm)] font-semibold text-[var(--text-primary)]'
                      : 'text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)]'
                  }`}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0 pr-2">
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-[var(--semantic-success)] shrink-0" />
                    )}
                    <span className="truncate">{p.name}</span>
                  </div>
                  <span
                    className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-semibold border ${
                      p.current_stock > 0
                        ? 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)]'
                        : 'bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border-[var(--semantic-alert-border)]'
                    }`}
                  >
                    Tồn: {p.current_stock}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default ProductSelect;
