import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Search,
  Filter,
  ArrowDownLeft,
  ArrowUpRight,
  SlidersHorizontal,
  Plus,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export const StockLedger = ({ defaultProductId }) => {
  const { user } = useAuth();
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState(defaultProductId || '');
  const [transactionType, setTransactionType] = useState('');

  // Adjustment Modal
  const [isAdjustOpen, setIsAdjustOpen] = useState(false);
  const [adjustProductId, setAdjustProductId] = useState('');
  const [actualStock, setActualStock] = useState(0);
  const [adjustNote, setAdjustNote] = useState('');
  const [adjustError, setAdjustError] = useState(null);

  const canAdjust = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';

  const fetchProducts = async () => {
    try {
      const res = await apiClient.products.getAll({ limit: 100 });
      setProducts(Array.isArray(res.data) ? res.data : (res.data.items || []));
      if (!selectedProductId && defaultProductId) {
        setSelectedProductId(defaultProductId);
      }
    } catch (err) {
      console.error('Lỗi tải sản phẩm:', err);
    }
  };

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const params = { limit: 100 };
      if (selectedProductId) params.product_id = selectedProductId;
      if (transactionType) params.transaction_type = transactionType;

      const res = await apiClient.stockLedger.getAll(params);
      setLedgerEntries(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error('Lỗi tải thẻ kho:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    fetchLedger();
  }, [selectedProductId, transactionType]);

  const handleOpenAdjust = () => {
    const firstP = products[0];
    setAdjustProductId(firstP?.id || '');
    setActualStock(firstP?.current_stock || 0);
    setAdjustNote('Kiểm kê định kỳ tháng này');
    setAdjustError(null);
    setIsAdjustOpen(true);
  };

  const handleProductSelectForAdjust = (pId) => {
    setAdjustProductId(pId);
    const p = products.find((prod) => prod.id === Number(pId));
    if (p) setActualStock(p.current_stock);
  };

  const handleAdjustSubmit = async (e) => {
    e.preventDefault();
    setAdjustError(null);
    try {
      await apiClient.stockLedger.adjust({
        product_id: Number(adjustProductId),
        actual_stock: Number(actualStock),
        note: adjustNote,
      });
      setIsAdjustOpen(false);
      fetchLedger();
      fetchProducts();
    } catch (err) {
      setAdjustError(err.response?.data?.detail || 'Không thể điều chỉnh tồn kho');
    }
  };

  const selectedProdForAdjust = products.find((p) => p.id === Number(adjustProductId));
  const diffQty = selectedProdForAdjust ? Number(actualStock) - selectedProdForAdjust.current_stock : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold font-serif text-wood-950">Sổ Cái Thẻ Kho (Stock Ledger)</h2>
          <p className="text-xs text-charcoal/70 mt-0.5">Nhật ký kiểm toán bất biến theo từng giây, truy vết biến động và số dư tức thời sau mỗi giao dịch</p>
        </div>

        {canAdjust && (
          <button
            onClick={handleOpenAdjust}
            className="btn-secondary flex items-center gap-2 text-xs"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Điều Chỉnh Kiểm Kê Kho</span>
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="card-warm p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="py-2 px-3 bg-white border border-wood-200 rounded-btn text-xs text-charcoal focus:outline-none focus:ring-2 focus:ring-wood-500/20 flex-1 max-w-sm"
          >
            <option value="">Tất cả mặt hàng</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} - {p.name} (Tồn: {p.current_stock} {p.unit})
              </option>
            ))}
          </select>

          <select
            value={transactionType}
            onChange={(e) => setTransactionType(e.target.value)}
            className="py-2 px-3 bg-white border border-wood-200 rounded-btn text-xs text-charcoal focus:outline-none focus:ring-2 focus:ring-wood-500/20"
          >
            <option value="">Tất cả loại giao dịch</option>
            <option value="IMPORT">Nhập kho (IMPORT)</option>
            <option value="EXPORT">Xuất kho (EXPORT)</option>
            <option value="ADJUSTMENT">Điều chỉnh kiểm kê (ADJUSTMENT)</option>
          </select>
        </div>

        <button
          onClick={fetchLedger}
          className="p-2 text-wood-600 hover:text-wood-900 hover:bg-wood-100 rounded-btn transition-colors cursor-pointer"
          title="Làm mới sổ cái"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Ledger Table */}
      <div className="card-warm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Mã SKU</th>
                <th className="py-3 px-4">Tên hàng hóa</th>
                <th className="py-3 px-4 text-center">Loại nghiệp vụ</th>
                <th className="py-3 px-4">Mã chứng từ</th>
                <th className="py-3 px-4 text-center">Biến động</th>
                <th className="py-3 px-4 text-center font-bold">Tồn sau giao dịch</th>
                <th className="py-3 px-4">Người thực hiện</th>
                <th className="py-3 px-4">Ghi chú</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-wood-100 font-sans">
              {loading ? (
                <tr>
                  <td colSpan="9" className="text-center py-10 text-charcoal/40">
                    Đang tải lịch sử thẻ kho...
                  </td>
                </tr>
              ) : ledgerEntries.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center py-10 text-charcoal/40">
                    Chưa ghi nhận biến động nào trong thẻ kho.
                  </td>
                </tr>
              ) : (
                ledgerEntries.map((l) => {
                  const isPositive = l.quantity_change > 0;
                  return (
                    <tr key={l.id} className="hover:bg-wood-50/70 transition-colors">
                      <td className="py-3.5 px-4 text-charcoal/70 font-mono">
                        {new Date(l.transaction_date).toLocaleString('vi-VN')}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold text-wood-700">{l.product?.code}</td>
                      <td className="py-3.5 px-4 font-medium text-wood-950">{l.product?.name}</td>
                      <td className="py-3.5 px-4 text-center">
                        <Badge
                          variant={
                            l.transaction_type === 'IMPORT'
                              ? 'forest'
                              : l.transaction_type === 'EXPORT'
                              ? 'wood'
                              : 'amber'
                          }
                        >
                          {l.transaction_type === 'IMPORT'
                            ? 'Nhập kho'
                            : l.transaction_type === 'EXPORT'
                            ? 'Xuất kho'
                            : 'Kiểm kê bù trừ'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-charcoal/80 font-medium">{l.reference_code}</td>
                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`font-bold px-2 py-0.5 rounded ${
                            isPositive
                              ? 'bg-forest-50 text-forest-700'
                              : 'bg-rust-50 text-rust-700'
                          }`}
                        >
                          {isPositive ? `+${l.quantity_change}` : l.quantity_change}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="font-bold text-wood-900 bg-wood-100 px-2.5 py-1 rounded-btn border border-wood-200">
                          {l.balance_after}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-charcoal/80">{l.creator?.full_name || 'Hệ thống'}</td>
                      <td className="py-3.5 px-4 text-charcoal/60 max-w-xs truncate">{l.note || '-'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Điều Chỉnh Kiểm Kê */}
      <Modal isOpen={isAdjustOpen} onClose={() => setIsAdjustOpen(false)} title="Điều Chỉnh Tồn Kho Sau Kiểm Kê Thực Tế">
        {adjustError && (
          <div className="mb-4 p-3 bg-rust-50 border border-rust-200 rounded-btn flex items-center gap-2 text-xs text-rust-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rust-600" />
            <span>{adjustError}</span>
          </div>
        )}

        <form onSubmit={handleAdjustSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">Mặt hàng kiểm kê</label>
            <select
              value={adjustProductId}
              onChange={(e) => handleProductSelectForAdjust(e.target.value)}
              className="w-full input-wood text-xs"
              required
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} - {p.name} (Tồn trên sổ sách: {p.current_stock})
                </option>
              ))}
            </select>
          </div>

          <div className="p-3 bg-wood-50 border border-wood-200 rounded-btn text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-charcoal/70">Tồn kho trên hệ thống:</span>
              <strong className="text-wood-950">{selectedProdForAdjust?.current_stock || 0}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-charcoal/70">Chênh lệch bù trừ:</span>
              <strong className={diffQty >= 0 ? 'text-forest-700' : 'text-rust-700'}>
                {diffQty >= 0 ? `+${diffQty}` : diffQty}
              </strong>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">Số lượng đếm thực tế tại kho</label>
            <input
              type="number"
              min="0"
              value={actualStock}
              onChange={(e) => setActualStock(e.target.value)}
              className="w-full input-wood text-xs font-bold text-wood-800"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">Lý do điều chỉnh kiểm kê</label>
            <input
              type="text"
              value={adjustNote}
              onChange={(e) => setAdjustNote(e.target.value)}
              placeholder="VD: Hao hụt tự nhiên, kiểm kê cuối tháng..."
              className="w-full input-wood text-xs"
              required
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-wood-200">
            <button
              type="button"
              onClick={() => setIsAdjustOpen(false)}
              className="btn-ghost text-xs"
            >
              Hủy
            </button>
            <button
              type="submit"
              className="btn-primary text-xs"
            >
              Cập Nhật Tồn Kho
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default StockLedger;
