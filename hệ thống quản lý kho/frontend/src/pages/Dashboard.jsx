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
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-indigo-800 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Hệ Thống Quản Lý Kho Thông Minh</h2>
            <p className="text-blue-100 text-xs mt-1">
              Theo dõi tồn kho thời gian thực, giao dịch ACID và phân tích gợi ý thông minh từ Trợ lý AI.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="px-3.5 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-xs font-semibold backdrop-blur-sm flex items-center gap-2 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Làm mới số liệu</span>
            </button>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="px-4 py-2 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-500 hover:to-amber-600 text-slate-900 font-bold rounded-xl text-xs shadow-md shadow-amber-500/20 flex items-center gap-2 transition-all cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-slate-900" />
              <span>Mở Trợ lý AI</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shrink-0">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Mặt hàng quản lý</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{products.length}</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Tổng số lượng tồn: {totalStockCount.toLocaleString()} sp</p>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Dưới tồn tối thiểu</p>
            <h3 className="text-2xl font-bold text-rose-600 mt-0.5">{lowStockProducts.length}</h3>
            <p className="text-[11px] text-rose-500 mt-0.5 font-medium">Cần bổ sung khẩn cấp</p>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
            <ArrowDownToLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Phiếu nhập kho</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{importNotes.length}</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Đã ghi nhận toàn hệ thống</p>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
            <ArrowUpFromLine className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Phiếu xuất kho</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{exportNotes.length}</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Đã xuất bán & bàn giao</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Cảnh báo hàng tồn & Giao dịch mới */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Cảnh báo hàng dưới định mức (2 columns) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-rose-500" />
              <h3 className="font-bold text-slate-800 text-sm">Cảnh báo hàng sắp hết (Dưới mức tối thiểu)</h3>
            </div>
            <button
              onClick={() => onNavigate('products')}
              className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
            >
              <span>Xem tất cả</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-x-auto">
            {lowStockProducts.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                Tuyệt vời! Không có mặt hàng nào đang ở dưới mức tồn kho an toàn.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                  <tr>
                    <th className="py-3 px-4">Mã SKU</th>
                    <th className="py-3 px-4">Tên hàng hóa</th>
                    <th className="py-3 px-4 text-center">Tồn hiện tại</th>
                    <th className="py-3 px-4 text-center">Tồn an toàn</th>
                    <th className="py-3 px-4 text-right">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {lowStockProducts.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-blue-600">{p.code}</td>
                      <td className="py-3 px-4 font-medium text-slate-800">{p.name}</td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-bold text-rose-600 px-2 py-0.5 rounded bg-rose-50 border border-rose-200">
                          {p.current_stock} {p.unit}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-slate-500">{p.min_stock} {p.unit}</td>
                      <td className="py-3 px-4 text-right">
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
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-5 border border-amber-200/80 shadow-xs">
            <div className="flex items-center gap-2.5 text-amber-800 font-bold text-sm mb-2">
              <Sparkles className="w-5 h-5 text-amber-600" />
              <span>Trợ lý Kho Gemini AI</span>
            </div>
            <p className="text-xs text-amber-900/80 leading-relaxed mb-4">
              AI tự động rà soát lịch sử 60 ngày để chỉ điểm hàng bán chạy, hàng chết lâu ngày và đề xuất khối lượng nhập hàng thông minh.
            </p>
            <button
              onClick={() => onNavigate('ai_assistant')}
              className="w-full py-2 px-3 bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition-colors cursor-pointer"
            >
              <span>Trải nghiệm ngay 3 bài toán AI</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs">
            <h3 className="font-bold text-slate-800 text-sm mb-3">Thao tác kho nhanh</h3>
            <div className="space-y-2">
              <button
                onClick={() => onNavigate('imports')}
                className="w-full p-2.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-between border border-slate-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowDownToLine className="w-4 h-4 text-emerald-600" />
                  <span>Tạo Phiếu Nhập Kho Mới</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
              <button
                onClick={() => onNavigate('exports')}
                className="w-full p-2.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-between border border-slate-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ArrowUpFromLine className="w-4 h-4 text-indigo-600" />
                  <span>Tạo Phiếu Xuất Kho Mới</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
              <button
                onClick={() => onNavigate('stock_ledger')}
                className="w-full p-2.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-between border border-slate-200 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Package className="w-4 h-4 text-purple-600" />
                  <span>Tra Cứu Sổ Cái Thẻ Kho</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
