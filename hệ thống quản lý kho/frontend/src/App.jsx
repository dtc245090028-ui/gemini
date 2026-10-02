import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Products } from './pages/Products';
import { Suppliers } from './pages/Suppliers';
import { ImportNotes } from './pages/ImportNotes';
import { ExportNotes } from './pages/ExportNotes';
import { StockLedger } from './pages/StockLedger';
import { AIAssistant } from './pages/AIAssistant';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Loader } from './components/Loader';

function AppContent() {
  const { user, isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [visitedTabs, setVisitedTabs] = useState(() => new Set(['dashboard']));
  const [ledgerProductId, setLedgerProductId] = useState(null);

  // Khi đổi tài khoản đăng nhập, đưa tab về dashboard
  React.useEffect(() => {
    setActiveTab('dashboard');
    setVisitedTabs(new Set(['dashboard']));
  }, [user?.username]);

  // Khi đang kiểm tra trạng thái token lưu trữ
  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col items-center justify-center">
        <Loader variant="page" message="Đang khởi tạo hệ thống SmartKho AI..." />
      </div>
    );
  }

  // Nếu chưa đăng nhập -> Hiển thị trang đăng nhập
  if (!isAuthenticated) {
    return <Login />;
  }

  // Điều hướng từ trang Sản phẩm sang Thẻ kho chi tiết
  const handleSelectProductLedger = (productId) => {
    setLedgerProductId(productId);
    setVisitedTabs((prev) => new Set(prev).add('stock_ledger'));
    setActiveTab('stock_ledger');
  };

  // Xử lý chuyển tab thông thường (Lazy Mount & Keep-Alive giữ nguyên trạng thái)
  const handleTabChange = (tabId) => {
    if (tabId !== 'stock_ledger') {
      setLedgerProductId(null);
    }
    setVisitedTabs((prev) => new Set(prev).add(tabId));
    setActiveTab(tabId);
  };

  return (
    <Layout activeTab={activeTab} onTabChange={handleTabChange}>
      <ErrorBoundary>
        {visitedTabs.has('dashboard') && (
          <div className={activeTab === 'dashboard' ? '' : 'hidden'}>
            <Dashboard onNavigate={handleTabChange} />
          </div>
        )}
        {visitedTabs.has('products') && (
          <div className={activeTab === 'products' ? '' : 'hidden'}>
            <Products onSelectProductLedger={handleSelectProductLedger} />
          </div>
        )}
        {visitedTabs.has('suppliers') && (
          <div className={activeTab === 'suppliers' ? '' : 'hidden'}>
            <Suppliers />
          </div>
        )}
        {visitedTabs.has('imports') && (
          <div className={activeTab === 'imports' ? '' : 'hidden'}>
            <ImportNotes />
          </div>
        )}
        {visitedTabs.has('exports') && (
          <div className={activeTab === 'exports' ? '' : 'hidden'}>
            <ExportNotes />
          </div>
        )}
        {visitedTabs.has('stock_ledger') && (
          <div className={activeTab === 'stock_ledger' ? '' : 'hidden'}>
            <StockLedger
              key={ledgerProductId || 'all'}
              defaultProductId={ledgerProductId}
            />
          </div>
        )}
        {visitedTabs.has('ai_assistant') && (
          <div className={activeTab === 'ai_assistant' ? '' : 'hidden'}>
            <AIAssistant />
          </div>
        )}
      </ErrorBoundary>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
