import React, { useState, useEffect } from 'react';
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
  Moon,
  Sun,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Badge from './Badge';

export const Layout = ({ activeTab, onTabChange, children }) => {
  const { user, logout, switchDemoRole } = useAuth();

  // Quản lý trạng thái Giao diện Sáng / Tối (Theme Mode)
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('smartkho_theme') || 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    try {
      document.documentElement.setAttribute('data-theme', theme);
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    } catch (e) {
      console.error('Lỗi khi thiết lập theme:', e);
    }
  }, [theme]);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    try {
      localStorage.setItem('smartkho_theme', nextTheme);
    } catch (e) {
      console.error(e);
    }
  };

  // Tiêu đề các mục hiển thị viết hoa chữ đầu câu (Sentence case)
  const navItems = [
    { id: 'dashboard', label: 'Tổng quan', icon: LayoutDashboard },
    { id: 'products', label: 'Hàng hóa & kho', icon: Package },
    { id: 'suppliers', label: 'Nhà cung cấp', icon: Truck },
    { id: 'imports', label: 'Phiếu nhập kho', icon: ArrowDownToLine },
    { id: 'exports', label: 'Phiếu xuất kho', icon: ArrowUpFromLine },
    { id: 'stock_ledger', label: 'Thẻ kho & kiểm kê', icon: ClipboardList },
    { id: 'ai_assistant', label: 'Trợ lý AI & báo cáo', icon: Sparkles, highlight: true },
  ];

  const roleMeta = {
    ADMIN: { label: 'Quản trị viên', variant: 'purple', icon: Shield },
    WAREHOUSE_KEEPER: { label: 'Thủ kho', variant: 'wood', icon: Warehouse },
    ACCOUNTANT: { label: 'Kế toán', variant: 'green', icon: Calculator },
  };

  const currentRole = roleMeta[user?.role] || { label: user?.role, variant: 'gray', icon: UserIcon };
  const RoleIcon = currentRole.icon;

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] overflow-hidden font-sans">
      {/* 1. SIDEBAR (Tầng 2: Gỗ óc chó mun trầm, tương phản cao đạt chuẩn WCAG AA >= 7:1) */}
      <aside className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-text)] flex flex-col border-r border-[var(--sidebar-border)] shadow-lg shrink-0">
        {/* Brand Logo & Title */}
        <div className="p-5 border-b border-[var(--sidebar-border)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--sidebar-logo-bg)] border border-[var(--sidebar-logo-border)] flex items-center justify-center text-[var(--sidebar-logo-icon)] shadow-xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-serif font-bold text-[var(--sidebar-logo-text)] text-base tracking-tight flex items-center gap-1.5">
              SmartKho <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-[var(--sidebar-badge-bg)] text-[var(--sidebar-badge-text)] font-bold border border-[var(--sidebar-badge-border)]">AI</span>
            </h1>
            <p className="text-xs text-[var(--sidebar-logo-sub)] font-medium">Hệ thống quản lý kho</p>
          </div>
        </div>

        {/* Navigation Links — Độ tương phản WCAG AA cao, Active sáng hơn Hover */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-btn text-xs transition-all cursor-pointer ${
                  isActive
                    ? 'bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] font-bold shadow-xs border-l-4 border-[var(--sidebar-active-border)] pl-3'
                    : 'text-[var(--sidebar-text)] hover:text-[var(--sidebar-hover-text)] hover:bg-[var(--sidebar-hover-bg)] font-medium'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive
                        ? 'text-[var(--sidebar-active-icon)]'
                        : item.highlight
                        ? 'text-[var(--sidebar-badge-text)]'
                        : 'text-[var(--sidebar-icon)]'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.highlight && !isActive && (
                  <span className="w-2 h-2 rounded-full bg-[var(--sidebar-badge-text)] animate-pulse"></span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Card */}
        <div className="p-3.5 border-t border-[var(--sidebar-border)] bg-[var(--sidebar-user-bg)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-[var(--sidebar-logo-bg)] border border-[var(--sidebar-logo-border)] flex items-center justify-center text-[var(--sidebar-logo-icon)] shrink-0">
                <RoleIcon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-[var(--sidebar-logo-text)] truncate">{user?.full_name || user?.username}</p>
                <p className="text-xs text-[var(--sidebar-logo-sub)] truncate font-medium">{currentRole.label}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Đăng xuất"
              className="text-[var(--sidebar-text)] hover:text-[var(--semantic-alert)] p-1.5 rounded-btn hover:bg-[var(--sidebar-hover-bg)] transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* 2. MAIN CONTENT AREA (Tầng 1: Nền canvas chính) */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[var(--bg-canvas)]">
        {/* Top Header (Tầng 2: Bề mặt header) */}
        <header className="h-16 bg-[var(--bg-header)] border-b border-[var(--border-subtle)] px-6 flex items-center justify-between shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-lg font-bold text-[var(--text-primary)] tracking-tight">
              {navItems.find((i) => i.id === activeTab)?.label}
            </h2>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Quick Demo Role Switcher */}
            <div className="flex items-center gap-1 bg-[var(--bg-linen)] p-1 rounded-btn border border-[var(--border-subtle)]">
              <span className="text-xs font-semibold text-[var(--text-secondary)] pl-2 pr-1 hidden sm:inline">
                Chuyển vai trò:
              </span>
              <button
                onClick={() => switchDemoRole('ADMIN')}
                className={`text-xs px-2.5 py-1 rounded-btn font-semibold transition-all cursor-pointer ${
                  user?.role === 'ADMIN'
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-xs border border-[var(--border-medium)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Admin
              </button>
              <button
                onClick={() => switchDemoRole('WAREHOUSE_KEEPER')}
                className={`text-xs px-2.5 py-1 rounded-btn font-semibold transition-all cursor-pointer ${
                  user?.role === 'WAREHOUSE_KEEPER'
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-xs border border-[var(--border-medium)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Thủ kho
              </button>
              <button
                onClick={() => switchDemoRole('ACCOUNTANT')}
                className={`text-xs px-2.5 py-1 rounded-btn font-semibold transition-all cursor-pointer ${
                  user?.role === 'ACCOUNTANT'
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-xs border border-[var(--border-medium)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Kế toán
              </button>
            </div>

            {/* Nút chuyển đổi Giao diện Tối / Sáng theo yêu cầu */}
            <button
              onClick={toggleTheme}
              className="px-2.5 py-1.5 rounded-btn bg-[var(--bg-card)] hover:bg-[var(--bg-surface-hover)] active:bg-[var(--bg-surface-active)] border border-[var(--border-subtle)] text-[var(--text-primary)] transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
              title={theme === 'light' ? 'Chuyển sang giao diện tối' : 'Chuyển sang giao diện sáng'}
              aria-label="Đổi giao diện sáng tối"
            >
              {theme === 'light' ? (
                <Moon className="w-4 h-4 text-[var(--wood-600)] shrink-0" />
              ) : (
                <Sun className="w-4 h-4 text-[var(--wood-300)] shrink-0" />
              )}
              <span className="text-xs font-semibold hidden md:inline">
                {theme === 'light' ? 'Giao diện tối' : 'Giao diện sáng'}
              </span>
            </button>
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-[var(--bg-canvas)]">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
