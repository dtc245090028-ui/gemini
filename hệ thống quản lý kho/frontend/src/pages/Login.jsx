import React, { useState } from 'react';
import { Sparkles, Shield, Warehouse, Calculator, LogIn, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

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
    <div className="min-h-screen bg-gradient-to-br from-wood-950 via-wood-900 to-wood-800 flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden border border-wood-200/80">
        {/* Header Phong cách Gỗ Quý */}
        <div className="bg-gradient-to-r from-wood-900 via-wood-800 to-wood-700 p-8 text-center text-white relative">
          <div className="w-14 h-14 bg-wood-400/20 backdrop-blur-md rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-lg border border-wood-400/30">
            <Sparkles className="w-7 h-7 text-wood-300" />
          </div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-wood-50">SmartKho AI</h1>
          <p className="text-wood-200 text-xs mt-1">Đề tài 07 — Quản Lý Kho Thông Minh Tích Hợp AI</p>
        </div>

        {/* Body */}
        <div className="p-8 bg-[#FAFAF7]">
          {error && (
            <div className="mb-5 p-3.5 bg-rust-50 border border-rust-200 rounded-xl flex items-center gap-2.5 text-xs text-rust-700">
              <AlertCircle className="w-4 h-4 shrink-0 text-rust-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-wood-900 mb-1.5 uppercase tracking-wider">
                Tên đăng nhập
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập tên đăng nhập..."
                className="w-full px-3.5 py-2.5 bg-white border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20 focus:border-wood-500 transition-all placeholder:text-wood-400"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-wood-900 mb-1.5 uppercase tracking-wider">
                Mật khẩu
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu..."
                className="w-full px-3.5 py-2.5 bg-white border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20 focus:border-wood-500 transition-all placeholder:text-wood-400"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-wood-500 hover:bg-wood-600 active:bg-wood-700 text-wood-50 rounded-btn text-xs font-bold shadow-md shadow-wood-900/10 flex items-center justify-center gap-2 transition-all disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Đăng nhập hệ thống</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access Buttons */}
          <div className="mt-8 pt-6 border-t border-wood-200">
            <p className="text-center text-[11px] font-semibold text-wood-600 uppercase tracking-wider mb-3">
              Tài khoản mẫu Demo (Bảo vệ đồ án)
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin', 'admin123')}
                className="p-2.5 bg-wood-100 hover:bg-wood-200/80 border border-wood-200 rounded-xl text-center text-xs font-medium text-wood-900 transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Shield className="w-4 h-4 text-wood-700" />
                <span>Admin</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('thukho', 'thukho123')}
                className="p-2.5 bg-wood-100 hover:bg-wood-200/80 border border-wood-200 rounded-xl text-center text-xs font-medium text-wood-900 transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Warehouse className="w-4 h-4 text-wood-700" />
                <span>Thủ kho</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('ketoan', 'ketoan123')}
                className="p-2.5 bg-wood-100 hover:bg-wood-200/80 border border-wood-200 rounded-xl text-center text-xs font-medium text-wood-900 transition-colors flex flex-col items-center gap-1 cursor-pointer"
              >
                <Calculator className="w-4 h-4 text-wood-700" />
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
