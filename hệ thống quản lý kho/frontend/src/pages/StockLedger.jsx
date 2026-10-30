import React, { useState, useEffect, useRef } from 'react';
import { stockEvents } from '../utils/stockEvents';
import { usePageSync } from '../hooks/usePageSync';
import {
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
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

export const StockLedger = ({ defaultProductId, isActive = true }) => {
  const { user } = useAuth();
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [ledgerSummary, setLedgerSummary] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const isStaleRef = useRef(false);
  const showTableLoader = useDelayedLoading(loading);

  // Filters
  const [selectedProductId, setSelectedProductId] = useState(defaultProductId ? String(defaultProductId) : '');
  const [transactionType, setTransactionType] = useState('');
  const [searchQ, setSearchQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Server-side product search timer
  const productSearchTimerRef = useRef(null);

  // Reference Detail Modal (E)
  const [isRefModalOpen, setIsRefModalOpen] = useState(false);
  const [refDetailLoading, setRefDetailLoading] = useState(false);
  const [refDetailError, setRefDetailError] = useState(null);
  const [refDetailData, setRefDetailData] = useState(null);

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

  // Debounce 300ms cho ô tìm kiếm q
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(searchQ.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQ]);

  // Mọi bộ lọc đổi thì quay về trang 1
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedProductId, transactionType, debouncedQ, dateFrom, dateTo]);

  const fetchProducts = async (serverQuery = '') => {
    try {
      const params = { limit: 500 };
      if (serverQuery && serverQuery.trim()) {
        params.search = serverQuery.trim();
      }
      const res = await apiClient.products.getAll(params);
      const fetched = Array.isArray(res.data) ? res.data : (res.data.items || []);
      if (serverQuery && serverQuery.trim()) {
        // Merge kết quả tìm kiếm server vào danh sách hiện có để giữ sản phẩm đang chọn
        setProducts((prev) => {
          const map = new Map(prev.map((item) => [item.id, item]));
          fetched.forEach((item) => map.set(item.id, item));
          return Array.from(map.values());
        });
      } else {
        setProducts(fetched);
      }
      if (!selectedProductId && defaultProductId) {
        setSelectedProductId(String(defaultProductId));
      }
    } catch (err) {
      console.error('Lỗi tải sản phẩm:', err);
    }
  };

  const handleProductSearchServer = (queryText) => {
    if (productSearchTimerRef.current) {
      clearTimeout(productSearchTimerRef.current);
    }
    productSearchTimerRef.current = setTimeout(() => {
      if (queryText && queryText.trim().length >= 2) {
        fetchProducts(queryText.trim());
      }
    }, 250);
  };

  const fetchLedger = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const params = {
        include_summary: true,
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      };
      if (selectedProductId) params.product_id = Number(selectedProductId);
      if (transactionType) params.transaction_type = transactionType;
      if (debouncedQ) params.q = debouncedQ;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await apiClient.stockLedger.getAll(params);
      if (Array.isArray(res.data)) {
        setLedgerEntries(res.data);
        setTotalEntries(res.data.length);
        setLedgerSummary(res.data[0]?.summary || null);
      } else {
        setLedgerEntries(res.data.items || []);
        setTotalEntries(res.data.total ?? (res.data.items || []).length);
        setLedgerSummary(res.data.summary || null);
      }
    } catch (err) {
      console.error('Lỗi tải thẻ kho:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    fetchLedger();
  }, [selectedProductId, transactionType, debouncedQ, dateFrom, dateTo, currentPage, pageSize]);

  // Đồng bộ thẻ kho tự động theo chuẩn Item 5 (Debounce, Single-Flight, MaxWait, Sparse Polling)
  const syncLedgerData = useCallback(async (silent = true) => {
    await Promise.all([fetchLedger(silent), fetchProducts()]);
  }, [fetchLedger, fetchProducts]);

  usePageSync({
    fetchFn: syncLedgerData,
    isActive,
    resource: 'stock_ledger',
  });

  // Mở popup Chi tiết chứng từ (E)
  const handleOpenReferenceDetail = async (referenceCode) => {
    if (!referenceCode) return;
    setIsRefModalOpen(true);
    setRefDetailLoading(true);
    setRefDetailError(null);
    setRefDetailData(null);
    try {
      const res = await apiClient.stockLedger.getByReference(referenceCode);
      setRefDetailData(res.data);
    } catch (err) {
      setRefDetailError(err.response?.data?.detail || 'Không thể tải thông tin chi tiết chứng từ.');
    } finally {
      setRefDetailLoading(false);
    }
  };

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
        split_columns: true,
      };
      if (selectedProductId) params.product_id = Number(selectedProductId);
      if (transactionType) params.transaction_type = transactionType;
      if (debouncedQ) params.q = debouncedQ;

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

  const handleOpenAdjust = () => {
    const draft = draftStorage.load(user?.username, 'stock_adjust');
    if (draft && draft.data) {
      setAdjustProductId(draft.data.adjustProductId || products[0]?.id || '');
      setActualStock(
        draft.data.actualStock !== undefined ? draft.data.actualStock : (products[0]?.current_stock || 0)
      );
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

  useEffect(() => {
    if (isAdjustOpen && user?.username) {
      const timer = setTimeout(() => {
        draftStorage.save(user.username, 'stock_adjust', { adjustProductId, actualStock, adjustNote });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isAdjustOpen, adjustProductId, actualStock, adjustNote, user?.username]);

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
        reason: adjustNote,
        note: adjustNote,
      });
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

  const handleResetFilters = () => {
    setSelectedProductId('');
    setTransactionType('');
    setSearchQ('');
    setDebouncedQ('');
    setDateFrom('');
    setDateTo('');
    setCurrentPage(1);
  };

  const hasActiveFilters = Boolean(selectedProductId || transactionType || searchQ || dateFrom || dateTo);
  const isSingleProductMode = Boolean(selectedProductId && ledgerSummary);

  const selectedProdForAdjust = products.find((p) => p.id === Number(adjustProductId));
  const diffQty = selectedProdForAdjust ? Number(actualStock) - selectedProdForAdjust.current_stock : 0;

  // Pagination helpers
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startItem = totalEntries === 0 ? 0 : (safeCurrentPage - 1) * pageSize + 1;
  const endItem = Math.min(safeCurrentPage * pageSize, totalEntries);

  const renderTransactionBadge = (type) => {
    if (type === 'IMPORT') {
      return <Badge variant="forest">Nhập kho</Badge>;
    }
    if (type === 'EXPORT') {
      return <Badge variant="wood">Xuất kho</Badge>;
    }
    return (
      <div className="inline-flex flex-col items-center gap-0.5">
        <Badge variant="amber">Kiểm kê</Badge>
      </div>
    );
  };

  const renderBalanceAfterCell = (balanceAfter, minStock) => {
    const safeMin = minStock !== null && minStock !== undefined ? Number(minStock) : 0;
    if (balanceAfter === 0) {
      return (
        <span className="font-mono font-bold px-2.5 py-1 rounded-btn border inline-block whitespace-nowrap bg-[var(--semantic-alert-solid-bg)] text-[var(--semantic-alert-solid-text)] border-[var(--semantic-alert-solid-border)]">
          0 (Hết hàng)
        </span>
      );
    }
    if (safeMin > 0 && balanceAfter <= safeMin) {
      return (
        <span className="font-mono font-bold px-2.5 py-1 rounded-btn border inline-block whitespace-nowrap bg-[var(--semantic-orange-bg)] text-[var(--semantic-orange)] border-[var(--semantic-orange-border)]">
          {balanceAfter.toLocaleString('vi-VN')} / min {safeMin.toLocaleString('vi-VN')}
        </span>
      );
    }
    return (
      <span className="font-mono font-bold text-[var(--text-primary)] bg-[var(--bg-linen)] px-2.5 py-1 rounded-btn border border-[var(--border-subtle)] inline-block whitespace-nowrap">
        {balanceAfter.toLocaleString('vi-VN')}
      </span>
    );
  };

  const refHasPricing = Boolean(
    refDetailData?.items?.some((it) => it.unit_price !== null && it.unit_price !== undefined)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold font-serif text-[var(--text-primary)]">Sổ cái thẻ kho</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Nhật ký kiểm toán bất biến theo từng giây, truy vết biến động và số dư tức thời sau mỗi giao dịch
          </p>
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

      {/* Filter Bar (D) */}
      <div className="card-warm p-3.5 sm:p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5 sm:gap-3 items-center">
          {/* 1. Ô chọn mặt hàng có tìm kiếm (toàn bộ 109 SKU) */}
          <div className="md:col-span-4 min-w-0">
            <ProductSelect
              products={products}
              value={selectedProductId}
              onChange={(val) => setSelectedProductId(val ? String(val) : '')}
              placeholder="Tất cả mặt hàng (Gõ tên / mã SKU để lọc...)"
              allowEmptyOption={true}
              emptyLabel="Tất cả mặt hàng"
              onSearchChange={handleProductSearchServer}
            />
          </div>

          {/* 2. Ô tìm kiếm Mã chứng từ / ghi chú / tên hàng (debounce 300ms) */}
          <div className="md:col-span-4 relative min-w-0">
            <Search className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Mã chứng từ / ghi chú / tên hàng..."
              className="input-wood pl-8 pr-7 text-xs w-full"
            />
            {searchQ && (
              <button
                type="button"
                onClick={() => setSearchQ('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
                title="Xóa từ khóa"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* 3. Loại nghiệp vụ */}
          <div className="md:col-span-4 flex items-center gap-2 min-w-0">
            <select
              value={transactionType}
              onChange={(e) => setTransactionType(e.target.value)}
              className="input-wood text-xs flex-1 min-w-0 cursor-pointer"
            >
              <option value="">Tất cả loại giao dịch</option>
              <option value="IMPORT">Nhập kho (IMPORT)</option>
              <option value="EXPORT">Xuất kho (EXPORT)</option>
              <option value="ADJUSTMENT">Kiểm kê (ADJUSTMENT)</option>
            </select>

            <button
              type="button"
              onClick={() => fetchLedger()}
              className="p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-linen)] rounded-btn border border-[var(--border-subtle)] transition-colors cursor-pointer shrink-0"
              title="Làm mới sổ cái"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Hàng 2: Bộ lọc Từ ngày - Đến ngày */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[var(--border-subtle)]">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
              <Calendar className="w-3.5 h-3.5 text-[var(--wood-500)] shrink-0" />
              <span className="font-medium">Từ ngày:</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-wood py-1 px-2.5 text-xs font-mono w-auto"
              />
            </div>

            <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
              <span className="font-medium">Đến ngày:</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-wood py-1 px-2.5 text-xs font-mono w-auto"
              />
            </div>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="text-xs text-[var(--semantic-alert)] hover:underline font-medium flex items-center gap-1 cursor-pointer ml-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Xóa bộ lọc</span>
              </button>
            )}
          </div>

          {isSingleProductMode && (
            <div className="text-xs text-[var(--text-secondary)] flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[var(--wood-500)]" />
              <span>
                Chế độ: <strong className="text-[var(--text-primary)]">Sổ kho chi tiết theo mặt hàng</strong>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Ledger Table (B & C & E) */}
      <div className="card-warm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--bg-linen)] text-[var(--text-secondary)] font-medium border-b border-[var(--border-subtle)]">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Tên hàng hóa</th>
                <th className="py-3 px-4 text-center">Loại nghiệp vụ</th>
                <th className="py-3 px-4">Mã chứng từ</th>
                <th className="py-3 px-4 text-center text-[var(--semantic-success)] font-bold">Nhập</th>
                <th className="py-3 px-4 text-center text-[var(--semantic-alert)] font-bold">Xuất</th>
                <th className="py-3 px-4 text-center font-bold">Tồn sau giao dịch</th>
                <th className="py-3 px-4">Người thực hiện</th>
                <th className="py-3 px-4">Ghi chú</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-card)]">
              {showTableLoader ? (
                <Loader variant="table" columns={9} rows={8} />
              ) : (
                <>
                  {/* C. Dòng đầu: Tồn đầu kỳ (chỉ hiện ở trang đầu khi lọc 1 mặt hàng) */}
                  {isSingleProductMode && safeCurrentPage === 1 && (
                    <tr className="bg-[var(--bg-surface-warm)] font-bold text-[var(--text-primary)] border-b border-[var(--border-medium)]">
                      <td colSpan={4} className="py-3 px-4">
                        Tồn đầu kỳ
                      </td>
                      <td className="py-3 px-4 text-center font-mono"></td>
                      <td className="py-3 px-4 text-center font-mono"></td>
                      <td className="py-3 px-4 text-center font-mono">
                        <span className="px-2.5 py-1 rounded-btn bg-[var(--bg-linen)] border border-[var(--border-medium)] inline-block">
                          {(ledgerSummary.opening_balance ?? 0).toLocaleString('vi-VN')}
                        </span>
                      </td>
                      <td colSpan={2} className="py-3 px-4 text-[var(--text-muted)] font-normal">
                        Số dư trước kỳ lọc
                      </td>
                    </tr>
                  )}

                  {ledgerEntries.length === 0 ? (
                    <tr>
                      <td colSpan="9" className="text-center py-10 text-[var(--text-muted)]">
                        Chưa ghi nhận biến động nào khớp với bộ lọc trong thẻ kho.
                      </td>
                    </tr>
                  ) : (
                    ledgerEntries.map((l) => {
                      const qtyIn = l.qty_in !== undefined ? Number(l.qty_in) : Math.max(Number(l.quantity_change) || 0, 0);
                      const qtyOut = l.qty_out !== undefined ? Number(l.qty_out) : Math.max(-(Number(l.quantity_change) || 0), 0);
                      return (
                        <tr key={l.id} className="hover:bg-[var(--bg-linen)]/60 transition-colors">
                          <td className="py-3.5 px-4 text-[var(--text-secondary)] font-mono whitespace-nowrap">
                            {new Date(l.transaction_date).toLocaleString('vi-VN')}
                          </td>
                          <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">
                            <div>{l.product_name || l.product?.name || 'Mặt hàng'}</div>
                            {l.product_sku && (
                              <span className="font-mono text-xs text-[var(--text-muted)]">{l.product_sku}</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {renderTransactionBadge(l.transaction_type)}
                          </td>
                          <td className="py-3.5 px-4 font-mono">
                            {l.reference_code ? (
                              <button
                                type="button"
                                onClick={() => handleOpenReferenceDetail(l.reference_code)}
                                className="inline-flex items-center gap-1 font-mono font-semibold text-[var(--wood-500)] hover:underline cursor-pointer"
                                title="Bấm để xem chi tiết chứng từ"
                              >
                                <span>{l.reference_code}</span>
                                <ExternalLink className="w-3 h-3 opacity-75 shrink-0" />
                              </button>
                            ) : (
                              <span className="text-[var(--text-muted)]">-</span>
                            )}
                          </td>
                          {/* Cột Nhập: hiện số dương màu xanh lá, ô không có giá trị để trống */}
                          <td className="py-3.5 px-4 text-center font-mono">
                            {qtyIn > 0 ? (
                              <span className="font-bold px-2 py-0.5 rounded-btn inline-block bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border border-[var(--semantic-success-border)]">
                                {qtyIn.toLocaleString('vi-VN')}
                              </span>
                            ) : null}
                          </td>
                          {/* Cột Xuất: hiện số dương màu đỏ, ô không có giá trị để trống */}
                          <td className="py-3.5 px-4 text-center font-mono">
                            {qtyOut > 0 ? (
                              <span className="font-bold px-2 py-0.5 rounded-btn inline-block bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border border-[var(--semantic-alert-border)]">
                                {qtyOut.toLocaleString('vi-VN')}
                              </span>
                            ) : null}
                          </td>
                          {/* Cột Tồn sau giao dịch tô màu theo min_stock */}
                          <td className="py-3.5 px-4 text-center">
                            {renderBalanceAfterCell(l.balance_after, l.min_stock)}
                          </td>
                          <td className="py-3.5 px-4 text-[var(--text-secondary)]">
                            {l.creator_name || l.creator?.full_name || 'Hệ thống'}
                          </td>
                          <td className="py-3.5 px-4 text-[var(--text-muted)] max-w-xs truncate" title={l.note || ''}>
                            {l.note || '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}

                  {/* C. Dòng cuối: Cộng phát sinh & Tồn cuối kỳ (luôn hiện theo tổng toàn bộ từ summary API) */}
                  {isSingleProductMode && (
                    <>
                      <tr className="bg-[var(--bg-surface-warm)] font-bold text-[var(--text-primary)] border-t border-[var(--border-medium)]">
                        <td colSpan={4} className="py-3 px-4">
                          Cộng phát sinh
                        </td>
                        <td className="py-3 px-4 text-center font-mono">
                          {(ledgerSummary.total_in ?? 0) > 0 ? (
                            <span className="px-2 py-0.5 rounded-btn inline-block bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border border-[var(--semantic-success-border)]">
                              {ledgerSummary.total_in.toLocaleString('vi-VN')}
                            </span>
                          ) : (
                            <span className="text-[var(--text-muted)]">0</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center font-mono">
                          {(ledgerSummary.total_out ?? 0) > 0 ? (
                            <span className="px-2 py-0.5 rounded-btn inline-block bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border border-[var(--semantic-alert-border)]">
                              {ledgerSummary.total_out.toLocaleString('vi-VN')}
                            </span>
                          ) : (
                            <span className="text-[var(--text-muted)]">0</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center font-mono"></td>
                        <td colSpan={2} className="py-3 px-4 text-[var(--text-muted)] font-normal">
                          Tổng phát sinh toàn kỳ lọc
                        </td>
                      </tr>
                      <tr className="bg-[var(--bg-surface-warm)] font-bold text-[var(--text-primary)] border-t border-[var(--border-subtle)]">
                        <td colSpan={4} className="py-3 px-4">
                          Tồn cuối kỳ
                        </td>
                        <td className="py-3 px-4 text-center font-mono"></td>
                        <td className="py-3 px-4 text-center font-mono"></td>
                        <td className="py-3 px-4 text-center font-mono">
                          <span className="px-2.5 py-1 rounded-btn bg-[var(--bg-linen)] border border-[var(--border-medium)] inline-block">
                            {(ledgerSummary.closing_balance ?? 0).toLocaleString('vi-VN')}
                          </span>
                        </td>
                        <td colSpan={2} className="py-3 px-4 text-[var(--text-muted)] font-normal">
                          = Tồn đầu kỳ ({(ledgerSummary.opening_balance ?? 0).toLocaleString('vi-VN')}) + Nhập (
                          {(ledgerSummary.total_in ?? 0).toLocaleString('vi-VN')}) - Xuất (
                          {(ledgerSummary.total_out ?? 0).toLocaleString('vi-VN')})
                        </td>
                      </tr>
                    </>
                  )}
                </>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-4 py-3 bg-[var(--bg-surface-warm)] border-t border-[var(--border-subtle)] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--text-secondary)]">
          <div className="flex items-center gap-3">
            <span>
              Hiển thị <strong className="text-[var(--text-primary)]">{startItem} – {endItem}</strong> trong tổng số{' '}
              <strong className="text-[var(--text-primary)]">{totalEntries}</strong> dòng thẻ kho
            </span>
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">Dòng/trang:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="py-1 px-2 bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] cursor-pointer"
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safeCurrentPage <= 1}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-btn border border-[var(--border-medium)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Trước</span>
            </button>
            <span className="px-2.5 py-1 font-mono font-semibold text-[var(--text-primary)]">
              Trang {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safeCurrentPage >= totalPages}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-btn border border-[var(--border-medium)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <span>Sau</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal Chi Tiết Chứng Từ (E) */}
      <Modal
        isOpen={isRefModalOpen}
        onClose={() => setIsRefModalOpen(false)}
        title={`Chi tiết chứng từ: ${refDetailData?.reference_code || ''}`}
        maxWidth="max-w-3xl"
      >
        {refDetailLoading ? (
          <div className="py-10 flex justify-center">
            <Loader variant="inline" />
            <span className="ml-2 text-xs text-[var(--text-secondary)]">Đang tải chi tiết chứng từ...</span>
          </div>
        ) : refDetailError ? (
          <div className="p-3 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] rounded-card flex items-center gap-2 text-xs text-[var(--semantic-alert)] font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{refDetailError}</span>
          </div>
        ) : refDetailData ? (
          <div className="space-y-4 text-xs">
            {/* Thông tin chung của phiếu */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 bg-[var(--bg-linen)] border border-[var(--border-subtle)] rounded-card">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between sm:justify-start sm:gap-2">
                  <span className="text-[var(--text-secondary)]">Mã phiếu:</span>
                  <strong className="font-mono text-[var(--text-primary)]">{refDetailData.reference_code}</strong>
                </div>
                <div className="flex items-center justify-between sm:justify-start sm:gap-2">
                  <span className="text-[var(--text-secondary)]">Thời gian:</span>
                  <span className="font-mono text-[var(--text-primary)]">
                    {refDetailData.transaction_date
                      ? new Date(refDetailData.transaction_date).toLocaleString('vi-VN')
                      : '-'}
                  </span>
                </div>
                <div className="flex items-center justify-between sm:justify-start sm:gap-2">
                  <span className="text-[var(--text-secondary)]">Loại nghiệp vụ:</span>
                  {renderTransactionBadge(refDetailData.transaction_type)}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between sm:justify-start sm:gap-2">
                  <span className="text-[var(--text-secondary)]">Đối tác / Khách hàng:</span>
                  <strong className="text-[var(--text-primary)]">
                    {refDetailData.partner_name || 'Nội bộ / Kiểm kê kho'}
                  </strong>
                </div>
                <div className="flex items-center justify-between sm:justify-start sm:gap-2">
                  <span className="text-[var(--text-secondary)]">Người thực hiện:</span>
                  <span className="text-[var(--text-primary)]">{refDetailData.creator_name || 'Hệ thống'}</span>
                </div>
                {refDetailData.note && (
                  <div className="flex items-start justify-between sm:justify-start sm:gap-2">
                    <span className="text-[var(--text-secondary)] shrink-0">Ghi chú:</span>
                    <span className="text-[var(--text-primary)]">{refDetailData.note}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Bảng tất cả mặt hàng cùng phiếu */}
            <div className="border border-[var(--border-subtle)] rounded-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-secondary)] font-semibold border-b border-[var(--border-subtle)]">
                    <tr>
                      <th className="py-2.5 px-3">Mã SKU</th>
                      <th className="py-2.5 px-3">Tên mặt hàng</th>
                      <th className="py-2.5 px-3 text-center text-[var(--semantic-success)]">SL Nhập</th>
                      <th className="py-2.5 px-3 text-center text-[var(--semantic-alert)]">SL Xuất</th>
                      <th className="py-2.5 px-3 text-center">Tồn sau</th>
                      {refHasPricing && (
                        <>
                          <th className="py-2.5 px-3 text-right">Đơn giá</th>
                          <th className="py-2.5 px-3 text-right">Thành tiền</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-surface)]">
                    {(refDetailData.items || []).map((item) => (
                      <tr key={item.id} className="hover:bg-[var(--bg-surface-hover)]">
                        <td className="py-2.5 px-3 font-mono text-[var(--text-secondary)]">
                          {item.product_sku || '-'}
                        </td>
                        <td className="py-2.5 px-3 font-medium text-[var(--text-primary)]">{item.product_name}</td>
                        <td className="py-2.5 px-3 text-center font-mono">
                          {item.qty_in > 0 ? (
                            <span className="font-bold text-[var(--semantic-success)]">
                              {item.qty_in.toLocaleString('vi-VN')}
                            </span>
                          ) : null}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono">
                          {item.qty_out > 0 ? (
                            <span className="font-bold text-[var(--semantic-alert)]">
                              {item.qty_out.toLocaleString('vi-VN')}
                            </span>
                          ) : null}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono font-bold text-[var(--text-primary)]">
                          {item.balance_after.toLocaleString('vi-VN')}
                        </td>
                        {refHasPricing && (
                          <>
                            <td className="py-2.5 px-3 text-right font-mono text-[var(--text-secondary)]">
                              {item.unit_price !== null && item.unit_price !== undefined
                                ? `${Number(item.unit_price).toLocaleString('vi-VN')} đ`
                                : '-'}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-semibold text-[var(--text-primary)]">
                              {item.subtotal !== null && item.subtotal !== undefined
                                ? `${Number(item.subtotal).toLocaleString('vi-VN')} đ`
                                : '-'}
                            </td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                  {refDetailData.total_amount !== null && refDetailData.total_amount !== undefined && (
                    <tfoot className="bg-[var(--bg-surface-warm)] border-t border-[var(--border-medium)] font-bold">
                      <tr>
                        <td colSpan={refHasPricing ? 6 : 4} className="py-2.5 px-3 text-right text-[var(--text-primary)]">
                          Tổng giá trị phiếu:
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-[var(--wood-500)]">
                          {Number(refDetailData.total_amount).toLocaleString('vi-VN')} đ
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button type="button" onClick={() => setIsRefModalOpen(false)} className="btn-outline text-xs">
                Đóng
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

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
              placeholder="Gõ tên hoặc mã SKU để tìm..."
              onSearchChange={handleProductSearchServer}
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
              File <span className="font-mono">.xlsx</span> gồm 2 bảng (sheet): <strong>Nhập kho</strong> và <strong>Xuất kho</strong> (với cột Nhập / Xuất tách biệt).
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
