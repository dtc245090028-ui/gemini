import React, { useState, useEffect, useRef } from 'react';
import { stockEvents } from '../utils/stockEvents';
import { usePageSync } from '../hooks/usePageSync';
import {
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  Ban,
  Sparkles,
  Search,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { draftStorage } from '../utils/draftStorage';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import ProductSelect from '../components/ProductSelect';
import Loader from '../components/Loader';
import useDelayedLoading from '../hooks/useDelayedLoading';
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';

export const ImportNotes = ({ isActive = true }) => {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const { confirm } = useConfirm();
  const [importNotes, setImportNotes] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const showTableLoader = useDelayedLoading(loading);

  // Synchronous submit lock Ref
  const isSubmittingRef = useRef(false);
  const isStaleRef = useRef(false);

  // Filter States (Yêu cầu 3.1.6: Tra cứu theo nhà cung cấp, hàng hóa, mã phiếu)
  const [searchCode, setSearchCode] = useState('');
  const [filterSupplierId, setFilterSupplierId] = useState('');
  const [filterProductId, setFilterProductId] = useState('');

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [onlySupplierProducts, setOnlySupplierProducts] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [noteText, setNoteText] = useState('');
  const [items, setItems] = useState([]);
  const [formError, setFormError] = useState(null);
  const [isDraftRestored, setIsDraftRestored] = useState(false);
  const [draftSavedTime, setDraftSavedTime] = useState('');

  // Detail Modal State
  const [selectedNote, setSelectedNote] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const canCreate = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [notesRes, supRes, prodRes, catRes] = await Promise.all([
        apiClient.importNotes.getAll(),
        apiClient.suppliers.getAll(),
        apiClient.products.getAll({ limit: 500 }),
        apiClient.categories.getAll(),
      ]);
      setImportNotes(Array.isArray(notesRes.data) ? notesRes.data : (notesRes.data.items || []));
      setSuppliers(Array.isArray(supRes.data) ? supRes.data : (supRes.data.items || []));
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
      setCategories(Array.isArray(catRes.data) ? catRes.data : (catRes.data.items || []));
    } catch (err) {
      console.error('Lỗi tải phiếu nhập:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Đồng bộ thời gian thực theo chuẩn Item 5 (Debounce, Single-Flight, MaxWait, Sparse Polling)
  usePageSync({
    fetchFn: fetchData,
    isActive,
    resource: 'import_notes',
  });

  const handleOpenCreate = () => {
    isSubmittingRef.current = false;
    const newKey = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `ik-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setIdempotencyKey(newKey);

    // Kiểm tra xem có bản nháp nào được lưu trong vòng 24h không
    const draft = draftStorage.load(user?.username, 'import_note');
    if (draft && draft.data) {
      setSupplierId(draft.data.supplierId || suppliers[0]?.id || '');
      setNoteText(draft.data.noteText || '');
      setItems(
        draft.data.items && draft.data.items.length > 0
          ? draft.data.items
          : [
              {
                category_id: products[0]?.category_id || '',
                product_id: products[0]?.id || '',
                quantity: 10,
                unit_price: Math.round((products[0]?.standard_price || 100000) * 0.75),
              },
            ]
      );
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setSupplierId(suppliers[0]?.id || '');
      setNoteText('');
      const firstSupId = suppliers[0]?.id || '';
      const supProds = products.filter((p) => Number(p.supplier_id) === Number(firstSupId));
      const defaultProd = supProds[0] || products[0];
      setItems([
        {
          category_id: defaultProd?.category_id || '',
          product_id: defaultProd?.id || '',
          quantity: 10,
          unit_price: Math.round((defaultProd?.standard_price || 100000) * 0.75),
        },
      ]);
      setIsDraftRestored(false);
      setDraftSavedTime('');
    }
    setFormError(null);
    setIsCreateOpen(true);
  };

  const handleCloseCreate = () => {
    setIsCreateOpen(false);
    isSubmittingRef.current = false;
    setIdempotencyKey('');
  };

  // Tự động lưu bản nháp ngầm khi người dùng thay đổi dữ liệu trên modal tạo phiếu
  useEffect(() => {
    if (isCreateOpen && user?.username) {
      const timer = setTimeout(() => {
        draftStorage.save(user.username, 'import_note', { supplierId, noteText, items });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isCreateOpen, supplierId, noteText, items, user?.username]);

  // Hủy bản nháp để làm mới từ đầu
  const handleDiscardDraft = () => {
    draftStorage.clear(user?.username, 'import_note');
    setIsDraftRestored(false);
    setSupplierId(suppliers[0]?.id || '');
    setNoteText('');
    const defaultProd = products[0];
    setItems([
      {
        category_id: defaultProd?.category_id || '',
        product_id: defaultProd?.id || '',
        quantity: 10,
        unit_price: Math.round((defaultProd?.standard_price || 100000) * 0.75),
      },
    ]);
  };

  const handleAddItemRow = () => {
    if (products.length === 0) return;
    const supProds = onlySupplierProducts && supplierId
      ? products.filter((p) => Number(p.supplier_id) === Number(supplierId))
      : [];
    const defaultProd = supProds[0] || products[0];
    setItems([
      ...items,
      {
        category_id: defaultProd?.category_id || '',
        product_id: defaultProd.id,
        quantity: 1,
        unit_price: Math.round(defaultProd.standard_price * 0.75),
      },
    ]);
  };

  const handleRemoveItemRow = (idx) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleItemChange = (idx, field, val) => {
    const updated = [...items];
    updated[idx][field] = val;

    // Xử lý khi thay đổi nhóm hàng: Tự động lọc và chọn mặt hàng phù hợp
    if (field === 'category_id') {
      const catId = val;
      const available = catId
        ? products.filter((p) => p.category_id === Number(catId))
        : products;
      if (available.length > 0 && !available.some((p) => p.id === Number(updated[idx].product_id))) {
        updated[idx].product_id = available[0].id;
        updated[idx].unit_price = Math.round(available[0].standard_price * 0.75);
      }
    }

    // Tự động gợi ý đơn giá và đồng bộ nhóm hàng nếu đổi sản phẩm
    if (field === 'product_id') {
      const p = products.find((prod) => prod.id === Number(val));
      if (p) {
        updated[idx].unit_price = Math.round(p.standard_price * 0.75);
        if (p.category_id && updated[idx].category_id !== p.category_id) {
          updated[idx].category_id = p.category_id;
        }
      }
    }
    setItems(updated);
  };

  const totalCalculated = items.reduce(
    (acc, it) => acc + (Number(it.quantity) || 0) * (Number(it.unit_price) || 0),
    0
  );

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setFormError(null);

    if (items.length === 0) {
      setFormError('Vui lòng thêm ít nhất một mặt hàng nhập kho');
      isSubmittingRef.current = false;
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.importNotes.create(
        {
          supplier_id: Number(supplierId),
          note: noteText,
          details: items.map((it) => ({
            product_id: Number(it.product_id),
            quantity: Number(it.quantity),
            unit_price: Number(it.unit_price),
          })),
        },
        idempotencyKey ? { headers: { 'X-Idempotency-Key': idempotencyKey } } : {}
      );
      // Xóa bản nháp khi đã lưu thành công
      draftStorage.clear(user?.username, 'import_note');
      setIsDraftRestored(false);
      setIsCreateOpen(false);
      setIdempotencyKey('');
      fetchData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Không thể tạo phiếu nhập kho');
    } finally {
      setIsSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  const handleViewDetail = async (note) => {
    try {
      const res = await apiClient.importNotes.getById(note.id);
      setSelectedNote(res.data);
      setIsDetailOpen(true);
    } catch (err) {
      showError('Không thể tải chi tiết phiếu nhập');
    }
  };

  const handleCancelNote = async (note) => {
    const res = await confirm({
      title: `Hủy phiếu nhập ${note.code}?`,
      message: 'Hệ thống sẽ hoàn trừ lại tồn kho các mặt hàng tương ứng và lưu vết phiếu đã hủy (với điều kiện tồn kho thực tế chưa bị xuất âm).',
      confirmText: 'Xác nhận hủy',
      cancelText: 'Giữ lại',
      variant: 'danger',
      showReasonInput: true,
      reasonPlaceholder: 'Nhập lý do hủy phiếu nhập (ví dụ: Nhà cung cấp giao nhầm hàng, nhập trùng...)...',
    });
    if (!res.confirmed) return;

    try {
      await apiClient.importNotes.cancel(note.id, res.reason);
      showSuccess('Đã hủy phiếu nhập và hoàn trừ tồn kho thành công!');
      fetchData();
    } catch (err) {
      showError(err.response?.data?.detail || 'Không thể hủy phiếu nhập');
    }
  };

  const filteredImportNotes = importNotes.filter((n) => {
    if (searchCode.trim()) {
      const kw = searchCode.trim().toLowerCase();
      const matchCode = (n.code || '').toLowerCase().includes(kw);
      const matchSup = (n.supplier_name || n.supplier?.name || '').toLowerCase().includes(kw);
      if (!matchCode && !matchSup) return false;
    }
    if (filterSupplierId && Number(n.supplier_id) !== Number(filterSupplierId)) {
      return false;
    }
    if (filterProductId) {
      const hasProd = (n.details || []).some((d) => Number(d.product_id) === Number(filterProductId));
      if (!hasProd) return false;
    }
    return true;
  });

  const handleSupplierChangeInModal = (newSupId) => {
    setSupplierId(newSupId);
    if (onlySupplierProducts && newSupId) {
      const supProds = products.filter((p) => Number(p.supplier_id) === Number(newSupId));
      if (supProds.length > 0) {
        setItems((prev) =>
          prev.map((row, idx) => {
            const picked = supProds[idx % supProds.length];
            return {
              ...row,
              category_id: picked.category_id || '',
              product_id: picked.id,
              unit_price: Math.round((picked.standard_price || 100000) * 0.75),
            };
          })
        );
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[var(--text-primary)] tracking-tight">Phiếu nhập kho</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Lập phiếu nhập hàng nhà cung cấp, tăng tồn kho và ghi nhận thẻ kho tự động</p>
        </div>

        {canCreate && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Lập phiếu nhập mới</span>
          </button>
        )}
      </div>

      {/* Filter Bar (Tra cứu theo Nhà cung cấp, Hàng hóa, Mã phiếu) */}
      <div className="card-wood p-3.5 sm:p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3 flex-1 min-w-0">
          <div className="relative flex-1 min-w-0">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchCode}
              onChange={(e) => setSearchCode(e.target.value)}
              placeholder="Tìm theo mã phiếu (PN-...) hoặc tên nhà cung cấp..."
              className="w-full pl-9 pr-3.5 py-2 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          <select
            value={filterSupplierId}
            onChange={(e) => setFilterSupplierId(e.target.value)}
            className="w-full sm:w-auto py-2 px-3 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer shrink-0"
          >
            <option value="">Tất cả nhà cung cấp</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            value={filterProductId}
            onChange={(e) => setFilterProductId(e.target.value)}
            className="w-full sm:w-auto py-2 px-3 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer shrink-0 max-w-xs"
          >
            <option value="">Tất cả mặt hàng nhập</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                [{p.code}] {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Import Notes Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-medium)]">
              <tr>
                <th className="py-3.5 px-4">Mã phiếu</th>
                <th className="py-3.5 px-4">Nhà cung cấp</th>
                <th className="py-3.5 px-4">Ngày chứng từ</th>
                <th className="py-3.5 px-4">Người lập</th>
                <th className="py-3.5 px-4 text-right">Tổng tiền (đ)</th>
                <th className="py-3.5 px-4 text-center">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] font-sans">
              {showTableLoader ? (
                <Loader variant="table" columns={7} rows={8} />
              ) : filteredImportNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-[var(--text-muted)]">
                    Không tìm thấy phiếu nhập kho nào phù hợp.
                  </td>
                </tr>
              ) : (
                filteredImportNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-[var(--wood-500)]">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">
                      {n.supplier_name || n.supplier?.name || suppliers.find((s) => s.id === n.supplier_id)?.name || 'N/A'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-[var(--text-secondary)]">
                      {new Date(n.note_date).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--text-secondary)]">{n.creator_name || n.creator?.full_name || 'Hệ thống'}</td>
                    <td className="py-3.5 px-4 text-right font-mono text-xs font-bold text-[var(--text-primary)]">
                      {n.total_amount?.toLocaleString()} đ
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={n.status === 'COMPLETED' ? 'success' : 'canceled'}>
                        {n.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã hủy'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleViewDetail(n)}
                          title="Xem chi tiết"
                          className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] rounded-btn transition-colors cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {canCreate && n.status === 'COMPLETED' && (
                          <button
                            onClick={() => handleCancelNote(n)}
                            title="Hủy phiếu nhập (Hoàn trừ kho)"
                            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn transition-colors cursor-pointer"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Lập Phiếu Nhập */}
      <Modal isOpen={isCreateOpen} onClose={handleCloseCreate} title="Lập phiếu nhập kho mới" maxWidth="max-w-3xl">
        {isDraftRestored && (
          <div className="mb-4 p-3.5 bg-[var(--semantic-ai-bg)] border border-[var(--semantic-ai-border)] rounded-input flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--semantic-ai)]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--semantic-ai-btn)] shrink-0" />
              <span>
                <strong>Đã khôi phục bản nháp tự động</strong> (lưu lúc {draftSavedTime}). Hệ thống lưu tối đa 1 ngày.
              </span>
            </div>
            <button
              type="button"
              onClick={handleDiscardDraft}
              className="text-xs font-bold text-[var(--semantic-alert)] hover:underline cursor-pointer shrink-0"
              title="Xóa nội dung nháp này để nhập từ đầu"
            >
              Xóa bản nháp
            </button>
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] text-[var(--semantic-alert)] rounded-input flex items-center gap-2 text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 text-[var(--semantic-alert)]" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Nhà cung cấp đối tác</label>
              <select
                value={supplierId}
                onChange={(e) => handleSupplierChangeInModal(e.target.value)}
                className="input-wood cursor-pointer"
                required
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Ghi chú chứng từ</label>
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="VD: Nhập lô hàng gỗ xuất khẩu đợt 1..."
                className="input-wood"
              />
            </div>
          </div>

          {/* Chi tiết mặt hàng */}
          <div className="border border-[var(--border-medium)] rounded-card p-3 sm:p-3.5 bg-[var(--bg-surface-warm)]">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
              <div className="flex flex-wrap items-center gap-3">
                <h4 className="text-xs font-bold text-[var(--text-primary)]">Danh mục sản phẩm nhập kho</h4>
                <label className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={onlySupplierProducts}
                    onChange={(e) => setOnlySupplierProducts(e.target.checked)}
                    className="rounded accent-[var(--wood-500)] cursor-pointer"
                  />
                  <span>Chỉ hiện SP của nhà cung cấp này</span>
                </label>
              </div>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-[var(--wood-500)] hover:text-[var(--wood-600)] font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng sản phẩm</span>
              </button>
            </div>

            <div className="space-y-2.5">
              {items.map((row, idx) => {
                const supplierPool = onlySupplierProducts && supplierId
                  ? products.filter((p) => Number(p.supplier_id) === Number(supplierId))
                  : products;
                const baseProducts = supplierPool.length > 0 ? supplierPool : products;
                const availableProducts = row.category_id
                  ? baseProducts.filter((p) => p.category_id === Number(row.category_id))
                  : baseProducts;

                return (
                  <div
                    key={idx}
                    style={{ zIndex: items.length - idx }}
                    className="grid grid-cols-1 md:grid-cols-12 gap-2.5 items-center bg-[var(--bg-surface)] p-2.5 sm:p-3 rounded-input border border-[var(--border-medium)] relative"
                  >
                    {/* Chọn nhóm hàng */}
                    <div className="md:col-span-3 min-w-0">
                      <select
                        value={row.category_id || ''}
                        onChange={(e) => handleItemChange(idx, 'category_id', e.target.value)}
                        className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer"
                        title="Lọc danh sách theo nhóm hàng"
                      >
                        <option value="">-- Tất cả nhóm --</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Chọn tên hàng hóa hỗ trợ gõ tìm kiếm & gõ tắt chữ cái đầu */}
                    <div className="md:col-span-4 min-w-0">
                      <ProductSelect
                        products={availableProducts}
                        value={row.product_id}
                        onChange={(newId) => handleItemChange(idx, 'product_id', newId)}
                        placeholder="Gõ tên hoặc chữ cái đầu (VD: blv)..."
                        className="w-full min-w-0"
                      />
                    </div>

                    {/* Cụm Số lượng + Đơn giá + Thành tiền + Xóa */}
                    <div className="md:col-span-5 grid grid-cols-12 gap-2 items-center min-w-0">
                      <div className="col-span-3 min-w-0">
                        <input
                          type="number"
                          min="1"
                          value={row.quantity}
                          onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                          placeholder="SL"
                          className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-2 text-center font-mono font-bold text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)]"
                          required
                        />
                      </div>
                      <div className="col-span-4 min-w-0">
                        <input
                          type="number"
                          min="0"
                          step="1000"
                          value={row.unit_price}
                          onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                          placeholder="Giá nhập"
                          className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-2 text-right font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)]"
                          required
                        />
                      </div>
                      <div className="col-span-4 text-right font-mono font-bold text-xs text-[var(--text-primary)] truncate">
                        {((Number(row.quantity) || 0) * (Number(row.unit_price) || 0)).toLocaleString()} đ
                      </div>
                      <div className="col-span-1 flex justify-end">
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          disabled={items.length <= 1}
                          className="text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn p-1.5 cursor-pointer disabled:opacity-30 disabled:pointer-events-none transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-[var(--border-medium)] flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-[var(--text-secondary)]">Tổng giá trị đơn nhập dự tính:</span>
              <span className="font-bold font-mono text-base text-[var(--text-primary)]">{totalCalculated.toLocaleString()} đ</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleCloseCreate}
              className="btn-outline"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary flex items-center justify-center gap-2 min-w-[140px]"
            >
              {isSubmitting && <Loader variant="inline" />}
              <span>{isSubmitting ? 'Đang lưu...' : 'Lưu & nhập kho'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Nhập */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi tiết phiếu nhập: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 bg-[var(--bg-surface-warm)] rounded-card border border-[var(--border-medium)]">
              <div>
                <span className="text-[var(--text-muted)] block">Nhà cung cấp:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.supplier_name || selectedNote.supplier?.name || suppliers.find((s) => s.id === selectedNote.supplier_id)?.name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Ngày tạo:</span>
                <span className="font-semibold font-mono text-[var(--text-primary)]">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Người thực hiện:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.creator_name || selectedNote.creator?.full_name || 'Hệ thống'}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block mb-0.5">Trạng thái:</span>
                <Badge variant={selectedNote.status === 'COMPLETED' ? 'success' : 'canceled'}>
                  {selectedNote.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã hủy'}
                </Badge>
              </div>
            </div>

            <div>
              <h5 className="font-bold text-[var(--text-primary)] mb-2">Chi tiết sản phẩm đã nhập:</h5>
              <div className="border border-[var(--border-medium)] rounded-card overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-medium)]">
                    <tr>
                      <th className="p-2.5">Sản phẩm</th>
                      <th className="p-2.5 text-center">Số lượng</th>
                      <th className="p-2.5 text-right">Đơn giá nhập</th>
                      <th className="p-2.5 text-right">Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)] font-sans">
                    {selectedNote.details?.map((d) => (
                      <tr key={d.id} className="hover:bg-[var(--bg-surface-hover)]">
                        <td className="p-2.5">
                          <p className="font-medium text-[var(--text-primary)]">{d.product_name}</p>
                        </td>
                        <td className="p-2.5 text-center font-bold font-mono text-[var(--text-primary)]">{d.quantity}</td>
                        <td className="p-2.5 text-right font-mono text-[var(--text-secondary)]">{d.unit_price?.toLocaleString()} đ</td>
                        <td className="p-2.5 text-right font-mono font-bold text-[var(--text-primary)]">{d.subtotal?.toLocaleString()} đ</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-[var(--bg-surface-warm)] font-bold border-t border-[var(--border-medium)]">
                    <tr>
                      <td colSpan="3" className="p-2.5 text-right text-[var(--text-secondary)]">Tổng cộng:</td>
                      <td className="p-2.5 text-right font-mono text-[var(--text-primary)]">{selectedNote.total_amount?.toLocaleString()} đ</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ImportNotes;
