/**
 * Kênh sự kiện biến động kho (Stock Event Hub).
 * Sử dụng EventTarget native của trình duyệt, siêu nhẹ, không phụ thuộc thư viện ngoài.
 * Cho phép phát tín hiệu và nhận diện thay đổi số dư tồn kho giữa các tab Keep-Alive.
 */

const target = new EventTarget();
const EVENT_NAME = 'stock:changed';

export const stockEvents = {
  /**
   * Phát tín hiệu khi có biến động kho (nhập, xuất, hủy, điều chỉnh)
   * @param {Object} detail - Thông tin chi tiết: { url, patches?: [{ id, current_stock }] }
   */
  emit(detail = {}) {
    target.dispatchEvent(
      new CustomEvent(EVENT_NAME, {
        detail: {
          timestamp: Date.now(),
          ...detail,
        },
      })
    );
  },

  /**
   * Đăng ký lắng nghe biến động kho
   * @param {Function} callback - Nhận { timestamp, url, patches, ... }
   * @returns {Function} Hàm hủy đăng ký (unsubscribe)
   */
  subscribe(callback) {
    const handler = (e) => callback(e.detail);
    target.addEventListener(EVENT_NAME, handler);
    return () => target.removeEventListener(EVENT_NAME, handler);
  },
};

export default stockEvents;
