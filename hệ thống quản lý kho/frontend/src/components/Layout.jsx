import React from 'react';
import {
  LayoutDashboard,
  Package,
  Truck,
  ArrowDownToLine,
  ArrowUpFromLine,
  ClipboardList,
  Sparkles,
  LogOut,
  User as UserIcon,
  Shield,
  Warehouse,
  Calculator,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Badge from './Badge';

export const Layout = ({ activeTab, onTabChange, children }) => {
  const { user, logout, switchDemoRole } = useAuth();

  const navItems = [
    { id: 'dashboard', label: 'Tổng quan', icon: LayoutDashboard },
    { id: 'products', label: 'Hàng hóa & Kho', icon: Package },
    { id: 'suppliers', label: 'Nhà cung cấp', icon: Truck },
    { id: 'imports', label: 'Phiếu nhập kho', icon: ArrowDownToLine },
    { id: 'exports', label: 'Phiếu xuất kho', icon: ArrowUpFromLine },
    { id: 'stock_ledger', label: 'Thẻ kho & Kiểm kê', icon: ClipboardList },
    { id: 'ai_assistant', label: 'Trợ lý AI & Báo cáo', icon: Sparkles, highlight: true },
  ];

  const roleMeta = {
    ADMIN: { label: 'Quản trị viên', variant: 'purple', icon: Shield },
    WAREHOUSE_KEEPER: { label: 'Thủ kho', variant: 'blue', icon: Warehouse },
    ACCOUNTANT: { label: 'Kế toán', variant: 'green', icon: Calculator },
  };

  const currentRole = roleMeta[user?.role] || { label: user?.role, variant: 'gray', icon: UserIcon };
  const RoleIcon = currentRole.icon;

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden font-sans">
      {/* 1. SIDEBAR */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 shadow-xl shrink-0">
        {/* Brand */}
        <div className="p-5 border-b border-slate-800/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-white text-base tracking-wide flex items-center gap-1.5">
              SmartKho <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">AI</span>
            </h1>
            <p className="text-xs text-slate-400">Đề tài 07 — Quản lý kho</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : item.highlight ? 'text-amber-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.highlight && !isActive && (
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Card */}
        <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                <RoleIcon className="w-4 h-4 text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white truncate">{user?.full_name || user?.username}</p>
                <p className="text-[11px] text-slate-400 truncate">{currentRole.label}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Đăng xuất"
              className="text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* 2. MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-slate-800">
              {navItems.find((i) => i.id === activeTab)?.label}
            </h2>
          </div>

          {/* Quick Demo Role Switcher */}
          <div className="flex items-center gap-2 bg-slate-100/80 p-1 rounded-xl border border-slate-200">
            <span className="text-xs font-medium text-slate-500 pl-2 pr-1">Chuyển vai trò Demo:</span>
            <button
              onClick={() => switchDemoRole('ADMIN')}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-all ${
                user?.role === 'ADMIN'
                  ? 'bg-white text-purple-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Admin
            </button>
            <button
              onClick={() => switchDemoRole('WAREHOUSE_KEEPER')}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-all ${
                user?.role === 'WAREHOUSE_KEEPER'
                  ? 'bg-white text-blue-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Thủ kho
            </button>
            <button
              onClick={() => switchDemoRole('ACCOUNTANT')}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-all ${
                user?.role === 'ACCOUNTANT'
                  ? 'bg-white text-emerald-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Kế toán
            </button>
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-50/70">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
