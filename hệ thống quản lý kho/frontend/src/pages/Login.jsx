import React, { useState } from 'react';
import { Sparkles, Shield, Warehouse, Calculator, LogIn, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Loader } from '../components/Loader';

export const Login = () => {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) return;
    await login(username, password);
  };

  const handleQuickLogin = async (u, p) => {
    setUsername(u);
    setPassword(p);
    await login(u, p);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-app)] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md bg-[var(--bg-card)] rounded-card shadow-modal overflow-hidden border border-[var(--border-subtle)]">
        {/* Header Phong cách Gỗ Quý */}
        <div className="card-wood p-8 text-center text-[var(--wood-light)] relative border-b border-[var(--border-subtle)]">
          <div className="w-14 h-14 bg-white/10 backdrop-blur-md rounded-card flex items-center justify-center mx-auto mb-3 shadow-card border border-white/10">
            <Sparkles className="w-7 h-7 text-[var(--semantic-ai)]" />
          </div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--wood-light)]">SmartKho AI</h1>
          <p className="text-[var(--wood-muted)] text-xs mt-1">Đề tài 07 — Quản lý kho thông minh tích hợp AI</p>
        </div>

        {/* Body */}
        <div className="p-8 bg-[var(--bg-card)]">
          {error && (
            <div className="mb-5 p-3.5 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card flex items-center gap-2.5 text-xs text-[var(--semantic-alert)] font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5 uppercase tracking-wider">
                Tên đăng nhập
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập tên đăng nhập..."
                className="w-full px-3.5 py-2.5 input-wood text-xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5 uppercase tracking-wider">
                Mật khẩu
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu..."
                className="w-full px-3.5 py-2.5 input-wood text-xs"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 px-4 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer min-w-[140px]"
            >
              {loading ? (
                <>
                  <Loader variant="inline" />
                  <span>Đang đăng nhập...</span>
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Đăng nhập hệ thống</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access Buttons */}
          <div className="mt-8 pt-6 border-t border-[var(--border-subtle)]">
            <p className="text-center text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">
              Tài khoản mẫu Demo (Bảo vệ đồ án)
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin', 'admin123')}
                className="p-2.5 bg-[var(--bg-linen)] hover:bg-[var(--border-subtle)] border border-[var(--border-subtle)] rounded-card text-center text-xs font-medium text-[var(--text-primary)] transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Shield className="w-4 h-4 text-[var(--wood-accent)]" />
                <span>Admin</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('thukho', 'thukho123')}
                className="p-2.5 bg-[var(--bg-linen)] hover:bg-[var(--border-subtle)] border border-[var(--border-subtle)] rounded-card text-center text-xs font-medium text-[var(--text-primary)] transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Warehouse className="w-4 h-4 text-[var(--wood-accent)]" />
                <span>Thủ kho</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('ketoan', 'ketoan123')}
                className="p-2.5 bg-[var(--bg-linen)] hover:bg-[var(--border-subtle)] border border-[var(--border-subtle)] rounded-card text-center text-xs font-medium text-[var(--text-primary)] transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Calculator className="w-4 h-4 text-[var(--wood-accent)]" />
                <span>Kế toán</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
