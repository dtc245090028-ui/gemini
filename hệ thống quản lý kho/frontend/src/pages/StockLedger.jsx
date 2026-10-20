import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  Calendar,
  Download,
  FileSpreadsheet,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { draftStorage } from '../utils/draftStorage';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import ProductSelect from '../components/ProductSelect';
import Loader from '../components/Loader';
import useDelayedLoading from '../hooks/useDelayedLoading';

const getTodayLocalStr = () => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

const formatRangePreview = (period, dateStr) => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  if (!y || !m || !d) return '';

  const fmt = (dt) =>
    `${String(dt.getDate()).padStart(2, '0')}/${String(dt.getMonth() + 1).padStart(2, '0')}/${dt.getFullYear()}`;

  if (period === 'day') {
    const cur = new Date(y, m - 1, d);
    return `Ngày ${fmt(cur)} (00:00 – 23:59)`;
  }
  if (period === 'week') {
    const cur = new Date(y, m - 1, d);
    const dayOfWeek = cur.getDay(); // 0 (CN) -> 6 (T7)
    const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    const monday = new Date(y, m - 1, d + diffToMonday);
    const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6);
    return `Tuần từ ${fmt(monday)} đến ${fmt(sunday)} (Thứ Hai – Chủ Nhật)`;
  }
  if (period === 'month') {
    const firstDay = new Date(y, m - 1, 1);
    const lastDay = new Date(y, m, 0);
    return `Tháng ${String(m).padStart(2, '0')}/${y} (${fmt(firstDay)} – ${fmt(lastDay)})`;
  }
  return '';
};

export const StockLedger = ({ defaultProductId }) => {
  const { user } = useAuth();
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const showTableLoader = useDelayedLoading(loading);
  const [selectedProductId, setSelectedProductId] = useState(defaultProductId || '');
  const [transactionType, setTransactionType] = useState('');

  // Excel Export Modal
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [exportPeriod, setExportPeriod] = useState('day');
  const [exportDate, setExportDate] = useState(getTodayLocalStr);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  // Adjustment Modal
  const [isAdjustOpen, setIsAdjustOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [adjustProductId, setAdjustProductId] = useState('');
  const [actualStock, setActualStock] = useState(0);
  const [adjustNote, setAdjustNote] = useState('');
  const [adjustError, setAdjustError] = useState(null);
  const [isDraftRestored, setIsDraftRestored] = useState(false);
  const [draftSavedTime, setDraftSavedTime] = useState('');

  const canAdjust = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';

  const handleOpenExportModal = () => {
    setExportPeriod('day');
    setExportDate(getTodayLocalStr());
    setExportError(null);
    setIsExportOpen(true);
  };

  const handleExportExcel = async (e) => {
    e.preventDefault();
    setExportError(null);
    setIsExporting(true);
    try {
      const params = {
        period: exportPeriod,
        target_date: exportDate || getTodayLocalStr(),
      };
      if (selectedProductId) {
        params.product_id = Number(selectedProductId);
      }

      const res = await apiClient.stockLedger.exportExcel(params);
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      let filename = `the_kho_${exportPeriod}_${(exportDate || getTodayLocalStr()).replace(/-/g, '')}.xlsx`;
      const disposition = res.headers?.['content-disposition'];
      if (disposition) {
        const match = disposition.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setIsExportOpen(false);
    } catch (err) {
      setExportError('Không thể xuất file Excel. Vui lòng kiểm tra lại thời gian chọn hoặc thử lại.');
    } finally {
      setIsExporting(false);
    }
  };

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
    // Kiểm tra xem có bản nháp kiểm kê bù trừ trong vòng 24h không
    const draft = draftStorage.load(user?.username, 'stock_adjust');
    if (draft && draft.data) {
      setAdjustProductId(draft.data.adjustProductId || products[0]?.id || '');
      setActualStock(draft.data.actualStock !== undefined ? draft.data.actualStock : (products[0]?.current_stock || 0));
      setAdjustNote(draft.data.adjustNote || 'Kiểm kê định kỳ tháng này');
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      const firstP = products[0];
      setAdjustProductId(firstP?.id || '');
      setActualStock(firstP?.current_stock || 0);
      setAdjustNote('Kiểm kê định kỳ tháng này');
      setIsDraftRestored(false);
      setDraftSavedTime('');
    }
    setAdjustError(null);
    setIsAdjustOpen(true);
  };

  // Tự động lưu bản nháp kiểm kê ngầm khi người dùng nhập số lượng
  useEffect(() => {
    if (isAdjustOpen && user?.username) {
      const timer = setTimeout(() => {
        draftStorage.save(user.username, 'stock_adjust', { adjustProductId, actualStock, adjustNote });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isAdjustOpen, adjustProductId, actualStock, adjustNote, user?.username]);

  // Hủy bản nháp kiểm kê
  const handleDiscardDraft = () => {
    draftStorage.clear(user?.username, 'stock_adjust');
    setIsDraftRestored(false);
    const firstP = products[0];
    setAdjustProductId(firstP?.id || '');
    setActualStock(firstP?.current_stock || 0);
    setAdjustNote('Kiểm kê định kỳ tháng này');
  };

  const handleProductSelectForAdjust = (pId) => {
    setAdjustProductId(pId);
    const p = products.find((prod) => prod.id === Number(pId));
    if (p) setActualStock(p.current_stock);
  };

  const handleAdjustSubmit = async (e) => {
    e.preventDefault();
    setAdjustError(null);
    setIsSubmitting(true);
    try {
      await apiClient.stockLedger.adjust({
        product_id: Number(adjustProductId),
        actual_stock: Number(actualStock),
        note: adjustNote,
      });
      // Xóa bản nháp sau khi kiểm kê thành công
      draftStorage.clear(user?.username, 'stock_adjust');
      setIsDraftRestored(false);
      setIsAdjustOpen(false);
      fetchLedger();
      fetchProducts();
    } catch (err) {
      setAdjustError(err.response?.data?.detail || 'Không thể điều chỉnh tồn kho');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedProdForAdjust = products.find((p) => p.id === Number(adjustProductId));
  const diffQty = selectedProdForAdjust ? Number(actualStock) - selectedProdForAdjust.current_stock : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold font-serif text-[var(--text-primary)]">Sổ cái thẻ kho</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Nhật ký kiểm toán bất biến theo từng giây, truy vết biến động và số dư tức thời sau mỗi giao dịch</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleOpenExportModal}
            className="btn-outline flex items-center gap-2 text-xs"
          >
            <FileSpreadsheet className="w-4 h-4 text-[var(--semantic-success)]" />
            <span>Xuất Excel</span>
          </button>

          {canAdjust && (
            <button
              onClick={handleOpenAdjust}
              className="btn-secondary flex items-center gap-2 text-xs"
            >
              <SlidersHorizontal className="w-4 h-4" />
              <span>Điều chỉnh kiểm kê kho</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card-warm p-3.5 sm:p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3 flex-1 min-w-0">
          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="input-wood text-xs flex-1 sm:max-w-sm min-w-0"
          >
            <option value="">Tất cả mặt hàng</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (Tồn: {p.current_stock} {p.unit})
              </option>
            ))}
          </select>

          <select
            value={transactionType}
            onChange={(e) => setTransactionType(e.target.value)}
            className="input-wood text-xs sm:w-auto min-w-0"
          >
            <option value="">Tất cả loại giao dịch</option>
            <option value="IMPORT">Nhập kho (IMPORT)</option>
            <option value="EXPORT">Xuất kho (EXPORT)</option>
            <option value="ADJUSTMENT">Điều chỉnh kiểm kê (ADJUSTMENT)</option>
          </select>
        </div>

        <button
          onClick={fetchLedger}
          className="p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-linen)] rounded-btn transition-colors cursor-pointer shrink-0"
          title="Làm mới sổ cái"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Ledger Table */}
      <div className="card-warm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--bg-linen)] text-[var(--text-secondary)] font-medium border-b border-[var(--border-subtle)]">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Tên hàng hóa</th>
                <th className="py-3 px-4 text-center">Loại nghiệp vụ</th>
                <th className="py-3 px-4">Mã chứng từ</th>
                <th className="py-3 px-4 text-center">Biến động</th>
                <th className="py-3 px-4 text-center font-bold">Tồn sau giao dịch</th>
                <th className="py-3 px-4">Người thực hiện</th>
                <th className="py-3 px-4">Ghi chú</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-card)]">
              {showTableLoader ? (
                <Loader variant="table" columns={8} rows={8} />
              ) : ledgerEntries.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-10 text-[var(--text-muted)]">
                    Chưa ghi nhận biến động nào trong thẻ kho.
                  </td>
                </tr>
              ) : (
                ledgerEntries.map((l) => {
                  const isPositive = l.quantity_change > 0;
                  return (
                    <tr key={l.id} className="hover:bg-[var(--bg-linen)]/60 transition-colors">
                      <td className="py-3.5 px-4 text-[var(--text-secondary)] font-mono">
                        {new Date(l.transaction_date).toLocaleString('vi-VN')}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">
                        {l.product_name || l.product?.name || 'Mặt hàng'}
                      </td>
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
                      <td className="py-3.5 px-4 font-mono text-[var(--text-primary)] font-medium">{l.reference_code}</td>
                      <td className="py-3.5 px-4 text-center font-mono">
                        <span
                          className={`font-bold px-2 py-0.5 rounded-btn inline-block ${
                            isPositive
                              ? 'bg-[var(--semantic-success)]/10 text-[var(--semantic-success)]'
                              : 'bg-[var(--semantic-alert)]/10 text-[var(--semantic-alert)]'
                          }`}
                        >
                          {isPositive ? `+${l.quantity_change}` : l.quantity_change}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="font-mono font-bold text-[var(--text-primary)] bg-[var(--bg-linen)] px-2.5 py-1 rounded-btn border border-[var(--border-subtle)]">
                          {l.balance_after}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--text-secondary)]">
                        {l.creator_name || l.creator?.full_name || 'Hệ thống'}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--text-muted)] max-w-xs truncate">{l.note || '-'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Điều Chỉnh Kiểm Kê */}
      <Modal isOpen={isAdjustOpen} onClose={() => setIsAdjustOpen(false)} title="Điều chỉnh tồn kho sau kiểm kê thực tế">
        {isDraftRestored && (
          <div className="mb-4 p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-card flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-primary)]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--semantic-ai)] shrink-0" />
              <span>
                <strong>Đã khôi phục bản nháp kiểm kê</strong> (lưu lúc {draftSavedTime}). Hệ thống lưu tối đa 1 ngày.
              </span>
            </div>
            <button
              type="button"
              onClick={handleDiscardDraft}
              className="text-xs font-semibold text-[var(--semantic-alert)] hover:underline cursor-pointer shrink-0"
              title="Xóa nội dung nháp này để nhập từ đầu"
            >
              Xóa bản nháp
            </button>
          </div>
        )}

        {adjustError && (
          <div className="mb-4 p-3 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card flex items-center gap-2 text-xs text-[var(--semantic-alert)] font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{adjustError}</span>
          </div>
        )}

        <form onSubmit={handleAdjustSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Mặt hàng kiểm kê</label>
            <ProductSelect
              products={products}
              value={adjustProductId}
              onChange={(newId) => handleProductSelectForAdjust(newId)}
              placeholder="Gõ tên hoặc chữ cái đầu để tìm..."
            />
          </div>

          <div className="p-3 bg-[var(--bg-linen)] border border-[var(--border-subtle)] rounded-card text-xs space-y-1.5">
            <div className="flex justify-between">
              <span className="text-[var(--text-secondary)]">Tồn kho trên hệ thống:</span>
              <strong className="font-mono text-[var(--text-primary)]">{selectedProdForAdjust?.current_stock || 0}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-secondary)]">Chênh lệch bù trừ:</span>
              <strong className={`font-mono ${diffQty >= 0 ? 'text-[var(--semantic-success)]' : 'text-[var(--semantic-alert)]'}`}>
                {diffQty >= 0 ? `+${diffQty}` : diffQty}
              </strong>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Số lượng đếm thực tế tại kho</label>
            <input
              type="number"
              min="0"
              value={actualStock}
              onChange={(e) => setActualStock(e.target.value)}
              className="w-full input-wood text-xs font-mono font-bold text-[var(--text-primary)]"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Lý do điều chỉnh kiểm kê</label>
            <input
              type="text"
              value={adjustNote}
              onChange={(e) => setAdjustNote(e.target.value)}
              placeholder="VD: Hao hụt tự nhiên, kiểm kê cuối tháng..."
              className="w-full input-wood text-xs"
              required
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-[var(--border-subtle)]">
            <button
              type="button"
              onClick={() => setIsAdjustOpen(false)}
              className="btn-outline text-xs"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary text-xs flex items-center justify-center gap-2 min-w-[150px]"
            >
              {isSubmitting && <Loader variant="inline" />}
              <span>{isSubmitting ? 'Đang cập nhật...' : 'Cập nhật tồn kho'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xuất Excel Sổ Cái Thẻ Kho */}
      <Modal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        title="Xuất Excel Sổ cái Thẻ kho (.xlsx)"
        maxWidth="max-w-md"
      >
        {exportError && (
          <div className="mb-4 p-3 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card flex items-center gap-2 text-xs text-[var(--semantic-alert)] font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{exportError}</span>
          </div>
        )}

        <form onSubmit={handleExportExcel} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
              Chọn phạm vi thời gian
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'day', label: 'Theo ngày' },
                { id: 'week', label: 'Theo tuần' },
                { id: 'month', label: 'Theo tháng' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setExportPeriod(opt.id)}
                  className={`py-2 px-3 rounded-btn text-xs font-medium border transition-colors cursor-pointer ${
                    exportPeriod === opt.id
                      ? 'bg-[var(--wood-900)] text-white border-[var(--wood-900)]'
                      : 'bg-[var(--bg-linen)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
              {exportPeriod === 'day'
                ? 'Chọn ngày xuất'
                : exportPeriod === 'week'
                ? 'Chọn một ngày bất kỳ trong tuần cần xuất'
                : 'Chọn ngày/tháng cần xuất'}
            </label>
            <div className="relative">
              <input
                type="date"
                value={exportDate}
                onChange={(e) => setExportDate(e.target.value)}
                className="w-full input-wood text-xs font-mono"
                required
              />
            </div>
          </div>

          <div className="p-3 bg-[var(--bg-linen)] border border-[var(--border-subtle)] rounded-card text-xs space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[var(--text-secondary)] flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[var(--wood-500)]" />
                <span>Phạm vi dữ liệu:</span>
              </span>
              <strong className="font-mono text-[var(--text-primary)] text-right">
                {formatRangePreview(exportPeriod, exportDate)}
              </strong>
            </div>
            <p className="text-[11px] text-[var(--text-muted)] pt-1 border-t border-[var(--border-subtle)]">
              File <span className="font-mono">.xlsx</span> gồm 2 bảng (sheet): <strong>Nhập kho</strong> và <strong>Xuất kho</strong>.
              {selectedProductId ? ' (Đang lọc theo mặt hàng đã chọn trên bảng)' : ' (Bao gồm tất cả mặt hàng)'}
            </p>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-[var(--border-subtle)]">
            <button
              type="button"
              onClick={() => setIsExportOpen(false)}
              className="btn-outline text-xs"
            >
              Đóng
            </button>
            <button
              type="submit"
              disabled={isExporting}
              className="btn-primary text-xs flex items-center justify-center gap-2 min-w-[140px]"
            >
              {isExporting ? <Loader variant="inline" /> : <Download className="w-4 h-4" />}
              <span>{isExporting ? 'Đang tạo file...' : 'Tải file .xlsx'}</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default StockLedger;
