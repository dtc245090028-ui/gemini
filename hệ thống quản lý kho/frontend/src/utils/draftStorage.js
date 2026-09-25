/**
 * Tiện ích quản lý Bản Nháp Tự Động (Form Draft Auto-Persistence with 1-Day TTL).
 * 
 * - Tự động lưu trữ nội dung thao tác dở vào localStorage theo từng tài khoản người dùng.
 * - Giữ lại tối đa đúng 1 ngày (24 giờ = 86,400,000 ms).
 * - Tự động tiêu hủy nếu bản nháp đã quá 24 giờ.
 * - Xóa sạch khi hoàn thành thao tác thành công hoặc khi người dùng chủ động bấm hủy nháp.
 */

const ONE_DAY_MS = 24 * 60 * 60 * 1000; // 24 giờ tính bằng mili-giây
const DRAFT_PREFIX = 'smartkho_draft_';

export const draftStorage = {
  /**
   * Lưu dữ liệu bản nháp vào localStorage
   * @param {string} username - Tên tài khoản đang đăng nhập
   * @param {string} formKey - Mã định danh form (vd: 'import_note', 'export_note', 'product_search')
   * @param {any} data - Dữ liệu form cần lưu
   * @param {number} ttlMs - Thời gian sống (mặc định 24h)
   */
  save: (username, formKey, data, ttlMs = ONE_DAY_MS) => {
    if (!username || !formKey || data === undefined || data === null) return;
    try {
      const now = Date.now();
      const payload = {
        saved_at: now,
        expires_at: now + ttlMs,
        data,
      };
      localStorage.setItem(`${DRAFT_PREFIX}${username}_${formKey}`, JSON.stringify(payload));
    } catch (e) {
      console.warn('[draftStorage] Không thể ghi bản nháp vào localStorage:', e);
    }
  },

  /**
   * Đọc dữ liệu bản nháp từ localStorage.
   * Nếu dữ liệu đã quá 24h (hết hạn), tự động xóa bỏ và trả về null.
   * @param {string} username - Tên tài khoản
   * @param {string} formKey - Mã định danh form
   * @returns {{ data: any, saved_at: number, expires_at: number } | null}
   */
  load: (username, formKey) => {
    if (!username || !formKey) return null;
    const storageKey = `${DRAFT_PREFIX}${username}_${formKey}`;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return null;

      const payload = JSON.parse(raw);
      if (!payload || !payload.expires_at) {
        localStorage.removeItem(storageKey);
        return null;
      }

      // Kiểm tra thời hạn 24 giờ
      if (Date.now() > payload.expires_at) {
        localStorage.removeItem(storageKey); // Quá 1 ngày -> Tự động tiêu hủy!
        return null;
      }

      return payload;
    } catch (e) {
      console.warn('[draftStorage] Lỗi khi đọc bản nháp:', e);
      return null;
    }
  },

  /**
   * Xóa bản nháp khi hoàn thành form hoặc người dùng bấm "Hủy nháp"
   * @param {string} username 
   * @param {string} formKey 
   */
  clear: (username, formKey) => {
    if (!username || !formKey) return;
    try {
      localStorage.removeItem(`${DRAFT_PREFIX}${username}_${formKey}`);
    } catch (e) {
      console.warn('[draftStorage] Lỗi khi xóa bản nháp:', e);
    }
  },

  /**
   * Quét và dọn dẹp toàn bộ các bản nháp đã quá hạn 1 ngày trong localStorage
   */
  cleanupExpired: () => {
    try {
      const now = Date.now();
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(DRAFT_PREFIX)) {
          try {
            const raw = localStorage.getItem(k);
            if (raw) {
              const payload = JSON.parse(raw);
              if (payload && payload.expires_at && now > payload.expires_at) {
                keysToRemove.push(k);
              }
            }
          } catch {
            keysToRemove.push(k);
          }
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    } catch (e) {
      console.warn('[draftStorage] Lỗi khi dọn dẹp bản nháp hết hạn:', e);
    }
  },

  /**
   * Định dạng thời gian lưu bản nháp theo tiếng Việt thân thiện
   * @param {number} timestamp 
   * @returns {string} Ví dụ: "14:35 hôm nay", "09:20 hôm qua"
   */
  formatSavedTime: (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const timeStr = `${hours}:${minutes}`;

    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear();

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday =
      date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear();

    if (isToday) return `${timeStr} hôm nay`;
    if (isYesterday) return `${timeStr} hôm qua`;

    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${timeStr} ngày ${day}/${month}`;
  },
};

export default draftStorage;
