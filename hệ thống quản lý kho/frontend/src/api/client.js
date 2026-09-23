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
    cancel: (id) => api.post(`/export-notes/${id}/cancel`),
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
    getMonthlyReport: (month, year) =>
      api.get('/ai/monthly-report', { params: { month, year } }),
    getRestockSuggestions: (lookbackDays = 30) =>
      api.get('/ai/restock-suggestions', { params: { lookback_days: lookbackDays } }),
    getAnomalies: (lookbackDays = 30) =>
      api.get('/ai/anomalies', { params: { lookback_days: lookbackDays } }),
  },
};

export default api;
