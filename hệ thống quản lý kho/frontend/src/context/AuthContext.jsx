import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleLogout = () => {
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
