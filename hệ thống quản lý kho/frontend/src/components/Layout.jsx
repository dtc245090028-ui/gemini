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
    WAREHOUSE_KEEPER: { label: 'Thủ kho', variant: 'wood', icon: Warehouse },
    ACCOUNTANT: { label: 'Kế toán', variant: 'green', icon: Calculator },
  };

  const currentRole = roleMeta[user?.role] || { label: user?.role, variant: 'gray', icon: UserIcon };
  const RoleIcon = currentRole.icon;

  return (
    <div className="flex h-screen bg-[#FAFAF7] text-charcoal overflow-hidden font-sans">
      {/* 1. SIDEBAR (Phong cách Deep Walnut Tone Gỗ Đậm Quý Phái) */}
      <aside className="w-64 bg-wood-900 text-wood-100 flex flex-col border-r border-wood-800 shadow-2xl shrink-0">
        {/* Brand */}
        <div className="p-5 border-b border-wood-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-wood-600 via-wood-500 to-wood-400 flex items-center justify-center text-wood-50 shadow-md shadow-wood-950/40">
            <Sparkles className="w-5 h-5 text-wood-50" />
          </div>
          <div>
            <h1 className="font-serif font-bold text-wood-50 text-base tracking-tight flex items-center gap-1.5">
              SmartKho <span className="font-sans text-[10px] px-1.5 py-0.5 rounded bg-wood-400/25 text-wood-300 font-semibold border border-wood-400/30">AI</span>
            </h1>
            <p className="text-[11px] text-wood-300/80">Timber & Grain Design System</p>
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
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-btn text-xs font-medium transition-all cursor-pointer ${
                  isActive
                    ? 'bg-wood-800 text-wood-50 font-semibold shadow-xs border-l-3 border-wood-400 pl-3'
                    : 'text-wood-300/90 hover:text-wood-50 hover:bg-wood-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-wood-300' : item.highlight ? 'text-wood-400' : 'text-wood-400/70'}`} />
                  <span>{item.label}</span>
                </div>
                {item.highlight && !isActive && (
                  <span className="w-2 h-2 rounded-full bg-wood-400 animate-pulse"></span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Card */}
        <div className="p-3.5 border-t border-wood-800 bg-wood-950/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-wood-800 border border-wood-700 flex items-center justify-center text-wood-200 shrink-0">
                <RoleIcon className="w-4 h-4 text-wood-300" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-wood-50 truncate">{user?.full_name || user?.username}</p>
                <p className="text-[11px] text-wood-300/80 truncate">{currentRole.label}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Đăng xuất"
              className="text-wood-400 hover:text-rust-500 p-1.5 rounded-lg hover:bg-wood-800 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* 2. MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white/90 backdrop-blur-xs border-b border-wood-200/80 px-6 flex items-center justify-between shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-lg font-bold text-wood-900 tracking-tight">
              {navItems.find((i) => i.id === activeTab)?.label}
            </h2>
          </div>

          {/* Quick Demo Role Switcher theo style ấm áp */}
          <div className="flex items-center gap-1.5 bg-wood-100 p-1 rounded-xl border border-wood-200">
            <span className="text-xs font-medium text-wood-700 pl-2 pr-1">Chuyển vai trò Demo:</span>
            <button
              onClick={() => switchDemoRole('ADMIN')}
              className={`text-xs px-2.5 py-1 rounded-btn font-medium transition-all cursor-pointer ${
                user?.role === 'ADMIN'
                  ? 'bg-white text-wood-900 shadow-xs font-bold border border-wood-300/60'
                  : 'text-wood-700 hover:text-wood-950'
              }`}
            >
              Admin
            </button>
            <button
              onClick={() => switchDemoRole('WAREHOUSE_KEEPER')}
              className={`text-xs px-2.5 py-1 rounded-btn font-medium transition-all cursor-pointer ${
                user?.role === 'WAREHOUSE_KEEPER'
                  ? 'bg-white text-wood-900 shadow-xs font-bold border border-wood-300/60'
                  : 'text-wood-700 hover:text-wood-950'
              }`}
            >
              Thủ kho
            </button>
            <button
              onClick={() => switchDemoRole('ACCOUNTANT')}
              className={`text-xs px-2.5 py-1 rounded-btn font-medium transition-all cursor-pointer ${
                user?.role === 'ACCOUNTANT'
                  ? 'bg-white text-wood-900 shadow-xs font-bold border border-wood-300/60'
                  : 'text-wood-700 hover:text-wood-950'
              }`}
            >
              Kế toán
            </button>
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#FAFAF7]">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
