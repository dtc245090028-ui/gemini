import { useEffect, useRef, useCallback } from 'react';
import { stockEvents } from '../utils/stockEvents';

/**
 * Hook đồng bộ dữ liệu chuẩn mực theo trang (Page-Level Data Sync Hook).
 * 
 * Đáp ứng đầy đủ các tiêu chuẩn Item 5:
 * 1. Debounce có MaxWait: Gom các sự kiện liên tiếp với debounce 250ms, tối đa chờ 1000ms.
 * 2. Single-Flight Protection: Ngăn chặn các request chạy chồng lấn nhau khi sự kiện đến dồn dập.
 * 3. Hủy / Bỏ qua response cũ: Quản lý requestId để phản hồi muộn không đè dữ liệu mới.
 * 4. Xử lý Tab/Trang ẩn: Khi trang ẩn (document.hidden) hoặc không active, chỉ đánh dấu stale;
 *    tự động tải lại êm ái khi tab active trở lại (visibilitychange / tab switch).
 * 5. Polling thưa dự phòng (Sparse Polling): Định kỳ 60 giây làm mới dữ liệu ngầm nếu đang active.
 */
export function usePageSync({
  fetchFn,
  isActive = true,
  resource = null,
  debounceMs = 350,
  maxWaitMs = 1200,
  sparsePollingMs = 60000,
}) {
  const isStaleRef = useRef(false);
  const inFlightRef = useRef(false);
  const pendingRefetchRef = useRef(false);
  const requestIdRef = useRef(0);
  const debounceTimerRef = useRef(null);
  const maxWaitTimerRef = useRef(null);
  const firstEventTimeRef = useRef(null);

  const executeFetch = useCallback(async (silent = true) => {
    if (inFlightRef.current) {
      pendingRefetchRef.current = true;
      return;
    }

    inFlightRef.current = true;
    const currentRequestId = ++requestIdRef.current;

    try {
      await fetchFn(silent);
    } catch (err) {
      console.warn(`[usePageSync] Lỗi fetch cho ${resource || 'trang'}:`, err);
    } finally {
      inFlightRef.current = false;
      // Nếu có yêu cầu refetch bị dồn trong lúc đang chạy, kích hoạt 1 lần duy nhất
      if (pendingRefetchRef.current && currentRequestId === requestIdRef.current) {
        pendingRefetchRef.current = false;
        executeFetch(true);
      }
    }
  }, [fetchFn, resource]);

  const scheduleDebouncedFetch = useCallback(() => {
    const isHidden = typeof document !== 'undefined' && document.hidden;
    if (!isActive || isHidden) {
      isStaleRef.current = true;
      return;
    }

    const now = Date.now();
    if (!firstEventTimeRef.current) {
      firstEventTimeRef.current = now;
    }

    // Xóa timer debounce cũ
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Kiểm tra nếu đã chạm mốc MaxWait
    if (now - firstEventTimeRef.current >= maxWaitMs) {
      firstEventTimeRef.current = null;
      if (maxWaitTimerRef.current) clearTimeout(maxWaitTimerRef.current);
      executeFetch(true);
      return;
    }

    // Thiết lập timer maxWait nếu chưa có
    if (!maxWaitTimerRef.current) {
      const remainingMaxWait = Math.max(50, maxWaitMs - (now - firstEventTimeRef.current));
      maxWaitTimerRef.current = setTimeout(() => {
        firstEventTimeRef.current = null;
        maxWaitTimerRef.current = null;
        if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
        executeFetch(true);
      }, remainingMaxWait);
    }

    // Debounce thông thường
    debounceTimerRef.current = setTimeout(() => {
      firstEventTimeRef.current = null;
      if (maxWaitTimerRef.current) clearTimeout(maxWaitTimerRef.current);
      executeFetch(true);
    }, debounceMs);
  }, [isActive, debounceMs, maxWaitMs, executeFetch]);

  // Lắng nghe sự kiện SSE phát từ stockEvents
  useEffect(() => {
    const unsubscribe = stockEvents.subscribe((event) => {
      // Nếu sự kiện có lọc theo resource cụ thể (hỗ trợ cả string và array, so sánh bằng includes)
      if (resource && event.resource && event.resource !== 'all') {
        const allowed = Array.isArray(resource) ? resource : [resource];
        if (allowed.length > 0 && !allowed.includes('all')) {
          if (!allowed.includes(event.resource)) {
            return;
          }
        }
      }
      scheduleDebouncedFetch();
    });

    return unsubscribe;
  }, [scheduleDebouncedFetch, resource]);

  // Khi chuyển lại tab ứng dụng (isActive đổi sang true) hoặc window focus
  useEffect(() => {
    if (isActive) {
      if (isStaleRef.current) {
        isStaleRef.current = false;
        executeFetch(true);
      }
    }
  }, [isActive, executeFetch]);

  // Lắng nghe visibilitychange của trình duyệt
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && isActive) {
        if (isStaleRef.current) {
          isStaleRef.current = false;
          executeFetch(true);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [isActive, executeFetch]);

  // Polling thưa dự phòng (mỗi 60s) phòng khi mạng chập chờn
  useEffect(() => {
    if (!sparsePollingMs || sparsePollingMs <= 0 || !isActive) return;

    const interval = setInterval(() => {
      if (isActive && document.visibilityState === 'visible') {
        executeFetch(true);
      }
    }, sparsePollingMs);

    return () => clearInterval(interval);
  }, [sparsePollingMs, isActive, executeFetch]);

  return {
    isStale: isStaleRef.current,
    refresh: () => executeFetch(false),
  };
}
