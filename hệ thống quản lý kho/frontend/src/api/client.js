import axios from 'axios';

// Tạo axios instance
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Tự động gán JWT Bearer Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Xử lý lỗi 401 tự động
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.dispatchEvent(new Event('auth-logout'));
    }
    return Promise.reject(error);
  }
);

// =========================================================================
// TẦNG CACHE BỘ NHỚ & KHỬ TRÙNG LẶP REQUEST (In-Memory Cache & Deduplication)
// =========================================================================
const cache = new Map();
const inFlightRequests = new Map();

// TTL 60s chỉ áp dụng cho GET suppliers, categories, products
const CACHE_TTL_MS = 60 * 1000;
const CACHEABLE_PATTERNS = ['/suppliers', '/categories', '/products'];

/**
 * Kiểm tra xem endpoint có đủ điều kiện cache hay không.
 * Tuyệt đối không cache /auth/* và /ai/*
 */
const isCacheableUrl = (url) => {
  if (!url || typeof url !== 'string') return false;
  if (url.includes('/auth') || url.includes('/ai')) {
    return false;
  }
  return CACHEABLE_PATTERNS.some((pattern) => url.includes(pattern));
};

/**
 * Tạo Cache Key gồm URL + params (chuẩn hóa thứ tự key)
 */
const getCacheKey = (url, params) => {
  if (!params || Object.keys(params).length === 0) {
    return url;
  }
  try {
    const sortedKeys = Object.keys(params).sort();
    const sortedObj = {};
    for (const k of sortedKeys) {
      if (params[k] !== undefined) {
        sortedObj[k] = params[k];
      }
    }
    return `${url}?${JSON.stringify(sortedObj)}`;
  } catch {
    return `${url}?${JSON.stringify(params)}`;
  }
};

/**
 * Xóa cache theo tiền tố hoặc xóa toàn bộ
 */
export const invalidateCache = (pattern) => {
  if (!pattern) {
    cache.clear();
    return;
  }
  for (const key of cache.keys()) {
    if (key.includes(pattern)) {
      cache.delete(key);
    }
  }
};

// Lưu các method gốc của axios instance
const rawGet = api.get.bind(api);
const rawPost = api.post.bind(api);
const rawPut = api.put.bind(api);
const rawPatch = api.patch ? api.patch.bind(api) : null;
const rawDelete = api.delete.bind(api);

// Bọc api.get: Cache TTL 60s cho GET suppliers/categories/products + In-flight dedupe
api.get = (url, config = {}) => {
  const cacheKey = getCacheKey(url, config.params);
  const cacheable = isCacheableUrl(url) && !config.skipCache && !config.forceRefresh;

  // 1. Kiểm tra cache đã lưu (nếu thuộc diện được cache)
  if (cacheable) {
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return Promise.resolve(cached.data);
    }
  }

  // 2. In-flight Dedupe: nếu cùng 1 request GET đang chờ phản hồi, dùng chung Promise
  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey);
  }

  // 3. Thực hiện request qua rawGet
  const promise = rawGet(url, config)
    .then((response) => {
      if (cacheable) {
        cache.set(cacheKey, { data: response, timestamp: Date.now() });
      }
      inFlightRequests.delete(cacheKey);
      return response;
    })
    .catch((error) => {
      inFlightRequests.delete(cacheKey);
      throw error;
    });

  inFlightRequests.set(cacheKey, promise);
  return promise;
};

// Tự động làm mới cache sau mọi POST/PUT/PATCH/DELETE
const handleAutoInvalidation = (url) => {
  if (typeof url !== 'string') return;
  if (url.includes('/import-notes') || url.includes('/export-notes')) {
    // import-notes / export-notes ảnh hưởng đến products, stock-ledger và reports
    invalidateCache('/products');
    invalidateCache('/stock-ledger');
    invalidateCache('/import-notes');
    invalidateCache('/export-notes');
    invalidateCache('/reports');
  } else if (url.includes('/products')) {
    invalidateCache('/products');
    invalidateCache('/stock-ledger');
    invalidateCache('/reports');
  } else if (url.includes('/categories')) {
    invalidateCache('/categories');
    invalidateCache('/products');
  } else if (url.includes('/suppliers')) {
    invalidateCache('/suppliers');
  } else if (url.includes('/stock-ledger')) {
    invalidateCache('/products');
    invalidateCache('/stock-ledger');
    invalidateCache('/reports');
  }
};

api.post = async (url, data, config) => {
  const res = await rawPost(url, data, config);
  handleAutoInvalidation(url);
  return res;
};

api.put = async (url, data, config) => {
  const res = await rawPut(url, data, config);
  handleAutoInvalidation(url);
  return res;
};

if (rawPatch) {
  api.patch = async (url, data, config) => {
    const res = await rawPatch(url, data, config);
    handleAutoInvalidation(url);
    return res;
  };
}

api.delete = async (url, config) => {
  const res = await rawDelete(url, config);
  handleAutoInvalidation(url);
  return res;
};

// Gom nhóm các dịch vụ API
export const apiClient = {
  // 1. Xác thực & Tài khoản
  auth: {
    login: (username, password) => api.post('/auth/login', { username, password }),
    getMe: () => api.get('/auth/me'),
  },

  // 2. Nhóm hàng
  categories: {
    getAll: () => api.get('/categories/'),
    create: (data) => api.post('/categories/', data),
    update: (id, data) => api.put(`/categories/${id}`, data),
    delete: (id) => api.delete(`/categories/${id}`),
  },

  // 3. Hàng hóa
  products: {
    getAll: (params) => api.get('/products/', { params }),
    getById: (id) => api.get(`/products/${id}`),
    create: (data) => api.post('/products/', data),
    update: (id, data) => api.put(`/products/${id}`, data),
    uploadImage: (id, formData) =>
      api.post(`/products/${id}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    delete: (id) => api.delete(`/products/${id}`),
  },

  // 4. Nhà cung cấp
  suppliers: {
    getAll: () => api.get('/suppliers/'),
    create: (data) => api.post('/suppliers/', data),
    update: (id, data) => api.put(`/suppliers/${id}`, data),
    delete: (id) => api.delete(`/suppliers/${id}`),
  },

  // 5. Phiếu nhập kho
  importNotes: {
    getAll: () => api.get('/import-notes/'),
    getById: (id) => api.get(`/import-notes/${id}`),
    create: (data) => api.post('/import-notes/', data),
    cancel: (id) => api.post(`/import-notes/${id}/cancel`),
  },

  // 6. Phiếu xuất kho
  exportNotes: {
    getAll: () => api.get('/export-notes/'),
    getById: (id) => api.get(`/export-notes/${id}`),
    create: (data) => api.post('/export-notes/', data),
    ship: (id) => api.post(`/export-notes/${id}/ship`),
    complete: (id) => api.post(`/export-notes/${id}/complete`),
    cancel: (id) => api.post(`/export-notes/${id}/cancel`),
    delete: (id) => api.delete(`/export-notes/${id}`),
  },

  // 7. Thẻ kho & Điều chỉnh kiểm kê
  stockLedger: {
    getAll: (params) => api.get('/stock-ledger/', { params }),
    adjust: (data) => api.post('/stock-ledger/adjust', data),
  },

  // 8. Báo cáo Nhập - Xuất - Tồn
  reports: {
    getSummary: (fromDate, toDate) =>
      api.get('/reports/inventory-summary', {
        params: { from_date: fromDate, to_date: toDate },
      }),
  },

  // 9. Trợ lý AI
  ai: {
    getMonthlyReport: (month, year, forceRefresh = false) =>
      api.get('/ai/monthly-report', { params: { month, year, force_refresh: forceRefresh } }),
    getRestockSuggestions: (lookbackDays = 30, forceRefresh = false) =>
      api.get('/ai/restock-suggestions', { params: { lookback_days: lookbackDays, force_refresh: forceRefresh } }),
    getAnomalies: (lookbackDays = 30, forceRefresh = false) =>
      api.get('/ai/anomalies', { params: { lookback_days: lookbackDays, force_refresh: forceRefresh } }),
    generateOrder: (forceRefresh = false) =>
      api.post('/ai/generate-order', null, { params: { force_refresh: forceRefresh } }),
    ask: (question, month, year, includeSmartKho = false) =>
      api.post('/ai/ask', {
        question,
        month,
        year,
        include_smartkho: includeSmartKho,
      }),
  },

  // 10. Quản trị Bộ nhớ đệm (Cache)
  cache: {
    invalidate: (pattern) => invalidateCache(pattern),
    clear: () => invalidateCache(),
  },
};

export default api;
