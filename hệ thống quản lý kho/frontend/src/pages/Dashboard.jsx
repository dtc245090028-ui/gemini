import React, { useState, useEffect, useRef } from 'react';
import { stockEvents } from '../utils/stockEvents';
import { usePageSync } from '../hooks/usePageSync';
import {
  Package,
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  Sparkles,
  RefreshCw,
  TrendingDown,
  ArrowRight,
} from 'lucide-react';
import { apiClient } from '../api/client';
import Badge from '../components/Badge';
import { useDelayedLoading } from '../hooks/useDelayedLoading';
import { Loader } from '../components/Loader';

export const Dashboard = ({ onNavigate, isActive = true }) => {
  const [loading, setLoading] = useState(true);
  const isStaleRef = useRef(false);
  const showLoader = useDelayedLoading(loading);
  const [lowStockProducts, setLowStockProducts] = useState([]);
  const [kpiStats, setKpiStats] = useState({
    total_products: 0,
    total_stock: 0,
    low_stock_count: 0,
    total_import_notes: 0,
    total_export_notes: 0,
  });

  const loadData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [kpiRes, lowRes] = await Promise.all([
        apiClient.reports.getKpiSummary(),
        apiClient.reports.getLowStockAlerts(),
      ]);
      if (kpiRes && kpiRes.data) {
        setKpiStats(kpiRes.data);
      }
      setLowStockProducts(Array.isArray(lowRes.data) ? lowRes.data : (lowRes.data.items || []));
    } catch (err) {
      console.error('Lỗi khi tải dữ liệu dashboard:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Tự động đồng bộ chuẩn mực theo trang: Debounce, MaxWait, Single-Flight, Sparse Polling
  usePageSync({
    fetchFn: loadData,
    isActive,
    resource: 'reports',
  });

  // KPI Stats được đồng bộ trực tiếp từ backend kpi-summary

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[var(--wood-900)] border border-[var(--wood-700)] rounded-card p-4 sm:p-6 text-[var(--wood-50)] shadow-md relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="min-w-0">
            <span className="text-xs font-semibold text-[var(--wood-300)] tracking-wider uppercase">
              Bảng điều khiển trung tâm
            </span>
            <h2 className="font-serif text-xl sm:text-2xl font-bold tracking-tight text-[var(--wood-50)] mt-0.5">
              Hệ thống quản lý kho thông minh
            </h2>
            <p className="text-[var(--wood-200)] text-xs mt-1 max-w-2xl leading-relaxed">
              Theo dõi tồn kho thời gian thực, giao dịch kho ACID và dự toán tái nhập hàng thông minh bằng Trợ lý AI.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={loadData}
              className="px-3.5 py-2 bg-[var(--wood-800)] hover:bg-[var(--wood-700)] border border-[var(--wood-700)] rounded-btn text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer text-[var(--wood-50)]"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Làm mới số liệu</span>
            </button>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="btn-ai"
            >
              <Sparkles className="w-4 h-4" />
              <span>Mở trợ lý AI</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Theo Design Tokens "Timber & Grain" */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1 */}
        <div className="card-wood p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-input bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] flex items-center justify-center text-[var(--wood-500)] shrink-0 shadow-xs">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-[var(--text-secondary)]">Mặt hàng quản lý</p>
            <h3 className="font-serif text-2xl font-bold text-[var(--text-primary)] mt-0.5">{kpiStats.total_products}</h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Tổng tồn: <strong className="font-mono text-[var(--text-primary)]">{(kpiStats.total_stock || 0).toLocaleString()}</strong> sp</p>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="card-wood p-5 flex items-center gap-4 border-l-4 border-l-[var(--semantic-alert)]">
          <div className="w-12 h-12 rounded-input bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] flex items-center justify-center text-[var(--semantic-alert)] shrink-0 shadow-xs">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-[var(--text-secondary)]">Dưới tồn tối thiểu</p>
            <h3 className="font-serif text-2xl font-bold text-[var(--semantic-alert)] mt-0.5">{kpiStats.low_stock_count}</h3>
            <p className="text-xs text-[var(--semantic-alert)] mt-0.5 font-semibold">Cần bổ sung kho</p>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="card-wood p-5 flex items-center gap-4 border-l-4 border-l-[var(--semantic-success)]">
          <div className="w-12 h-12 rounded-input bg-[var(--semantic-success-bg)] border border-[var(--semantic-success-border)] flex items-center justify-center text-[var(--semantic-success)] shrink-0 shadow-xs">
            <ArrowDownToLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-[var(--text-secondary)]">Phiếu nhập kho</p>
            <h3 className="font-serif text-2xl font-bold text-[var(--text-primary)] mt-0.5">{kpiStats.total_import_notes}</h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Đã ghi nhận toàn kho</p>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="card-wood p-5 flex items-center gap-4 border-l-4 border-l-[var(--wood-400)]">
          <div className="w-12 h-12 rounded-input bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] flex items-center justify-center text-[var(--wood-500)] shrink-0 shadow-xs">
            <ArrowUpFromLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-[var(--text-secondary)]">Phiếu xuất kho</p>
            <h3 className="font-serif text-2xl font-bold text-[var(--text-primary)] mt-0.5">{kpiStats.total_export_notes}</h3>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Đã xuất bán & bàn giao</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Cảnh báo hàng tồn & Giao dịch mới */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Cảnh báo hàng dưới định mức (2 columns) */}
        <div className="lg:col-span-2 card-wood overflow-hidden flex flex-col">
          <div className="p-4 border-b border-[var(--border-medium)] bg-[var(--bg-surface-warm)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-[var(--semantic-alert)]" />
              <h3 className="font-serif font-bold text-[var(--text-primary)] text-sm">
                Cảnh báo hàng sắp hết (dưới mức an toàn)
              </h3>
            </div>
            <button
              onClick={() => onNavigate('products')}
              className="text-xs font-semibold text-[var(--wood-500)] hover:text-[var(--wood-600)] flex items-center gap-1 cursor-pointer"
            >
              <span>Xem tất cả</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-x-auto">
            {showLoader ? (
              <table className="w-full text-left text-xs">
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  <Loader variant="table" columns={4} rows={5} />
                </tbody>
              </table>
            ) : lowStockProducts.length === 0 ? (
              <div className="p-10 text-center text-xs text-[var(--text-secondary)]">
                Không có mặt hàng nào đang ở dưới mức tồn kho an toàn.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-medium)]">
                  <tr>
                    <th className="py-3 px-4">Hàng hóa</th>
                    <th className="py-3 px-4 text-center">Tồn hiện tại</th>
                    <th className="py-3 px-4 text-center">Tồn an toàn</th>
                    <th className="py-3 px-4 text-right">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)] font-sans">
                  {lowStockProducts.map((p) => (
                    <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-input bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] overflow-hidden flex items-center justify-center shrink-0">
                            {p.image_url ? (
                              <img
                                src={p.image_url}
                                alt={p.name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                  if (e.currentTarget.nextSibling) e.currentTarget.nextSibling.style.display = 'flex';
                                }}
                              />
                            ) : null}
                            <Package className="w-4 h-4 text-[var(--text-muted)]" style={{ display: p.image_url ? 'none' : 'block' }} />
                          </div>
                          <div>
                            <p className="font-medium text-[var(--text-primary)] leading-tight">{p.name}</p>
                            <span className="font-mono text-xs text-[var(--text-secondary)]">{p.code}</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        <span className="font-mono text-xs font-bold text-[var(--semantic-alert)] px-2 py-0.5 rounded-sm bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)]">
                          {p.current_stock} {p.unit}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-center font-mono text-xs text-[var(--text-secondary)]">
                        {p.min_stock} {p.unit}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <Badge variant={p.current_stock === 0 ? 'alert' : 'amber'}>
                          {p.current_stock === 0 ? 'Hết hàng' : 'Sắp hết hàng'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: Thao tác nhanh & Giới thiệu AI */}
        <div className="space-y-6">
          {/* Quick AI Card — Phong cách Hổ phách mật ong */}
          <div className="bg-[var(--semantic-ai-bg)] rounded-card p-5 border border-[var(--semantic-ai-border)] shadow-xs">
            <div className="flex items-center gap-2.5 text-[var(--semantic-ai)] font-serif font-bold text-sm mb-2">
              <Sparkles className="w-4 h-4 text-[var(--semantic-ai-btn)]" />
              <span>Trợ lý kho Gemini AI</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-4">
              AI tự động rà soát lịch sử 60 ngày để chỉ điểm hàng bán chạy, hàng tồn lâu ngày và đề xuất khối lượng nhập hàng thông minh.
            </p>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="btn-ai w-full justify-between"
            >
              <span>Trải nghiệm 3 bài toán AI</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Actions */}
          <div className="card-wood p-5">
            <h3 className="font-serif font-bold text-[var(--text-primary)] text-sm mb-3">Thao tác kho nhanh</h3>
            <div className="space-y-2">
              <button
                onClick={() => onNavigate('imports')}
                className="w-full p-2.5 bg-[var(--bg-surface-warm)] hover:bg-[var(--bg-surface-hover)] rounded-btn text-xs font-semibold text-[var(--text-primary)] flex items-center justify-between border border-[var(--border-medium)] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowDownToLine className="w-4 h-4 text-[var(--semantic-success)]" />
                  <span>Tạo phiếu nhập kho</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              </button>
              <button
                onClick={() => onNavigate('exports')}
                className="w-full p-2.5 bg-[var(--bg-surface-warm)] hover:bg-[var(--bg-surface-hover)] rounded-btn text-xs font-semibold text-[var(--text-primary)] flex items-center justify-between border border-[var(--border-medium)] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowUpFromLine className="w-4 h-4 text-[var(--wood-500)]" />
                  <span>Tạo phiếu xuất kho</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              </button>
              <button
                onClick={() => onNavigate('stock_ledger')}
                className="w-full p-2.5 bg-[var(--bg-surface-warm)] hover:bg-[var(--bg-surface-hover)] rounded-btn text-xs font-semibold text-[var(--text-primary)] flex items-center justify-between border border-[var(--border-medium)] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Package className="w-4 h-4 text-[var(--wood-400)]" />
                  <span>Tra cứu sổ cái thẻ kho</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
