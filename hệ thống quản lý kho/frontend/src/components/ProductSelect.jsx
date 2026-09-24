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
          className="w-full text-xs bg-wood-50/70 border border-wood-200 rounded-lg pl-2.5 pr-12 py-1.5 text-wood-900 focus:outline-none focus:ring-1 focus:ring-wood-400 focus:border-wood-400 placeholder:text-wood-400"
          autoComplete="off"
        />

        <div className="absolute right-1 flex items-center gap-0.5">
          {searchQuery && isOpen && (
            <button
              type="button"
              tabIndex={-1}
              onClick={handleClear}
              className="text-wood-400 hover:text-wood-600 p-0.5 rounded cursor-pointer"
              title="Xóa tìm kiếm"
            >
              <X className="w-3 h-3" />
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
            className="text-wood-400 hover:text-wood-600 p-1 cursor-pointer"
            title="Mở danh sách hàng hóa"
          >
            <ChevronDown
              className={`w-3.5 h-3.5 transition-transform duration-150 ${
                isOpen ? 'rotate-180 text-wood-700' : ''
              }`}
            />
          </button>
        </div>
      </div>

      {/* Danh sách Dropdown xổ xuống */}
      {isOpen && (
        <div
          ref={listRef}
          className="absolute left-0 right-0 top-full mt-1 bg-white border border-wood-200 rounded-xl shadow-xl z-50 max-h-52 overflow-y-auto divide-y divide-wood-100"
        >
          {filteredProducts.length === 0 ? (
            <div className="p-3 text-center text-xs text-wood-500 italic">
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
                    // Dùng onMouseDown để ngăn blur input trước khi sự kiện chọn diễn ra
                    e.preventDefault();
                    handleSelect(p);
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`flex items-center justify-between px-3 py-2 cursor-pointer text-xs transition-colors ${
                    isHighlighted
                      ? 'bg-wood-100/90 text-wood-900'
                      : isSelected
                      ? 'bg-wood-50 font-semibold text-wood-900'
                      : 'text-wood-800 hover:bg-wood-50'
                  }`}
                >
                  <div className="flex items-center gap-1.5 flex-1 min-w-0 pr-2">
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-forest-600 shrink-0" />
                    )}
                    <span className="truncate">{p.name}</span>
                  </div>
                  <span
                    className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      p.current_stock > 0
                        ? 'bg-forest-50 text-forest-700'
                        : 'bg-rust-50 text-rust-700'
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
