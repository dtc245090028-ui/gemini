import React, { useState, useEffect } from 'react';
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

export const Dashboard = ({ onNavigate }) => {
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [importNotes, setImportNotes] = useState([]);
  const [exportNotes, setExportNotes] = useState([]);
  const [lowStockProducts, setLowStockProducts] = useState([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prodRes, impRes, expRes, lowRes] = await Promise.all([
        apiClient.products.getAll({ limit: 100 }),
        apiClient.importNotes.getAll(),
        apiClient.exportNotes.getAll(),
        apiClient.products.getAll({ is_low_stock: true }),
      ]);
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
      setImportNotes(Array.isArray(impRes.data) ? impRes.data : (impRes.data.items || []));
      setExportNotes(Array.isArray(expRes.data) ? expRes.data : (expRes.data.items || []));
      setLowStockProducts(Array.isArray(lowRes.data) ? lowRes.data : (lowRes.data.items || []));
    } catch (err) {
      console.error('Lỗi khi tải dữ liệu dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalStockCount = products.reduce((acc, p) => acc + (p.current_stock || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top Banner Phong cách Gỗ Quý Deep Walnut & Amber */}
      <div className="bg-gradient-to-r from-wood-900 via-wood-800 to-wood-700 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden border border-wood-700/60">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-semibold text-wood-300 tracking-wider uppercase">
              Bảng điều khiển trung tâm
            </span>
            <h2 className="font-serif text-2xl font-bold tracking-tight text-wood-50 mt-0.5">
              Hệ Thống Quản Lý Kho Thông Minh
            </h2>
            <p className="text-wood-200/90 text-xs mt-1 max-w-2xl">
              Theo dõi tồn kho thời gian thực, giao dịch kho ACID và dự toán tái nhập hàng thông minh bằng Trợ lý AI.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="px-3.5 py-2 bg-white/10 hover:bg-white/20 border border-wood-400/30 rounded-btn text-xs font-semibold backdrop-blur-xs flex items-center gap-2 transition-colors cursor-pointer text-wood-100"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Làm mới số liệu</span>
            </button>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="px-4 py-2 bg-wood-400 hover:bg-wood-300 active:bg-wood-500 text-wood-950 font-bold rounded-btn text-xs shadow-md shadow-wood-950/30 flex items-center gap-2 transition-all cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-wood-950" />
              <span>Mở Trợ lý AI</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Theo Palette Wood-Tone */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1 */}
        <div className="card-wood p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-wood-100 border border-wood-200 flex items-center justify-center text-wood-700 shrink-0">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-wood-600">Mặt hàng quản lý</p>
            <h3 className="font-serif text-2xl font-bold text-wood-900 mt-0.5">{products.length}</h3>
            <p className="text-[11px] text-wood-500 mt-0.5">Tổng lượng tồn: {totalStockCount.toLocaleString()} sp</p>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="card-wood p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-rust-50 border border-rust-200 flex items-center justify-center text-rust-500 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-wood-600">Dưới tồn tối thiểu</p>
            <h3 className="font-serif text-2xl font-bold text-rust-500 mt-0.5">{lowStockProducts.length}</h3>
            <p className="text-[11px] text-rust-600 mt-0.5 font-medium">Cần bổ sung kho</p>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="card-wood p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-forest-50 border border-forest-200 flex items-center justify-center text-forest-500 shrink-0">
            <ArrowDownToLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-wood-600">Phiếu nhập kho</p>
            <h3 className="font-serif text-2xl font-bold text-wood-900 mt-0.5">{importNotes.length}</h3>
            <p className="text-[11px] text-wood-500 mt-0.5">Đã ghi nhận toàn kho</p>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="card-wood p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-wood-50 border border-wood-300 flex items-center justify-center text-wood-600 shrink-0">
            <ArrowUpFromLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-wood-600">Phiếu xuất kho</p>
            <h3 className="font-serif text-2xl font-bold text-wood-900 mt-0.5">{exportNotes.length}</h3>
            <p className="text-[11px] text-wood-500 mt-0.5">Đã xuất bán & bàn giao</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Cảnh báo hàng tồn & Giao dịch mới */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Cảnh báo hàng dưới định mức (2 columns) */}
        <div className="lg:col-span-2 card-wood overflow-hidden flex flex-col">
          <div className="p-5 border-b border-wood-200/80 bg-wood-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-rust-500" />
              <h3 className="font-serif font-bold text-wood-900 text-sm">
                Cảnh báo hàng sắp hết (Dưới mức an toàn)
              </h3>
            </div>
            <button
              onClick={() => onNavigate('products')}
              className="text-xs font-semibold text-wood-600 hover:text-wood-800 flex items-center gap-1 cursor-pointer"
            >
              <span>Xem tất cả</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-x-auto">
            {loading ? (
              <div className="p-8 text-center text-xs text-wood-400">Đang đồng bộ dữ liệu kho...</div>
            ) : lowStockProducts.length === 0 ? (
              <div className="p-10 text-center text-xs text-wood-500">
                Tuyệt vời! Không có mặt hàng nào đang ở dưới mức tồn kho an toàn.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
                  <tr>
                    <th className="py-3 px-4">Hàng hóa</th>
                    <th className="py-3 px-4 text-center">Tồn hiện tại</th>
                    <th className="py-3 px-4 text-center">Tồn an toàn</th>
                    <th className="py-3 px-4 text-right">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-wood-100">
                  {lowStockProducts.map((p) => (
                    <tr key={p.id} className="hover:bg-wood-50/80 transition-colors">
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-wood-100 border border-wood-200 overflow-hidden flex items-center justify-center shrink-0">
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
                            <Package className="w-4 h-4 text-wood-400" style={{ display: p.image_url ? 'none' : 'block' }} />
                          </div>
                          <div>
                            <p className="font-medium text-wood-900 leading-tight">{p.name}</p>
                            <span className="font-mono text-[10px] text-wood-500">{p.code}</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        <span className="font-bold text-rust-600 px-2 py-0.5 rounded bg-rust-50 border border-rust-200">
                          {p.current_stock} {p.unit}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-center text-wood-600">{p.min_stock} {p.unit}</td>
                      <td className="py-2.5 px-4 text-right">
                        <Badge variant={p.current_stock === 0 ? 'red' : 'amber'}>
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
          {/* Quick AI Card */}
          <div className="bg-gradient-to-br from-wood-50 to-wood-100 rounded-2xl p-5 border border-wood-200/90 shadow-xs">
            <div className="flex items-center gap-2.5 text-wood-900 font-serif font-bold text-sm mb-2">
              <Sparkles className="w-5 h-5 text-wood-500" />
              <span>Trợ lý Kho Gemini AI</span>
            </div>
            <p className="text-xs text-wood-800/80 leading-relaxed mb-4">
              AI tự động rà soát lịch sử 60 ngày để chỉ điểm hàng bán chạy, hàng chết lâu ngày và đề xuất khối lượng nhập hàng thông minh.
            </p>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="btn-primary w-full text-xs font-bold"
            >
              <span>Trải nghiệm ngay 3 bài toán AI</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Actions */}
          <div className="card-wood p-5">
            <h3 className="font-serif font-bold text-wood-900 text-sm mb-3">Thao tác kho nhanh</h3>
            <div className="space-y-2">
              <button
                onClick={() => onNavigate('imports')}
                className="w-full p-2.5 bg-wood-50/70 hover:bg-wood-100 rounded-btn text-xs font-semibold text-wood-800 flex items-center justify-between border border-wood-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowDownToLine className="w-4 h-4 text-forest-500" />
                  <span>Tạo Phiếu Nhập Kho Mới</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-wood-400" />
              </button>
              <button
                onClick={() => onNavigate('exports')}
                className="w-full p-2.5 bg-wood-50/70 hover:bg-wood-100 rounded-btn text-xs font-semibold text-wood-800 flex items-center justify-between border border-wood-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowUpFromLine className="w-4 h-4 text-wood-600" />
                  <span>Tạo Phiếu Xuất Kho Mới</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-wood-400" />
              </button>
              <button
                onClick={() => onNavigate('stock_ledger')}
                className="w-full p-2.5 bg-wood-50/70 hover:bg-wood-100 rounded-btn text-xs font-semibold text-wood-800 flex items-center justify-between border border-wood-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Package className="w-4 h-4 text-wood-500" />
                  <span>Tra Cứu Sổ Cái Thẻ Kho</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-wood-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
