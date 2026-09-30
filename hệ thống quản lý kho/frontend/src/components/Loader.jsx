import React, { useState, useEffect } from 'react';
import './Loader.css';

/**
 * Component Loader đa năng chuẩn "Timber & Grain"
 * @param {'page' | 'inline' | 'table'} variant - Biến thể hiển thị
 * @param {string} message - Thông báo ngữ cảnh
 * @param {boolean} isAi - Bật dòng trạng thái đếm giờ ngữ cảnh cho tác vụ AI
 * @param {number} columns - Số cột cho variant="table"
 * @param {number} rows - Số dòng cho variant="table"
 * @param {string} className - Class tùy biến bổ sung
 */
export const Loader = ({
  variant = 'page',
  message = 'Đang tải dữ liệu...',
  isAi = false,
  columns = 6,
  rows = 6,
  className = '',
}) => {
  // Trạng thái phụ theo thời gian cho các tác vụ AI
  const [aiStage, setAiStage] = useState(0); // 0: ban đầu, 1: sau 3s, 2: sau 10s

  useEffect(() => {
    if (!isAi) return;

    const timer3s = setTimeout(() => {
      setAiStage(1);
    }, 3000);

    const timer10s = setTimeout(() => {
      setAiStage(2);
    }, 10000);

    return () => {
      clearTimeout(timer3s);
      clearTimeout(timer10s);
    };
  }, [isAi]);

  // =========================================================================
  // BIẾN THỂ 1: INLINE (Dùng trong nút bấm hoặc cạnh chữ, 20-24px)
  // =========================================================================
  if (variant === 'inline') {
    return (
      <span
        role="status"
        aria-live="polite"
        className={`inline-flex items-center justify-center shrink-0 w-4 h-4 mr-1.5 text-current ${className}`}
      >
        <svg
          className="w-4 h-4 sk-inline-spinner"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            cx="12"
            cy="12"
            r="9"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeOpacity="0.25"
          />
          <path
            d="M12 3C7.02944 3 3 7.02944 3 12"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        <span className="sr-only">Đang xử lý...</span>
      </span>
    );
  }

  // =========================================================================
  // BIẾN THỂ 2: TABLE SKELETON (Khung xương mờ nhấp nháy cho bảng danh sách)
  // =========================================================================
  if (variant === 'table') {
    // Độ rộng giả lập so le tự nhiên cho các cột
    const widths = ['w-3/4', 'w-4/5', 'w-1/2', 'w-2/3', 'w-3/5', 'w-5/6', 'w-1/3', 'w-2/3'];

    return (
      <>
        {[...Array(rows)].map((_, rIdx) => (
          <tr key={rIdx} className="sk-skeleton-pulse border-b border-[var(--border-subtle)]">
            {[...Array(columns)].map((_, cIdx) => (
              <td key={cIdx} className="py-3.5 px-4">
                <div
                  className={`h-3.5 rounded-sm bg-[var(--border-medium)]/60 ${
                    widths[(rIdx + cIdx) % widths.length]
                  }`}
                />
              </td>
            ))}
          </tr>
        ))}
      </>
    );
  }

  // Kiểm tra nếu biến môi trường VITE_USE_ANIME_GIF được bật
  const isCustomGifEnabled = Boolean(import.meta.env?.VITE_USE_ANIME_GIF === 'true');

  return (
    <div
      role="status"
      aria-live="polite"
      className={`sk-loader-container flex flex-col items-center justify-center p-8 text-center select-none ${className}`}
    >
      {isCustomGifEnabled ? (
        <div className="w-56 h-56 relative mb-3 flex items-center justify-center">
          <img
            src="/anime-dance.gif"
            alt="Đang tải dữ liệu..."
            className="w-full h-full object-contain drop-shadow-md rounded-card"
          />
        </div>
      ) : (
        /* Đồ họa SVG Vector 3 thùng hàng gỗ & Pallet chuẩn Timber & Grain */
        <div className="w-32 h-24 relative mb-3">
          <svg
            viewBox="0 0 120 115"
            className="w-full h-full"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
          {/* Bóng mờ đáy pallet */}
          <ellipse
            cx="60"
            cy="106"
            rx="46"
            ry="4.5"
            fill="var(--text-primary)"
            className="sk-pallet-shadow"
          />

          {/* Pallet gỗ đỡ hàng đáy (Wooden Pallet Base) */}
          <g className="pallet-base">
            {/* Thanh nan pallet ngang */}
            <rect
              x="14"
              y="94"
              width="92"
              height="4.5"
              rx="1.5"
              fill="var(--bg-linen)"
              stroke="var(--border-strong)"
              strokeWidth="1.2"
            />
            {/* 3 khối chân kê pallet */}
            <rect
              x="16"
              y="98.5"
              width="10"
              height="6"
              rx="1"
              fill="var(--border-strong)"
            />
            <rect
              x="55"
              y="98.5"
              width="10"
              height="6"
              rx="1"
              fill="var(--border-strong)"
            />
            <rect
              x="94"
              y="98.5"
              width="10"
              height="6"
              rx="1"
              fill="var(--border-strong)"
            />
            {/* Thanh nan đáy */}
            <rect
              x="14"
              y="104.5"
              width="92"
              height="3"
              rx="1"
              fill="var(--bg-linen)"
              stroke="var(--border-strong)"
              strokeWidth="0.8"
            />
          </g>

          {/* Thùng hàng gỗ 1: Dưới bên trái */}
          <g className="sk-crate-1">
            <rect
              x="25"
              y="62"
              width="31"
              height="31"
              rx="2.5"
              fill="var(--bg-card)"
              stroke="var(--wood-500)"
              strokeWidth="1.5"
            />
            {/* Vân thanh chéo chữ X dập nổi */}
            <line
              x1="26"
              y1="63"
              x2="55"
              y2="92"
              stroke="var(--border-strong)"
              strokeWidth="1.2"
              strokeDasharray="2 1"
            />
            <line
              x1="55"
              y1="63"
              x2="26"
              y2="92"
              stroke="var(--border-strong)"
              strokeWidth="1.2"
              strokeDasharray="2 1"
            />
            {/* Viền nẹp gỗ góc */}
            <circle cx="28" cy="65" r="1" fill="var(--wood-accent)" />
            <circle cx="53" cy="65" r="1" fill="var(--wood-accent)" />
            <circle cx="28" cy="90" r="1" fill="var(--wood-accent)" />
            <circle cx="53" cy="90" r="1" fill="var(--wood-accent)" />
          </g>

          {/* Thùng hàng gỗ 2: Dưới bên phải */}
          <g className="sk-crate-2">
            <rect
              x="64"
              y="62"
              width="31"
              height="31"
              rx="2.5"
              fill="var(--bg-card)"
              stroke="var(--wood-500)"
              strokeWidth="1.5"
            />
            {/* Vân thanh chéo chữ X dập nổi */}
            <line
              x1="65"
              y1="63"
              x2="94"
              y2="92"
              stroke="var(--border-strong)"
              strokeWidth="1.2"
              strokeDasharray="2 1"
            />
            <line
              x1="94"
              y1="63"
              x2="65"
              y2="92"
              stroke="var(--border-strong)"
              strokeWidth="1.2"
              strokeDasharray="2 1"
            />
            {/* Viền nẹp gỗ góc */}
            <circle cx="67" cy="65" r="1" fill="var(--wood-accent)" />
            <circle cx="92" cy="65" r="1" fill="var(--wood-accent)" />
            <circle cx="67" cy="90" r="1" fill="var(--wood-accent)" />
            <circle cx="92" cy="90" r="1" fill="var(--wood-accent)" />
          </g>

          {/* Thùng hàng gỗ 3: Xếp trên đỉnh ở giữa */}
          <g className="sk-crate-3">
            <rect
              x="44.5"
              y="28"
              width="31"
              height="31"
              rx="2.5"
              fill="var(--bg-card)"
              stroke="var(--wood-accent)"
              strokeWidth="1.8"
            />
            {/* Vân thanh chéo chữ X dập nổi */}
            <line
              x1="45.5"
              y1="29"
              x2="74.5"
              y2="58"
              stroke="var(--wood-500)"
              strokeWidth="1.2"
            />
            <line
              x1="74.5"
              y1="29"
              x2="45.5"
              y2="58"
              stroke="var(--wood-500)"
              strokeWidth="1.2"
            />
            {/* Viền nẹp gỗ góc vàng kim */}
            <circle cx="47.5" cy="31" r="1.2" fill="var(--wood-accent)" />
            <circle cx="72.5" cy="31" r="1.2" fill="var(--wood-accent)" />
            <circle cx="47.5" cy="56" r="1.2" fill="var(--wood-accent)" />
            <circle cx="72.5" cy="56" r="1.2" fill="var(--wood-accent)" />
          </g>
        </svg>
      </div>
    )}

      {/* Dòng chữ thông báo chính */}
      <p className="text-xs font-semibold text-[var(--text-primary)] font-serif tracking-wide max-w-sm">
        {message}
      </p>

      {/* Dòng chữ trạng thái phụ động cho AI */}
      {isAi && aiStage === 1 && (
        <p className="text-xs text-[var(--semantic-ai)] mt-1 animate-pulse font-medium">
          Vẫn đang xử lý, vui lòng chờ thêm…
        </p>
      )}

      {isAi && aiStage === 2 && (
        <p className="text-xs text-[var(--semantic-alert)] mt-1 font-medium">
          Tác vụ này mất lâu hơn dự kiến…
        </p>
      )}
    </div>
  );
};

export default Loader;
