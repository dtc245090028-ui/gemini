import { useEffect, useRef } from 'react';
import { stockEvents } from '../utils/stockEvents';
import { CLIENT_ID, invalidateCache } from '../api/client';

/**
 * Hook quản lý kết nối Server-Sent Events (SSE) thời gian thực qua fetch + ReadableStream.
 * - Xác thực JWT Bearer trong Header Authorization (không lộ token trên URL).
 * - Tự động tái kết nối với Exponential Backoff + Jitter khi ngắt mạng.
 * - Tự động tải lại toàn bộ (Full Refetch) khi tab active trở lại (VisibilityChange).
 * - Lọc bỏ sự kiện trùng lặp từ chính phiên người dùng thông qua X-Client-Id.
 */
export function useServerEvents() {
  const abortControllerRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const retryAttemptRef = useRef(0);
  const isInitialConnectRef = useRef(true);

  useEffect(() => {
    let isMounted = true;

    async function connectSSE() {
      const token = localStorage.getItem('token');
      if (!token) return;

      // Hủy kết nối cũ nếu có
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch('/api/v1/events/stream', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'text/event-stream',
            'X-Client-Id': CLIENT_ID,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          if (response.status === 401) {
            console.warn('[SSE] Token hết hạn hoặc không hợp lệ.');
            return;
          }
          throw new Error(`SSE kết nối thất bại với mã trạng thái ${response.status}`);
        }

        const isReconnect = !isInitialConnectRef.current;
        isInitialConnectRef.current = false;
        retryAttemptRef.current = 0; // Đặt lại bộ đếm retry khi kết nối thành công

        if (isReconnect) {
          console.info('[SSE] Tái kết nối thành công, tự động đồng bộ lại toàn bộ dữ liệu.');
          invalidateCache();
          if (typeof document === 'undefined' || document.visibilityState === 'visible') {
            stockEvents.emit({ type: 'FULL_REFETCH' });
          }
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (isMounted) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // Giữ lại đoạn chưa kết thúc bằng newline

          let currentEventName = null;
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(':')) {
              // Comment / keepalive heartbeat -> bỏ qua
              continue;
            }

            if (trimmed.startsWith('event:')) {
              currentEventName = trimmed.replace('event:', '').trim();
            } else if (trimmed.startsWith('data:')) {
              const dataStr = trimmed.replace('data:', '').trim();
              try {
                const payload = JSON.parse(dataStr);
                handleServerEvent(currentEventName, payload);
              } catch (parseErr) {
                console.error('[SSE] Lỗi phân tích cú pháp dữ liệu sự kiện:', parseErr);
              }
              currentEventName = null;
            }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') {
          return; // Client chủ động ngắt
        }
        console.warn('[SSE] Mất kết nối luồng sự kiện:', err.message);
        scheduleReconnect();
      }
    }

    function handleServerEvent(eventName, payload) {
      if (eventName === 'data_changed') {
        const clientIds = payload.client_ids || [];
        // Nếu sự kiện được khởi phát từ chính tab/client này, state cục bộ đã tự cập nhật
        const isSelfOriginated = clientIds.includes(CLIENT_ID);
        
        // Luôn xóa cache tài nguyên tương ứng
        if (payload.resource) {
          invalidateCache(`/${payload.resource}`);
        }
        invalidateCache('/reports');

        // Phát sự kiện ra toàn bộ giao diện (chỉ refetch nếu không phải tự mình vừa cập nhật hoặc là Thẻ kho)
        stockEvents.emit({
          type: 'SERVER_DATA_CHANGED',
          resource: payload.resource,
          action: payload.action,
          isSelfOriginated,
        });
      }
    }

    function scheduleReconnect() {
      if (!isMounted) return;
      const attempt = retryAttemptRef.current;
      // Exponential backoff: 1s, 2s, 4s, 8s, tối đa 15s + jitter
      const delayMs = Math.min(15000, 1000 * Math.pow(2, attempt)) + Math.random() * 500;
      retryAttemptRef.current = attempt + 1;

      console.debug(`[SSE] Sẽ thử kết nối lại sau ${Math.round(delayMs)} ms...`);
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(() => {
        if (isMounted) connectSSE();
      }, delayMs);
    }

    // Lắng nghe khi tab người dùng active trở lại -> Full Refetch đồng bộ
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        invalidateCache();
        stockEvents.emit({ type: 'FULL_REFETCH' });
        // Kiểm tra xem kết nối SSE có còn sống không
        if (abortControllerRef.current === null) {
          connectSSE();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    connectSSE();

    return () => {
      isMounted = false;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearTimeout(reconnectTimeoutRef.current);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);
}
