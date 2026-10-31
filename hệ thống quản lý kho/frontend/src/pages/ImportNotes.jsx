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
  X,
  ChevronDown,
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
  // Danh sách mặt hàng đang kinh doanh (dùng riêng cho Modal lập phiếu mới)
  const activeProducts = React.useMemo(
    () => products.filter((p) => (p.status || 'ACTIVE').toUpperCase() === 'ACTIVE'),
    [products]
  );
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
    resource: ['import_notes', 'suppliers', 'products'],
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
      setSupplierId(draft.data.supplierId || '');
      setNoteText(draft.data.noteText || '');
      // Lọc bỏ hàng đã ngừng kinh doanh nếu có trong bản nháp cũ, đồng thời fallback supplier_id
      const validItems = (draft.data.items || [])
        .filter((it) => {
          if (!it.product_id) return true;
          const prod = products.find((p) => p.id === Number(it.product_id));
          return prod && (prod.status || 'ACTIVE').toUpperCase() === 'ACTIVE';
        })
        .map((it) => {
          const prod = products.find((p) => p.id === Number(it.product_id));
          return {
            category_id: it.category_id || prod?.category_id || '',
            supplier_id: it.supplier_id || prod?.supplier_id || '',
            product_id: it.product_id || '',
            quantity: it.quantity || 1,
            unit_price: it.unit_price !== undefined ? it.unit_price : (prod ? Math.round((prod.standard_price || 0) * 0.75) : 0),
          };
        });

      setItems(
        validItems.length > 0
          ? validItems
          : [
              {
                category_id: '',
                supplier_id: draft.data.supplierId || '',
                product_id: '',
                quantity: 10,
                unit_price: 0,
              },
            ]
      );
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setSupplierId('');
      setNoteText('');
      setItems([
        {
          category_id: '',
          supplier_id: '',
          product_id: '',
          quantity: 10,
          unit_price: 0,
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
    setSupplierId('');
    setNoteText('');
    setItems([
      {
        category_id: '',
        supplier_id: '',
        product_id: '',
        quantity: 10,
        unit_price: 0,
      },
    ]);
  };

  const handleAddItemRow = () => {
    setItems([
      ...items,
      {
        category_id: '',
        supplier_id: supplierId || '',
        product_id: '',
        quantity: 1,
        unit_price: 0,
      },
    ]);
  };

  const handleRemoveItemRow = (idx) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleItemChange = (idx, field, val) => {
    const updated = [...items];
    const pool = activeProducts.length > 0 ? activeProducts : products;

    if (field === 'category_id') {
      const catId = val ? Number(val) : '';
      updated[idx].category_id = catId;
      // Bỏ hành vi tự chọn sản phẩm đầu tiên; nếu SP đang chọn không còn khớp -> đặt product_id = ''
      if (updated[idx].product_id) {
        const curProd = pool.find((p) => p.id === Number(updated[idx].product_id));
        const matchCat = !catId || (curProd && curProd.category_id === catId);
        const matchSup = !updated[idx].supplier_id || (curProd && Number(curProd.supplier_id) === Number(updated[idx].supplier_id));
        if (!matchCat || !matchSup) {
          updated[idx].product_id = '';
          updated[idx].unit_price = 0;
        }
      }
    } else if (field === 'supplier_id') {
      const supId = val ? Number(val) : '';
      updated[idx].supplier_id = supId;
      // Nếu SP đang chọn không còn khớp với NCC mới -> đặt product_id = ''
      if (updated[idx].product_id) {
        const curProd = pool.find((p) => p.id === Number(updated[idx].product_id));
        const matchCat = !updated[idx].category_id || (curProd && curProd.category_id === Number(updated[idx].category_id));
        const matchSup = !supId || (curProd && Number(curProd.supplier_id) === supId);
        if (!matchCat || !matchSup) {
          updated[idx].product_id = '';
          updated[idx].unit_price = 0;
        }
      }
    } else if (field === 'product_id') {
      const prodId = val ? Number(val) : '';
      updated[idx].product_id = prodId;
      if (prodId) {
        const p = pool.find((prod) => prod.id === prodId);
        if (p) {
          updated[idx].unit_price = Math.round((p.standard_price || 0) * 0.75);
          // Tự động điền ngược Nhóm hàng & Nhà cung cấp
          if (p.category_id) {
            updated[idx].category_id = p.category_id;
          }
          if (p.supplier_id) {
            updated[idx].supplier_id = p.supplier_id;
            // Cách A: Chọn SP khi Header trống thì tự điền NCC
            if (!supplierId) {
              setSupplierId(String(p.supplier_id));
            }
          }
        }
      } else {
        updated[idx].unit_price = 0;
      }
    } else {
      updated[idx][field] = val;
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

    if (!supplierId) {
      setFormError('Vui lòng chọn nhà cung cấp cho phiếu nhập kho');
      isSubmittingRef.current = false;
      return;
    }

    if (items.length === 0) {
      setFormError('Vui lòng thêm ít nhất một mặt hàng nhập kho');
      isSubmittingRef.current = false;
      return;
    }

    const unselected = items.some((it) => !it.product_id);
    if (unselected) {
      setFormError('Vui lòng chọn sản phẩm cho tất cả các dòng trước khi lưu phiếu');
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
    // Giữ nguyên các dòng sản phẩm hiện có, không tự ý ghi đè
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
            {products.map((p) => {
              const isDiscontinued = (p.status || 'ACTIVE').toUpperCase() === 'DISCONTINUED';
              return (
                <option key={p.id} value={p.id}>
                  [{p.code}] {p.name}{isDiscontinued ? ' (Ngừng KD)' : ''}
                </option>
              );
            })}
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
      <Modal isOpen={isCreateOpen} onClose={handleCloseCreate} title="Lập phiếu nhập kho mới" maxWidth="max-w-4xl">
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
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-[var(--text-primary)]">
                  Nhà cung cấp phiếu nhập <span className="text-[var(--semantic-alert)]">*</span>
                </label>
                {supplierId && (
                  <button
                    type="button"
                    onClick={() => handleSupplierChangeInModal('')}
                    className="text-[11px] text-[var(--text-muted)] hover:text-[var(--semantic-alert)] flex items-center gap-0.5 cursor-pointer"
                    title="Xóa chọn nhà cung cấp trên phiếu"
                  >
                    <X className="w-3 h-3" />
                    <span>Bỏ chọn</span>
                  </button>
                )}
              </div>
              <select
                value={supplierId || ''}
                onChange={(e) => handleSupplierChangeInModal(e.target.value)}
                className="input-wood cursor-pointer"
                required
              >
                <option value="">-- Chọn nhà cung cấp --</option>
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
              <h4 className="text-xs font-bold text-[var(--text-primary)]">Danh mục sản phẩm nhập kho</h4>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-[var(--wood-500)] hover:text-[var(--wood-600)] font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng sản phẩm</span>
              </button>
            </div>

            <div className="space-y-3">
              {items.map((row, idx) => {
                const pool = activeProducts.length > 0 ? activeProducts : products;

                // 1. Nhóm hàng khả dụng cho dòng này (thu hẹp theo NCC dòng nếu có)
                const rowCategories = row.supplier_id
                  ? categories.filter((c) =>
                      pool.some(
                        (p) =>
                          p.category_id === Number(c.id) &&
                          Number(p.supplier_id) === Number(row.supplier_id)
                      )
                    )
                  : categories;

                // 2. Nhà cung cấp khả dụng cho dòng này (thu hẹp theo Nhóm dòng nếu có)
                const rowSuppliers = row.category_id
                  ? suppliers.filter((s) =>
                      pool.some(
                        (p) =>
                          Number(p.supplier_id) === Number(s.id) &&
                          p.category_id === Number(row.category_id)
                      )
                    )
                  : suppliers;

                // 3. Sản phẩm khả dụng cho dòng này (lọc theo Nhóm & NCC dòng nếu có)
                const rowProducts = pool.filter((p) => {
                  if (row.category_id && p.category_id !== Number(row.category_id)) return false;
                  if (row.supplier_id && Number(p.supplier_id) !== Number(row.supplier_id)) return false;
                  return true;
                });

                // Kiểm tra cảnh báo khác NCC với Header của phiếu
                const selectedProd = row.product_id ? pool.find((p) => p.id === Number(row.product_id)) : null;
                const isSupplierDiffFromHeader = Boolean(
                  supplierId && selectedProd && Number(selectedProd.supplier_id) !== Number(supplierId)
                );
                const prodSupObj = selectedProd
                  ? suppliers.find((s) => Number(s.id) === Number(selectedProd.supplier_id))
                  : null;

                return (
                  <div
                    key={idx}
                    style={{ zIndex: items.length - idx }}
                    className="bg-[var(--bg-surface)] p-2.5 sm:p-3 rounded-card border border-[var(--border-medium)] relative space-y-2.5 shadow-xs"
                  >
                    {/* Hàng 1: 3 ô lựa chọn độc lập [Nhóm hàng ✕] [Nhà cung cấp ✕] [Sản phẩm ✕] */}
                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                      {/* Ô 1: Nhóm hàng */}
                      <div className="sm:col-span-3 min-w-0">
                        <div className="relative flex items-center">
                          <select
                            value={row.category_id || ''}
                            onChange={(e) => handleItemChange(idx, 'category_id', e.target.value)}
                            className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input pl-2.5 pr-7 py-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer truncate"
                            title="Lọc theo nhóm hàng"
                          >
                            <option value="">-- Tất cả nhóm --</option>
                            {rowCategories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                          </select>
                          {row.category_id && (
                            <button
                              type="button"
                              onClick={() => handleItemChange(idx, 'category_id', '')}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-0.5 cursor-pointer"
                              title="Xóa lọc nhóm hàng"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Ô 2: Nhà cung cấp */}
                      <div className="sm:col-span-4 min-w-0">
                        <div className="relative flex items-center">
                          <select
                            value={row.supplier_id || ''}
                            onChange={(e) => handleItemChange(idx, 'supplier_id', e.target.value)}
                            className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input pl-2.5 pr-7 py-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer truncate"
                            title="Lọc theo nhà cung cấp"
                          >
                            <option value="">-- Tất cả nhà cung cấp --</option>
                            {rowSuppliers.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.name}
                              </option>
                            ))}
                          </select>
                          {row.supplier_id && (
                            <button
                              type="button"
                              onClick={() => handleItemChange(idx, 'supplier_id', '')}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-0.5 cursor-pointer"
                              title="Xóa lọc nhà cung cấp"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Ô 3: Sản phẩm (Combobox tìm kiếm tự do) */}
                      <div className="sm:col-span-5 min-w-0">
                        <ProductSelect
                          products={rowProducts}
                          value={row.product_id}
                          onChange={(newId) => handleItemChange(idx, 'product_id', newId)}
                          placeholder="Tìm sản phẩm (mã, tên, chữ cái đầu)..."
                          clearable={true}
                          className="w-full min-w-0"
                        />
                      </div>
                    </div>

                    {/* Hàng 2: [SL] [Đơn giá] [Thành tiền] [Xóa dòng] */}
                    <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[var(--border-subtle)]">
                      <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[200px]">
                        <div className="flex items-center gap-1.5">
                          <label className="text-[11px] font-medium text-[var(--text-muted)] shrink-0">SL:</label>
                          <input
                            type="number"
                            min="1"
                            value={row.quantity}
                            onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                            placeholder="SL"
                            className="w-20 text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-1.5 text-center font-mono font-bold text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)]"
                            required
                          />
                        </div>

                        <div className="flex items-center gap-1.5">
                          <label className="text-[11px] font-medium text-[var(--text-muted)] shrink-0">Giá nhập:</label>
                          <input
                            type="number"
                            min="0"
                            step="1000"
                            value={row.unit_price}
                            onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                            placeholder="Đơn giá"
                            className="w-28 text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-1.5 text-right font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)]"
                            required
                          />
                          <span className="text-xs text-[var(--text-muted)]">đ</span>
                        </div>

                        <div className="flex items-center gap-1.5 ml-auto">
                          <span className="text-[11px] text-[var(--text-muted)]">Thành tiền:</span>
                          <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                            {((Number(row.quantity) || 0) * (Number(row.unit_price) || 0)).toLocaleString()} đ
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center shrink-0">
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          disabled={items.length <= 1}
                          className="text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn p-1.5 cursor-pointer disabled:opacity-30 disabled:pointer-events-none transition-colors"
                          title={items.length <= 1 ? 'Phiếu cần tối thiểu 1 mặt hàng' : 'Xóa dòng này'}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Cảnh báo nhẹ nếu mặt hàng có NCC khác với Header của phiếu */}
                    {isSupplierDiffFromHeader && (
                      <div className="flex items-center gap-1.5 text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 px-2.5 py-1 rounded border border-amber-200 dark:border-amber-800/50">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                        <span>
                          Lưu ý: Mặt hàng này có NCC mặc định là <strong>{prodSupObj?.name || 'NCC khác'}</strong>, khác với NCC của phiếu nhập ({suppliers.find((s) => s.id === Number(supplierId))?.name || 'NCC đã chọn'}).
                        </span>
                      </div>
                    )}
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
