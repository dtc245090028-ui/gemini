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
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [ledgerProductId, setLedgerProductId] = useState(null);

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
    setActiveTab('stock_ledger');
  };

  // Xử lý chuyển tab thông thường
  const handleTabChange = (tabId) => {
    if (tabId !== 'stock_ledger') {
      setLedgerProductId(null);
    }
    setActiveTab(tabId);
  };

  return (
    <Layout activeTab={activeTab} onTabChange={handleTabChange}>
      <ErrorBoundary key={activeTab}>
        {activeTab === 'dashboard' && <Dashboard onNavigate={handleTabChange} />}
        {activeTab === 'products' && (
          <Products onSelectProductLedger={handleSelectProductLedger} />
        )}
        {activeTab === 'suppliers' && <Suppliers />}
        {activeTab === 'imports' && <ImportNotes />}
        {activeTab === 'exports' && <ExportNotes />}
        {activeTab === 'stock_ledger' && (
          <StockLedger
            key={ledgerProductId || 'all'}
            defaultProductId={ledgerProductId}
          />
        )}
        {activeTab === 'ai_assistant' && <AIAssistant />}
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
