import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient, invalidateCache } from '../api/client';
import { draftStorage } from '../utils/draftStorage';

const AuthContext = createContext(null);

/**
 * Giải mã payload JWT bằng atob để kiểm tra thời hạn exp.
 * Trả về true nếu token không hợp lệ hoặc đã hết hạn.
 */
const isTokenExpired = (jwtToken) => {
  if (!jwtToken || typeof jwtToken !== 'string') return true;
  try {
    const parts = jwtToken.split('.');
    if (parts.length !== 3) return true;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    const payload = JSON.parse(atob(padded));
    if (!payload.exp) return false;
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => {
    const savedToken = localStorage.getItem('token');
    if (!savedToken) return null;
    if (isTokenExpired(savedToken)) {
      invalidateCache();
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      return null;
    }
    return savedToken;
  });

  const [user, setUser] = useState(() => {
    const savedToken = localStorage.getItem('token');
    if (!savedToken || isTokenExpired(savedToken)) {
      return null;
    }
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Tự động dọn dẹp các bản nháp đã quá 24h khi khởi động ứng dụng
    draftStorage.cleanupExpired();

    // Kiểm tra lại hạn JWT khi mở web
    const currentToken = localStorage.getItem('token');
    if (currentToken && isTokenExpired(currentToken)) {
      invalidateCache();
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setUser(null);
      setToken(null);
    }

    const handleLogout = () => {
      invalidateCache();
      setUser(null);
      setToken(null);
    };
    window.addEventListener('auth-logout', handleLogout);
    return () => window.removeEventListener('auth-logout', handleLogout);
  }, []);

  const login = async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      invalidateCache();
      const res = await apiClient.auth.login(username, password);
      const accessToken = res.data.access_token;
      setToken(accessToken);
      localStorage.setItem('token', accessToken);

      // Lấy thông tin user hiện tại
      const meRes = await apiClient.auth.getMe();
      const userData = meRes.data;
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      return { success: true };
    } catch (err) {
      const msg = err.response?.data?.detail || 'Đăng nhập không thành công';
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  };

  // Nút chuyển đổi vai trò nhanh dành riêng cho mục đích Demo đồ án
  const switchDemoRole = async (targetRole) => {
    const credentials = {
      ADMIN: { u: 'admin', p: 'admin123' },
      WAREHOUSE_KEEPER: { u: 'thukho', p: 'thukho123' },
      ACCOUNTANT: { u: 'ketoan', p: 'ketoan123' },
    };
    const cred = credentials[targetRole];
    if (cred) {
      return await login(cred.u, cred.p);
    }
  };

  const logout = () => {
    invalidateCache();
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        error,
        login,
        logout,
        switchDemoRole,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
