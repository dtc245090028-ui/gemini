import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  Ban,
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

export const ImportNotes = () => {
  const { user } = useAuth();
  const [importNotes, setImportNotes] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const showTableLoader = useDelayedLoading(loading);

  // Synchronous submit lock Ref
  const isSubmittingRef = useRef(false);

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

  const fetchData = async () => {
    setLoading(true);
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
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

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
      const defaultProd = products[0];
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
    const defaultProd = products[0];
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
      alert('Không thể tải chi tiết phiếu nhập');
    }
  };

  const handleCancelNote = async (note) => {
    if (
      !window.confirm(
        `Xác nhận hủy phiếu nhập ${note.code}? Hệ thống sẽ hoàn trừ tồn kho tương ứng nếu đủ điều kiện.`
      )
    )
      return;

    try {
      await apiClient.importNotes.cancel(note.id);
      alert('Đã hủy phiếu nhập và hoàn trừ tồn kho thành công!');
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể hủy phiếu nhập');
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
              ) : importNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-[var(--text-muted)]">
                    Chưa có phiếu nhập kho nào.
                  </td>
                </tr>
              ) : (
                importNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-[var(--wood-500)]">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">{n.supplier?.name || 'N/A'}</td>
                    <td className="py-3.5 px-4 font-mono text-xs text-[var(--text-secondary)]">
                      {new Date(n.note_date).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--text-secondary)]">{n.creator?.full_name || 'Hệ thống'}</td>
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Nhà cung cấp đối tác</label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
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
          <div className="border border-[var(--border-medium)] rounded-card p-3.5 bg-[var(--bg-surface-warm)]">
            <div className="flex items-center justify-between mb-2.5">
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

              {items.map((row, idx) => {
                const availableProducts = row.category_id
                  ? products.filter((p) => p.category_id === Number(row.category_id))
                  : products;

                return (
                  <div
                    key={idx}
                    style={{ zIndex: items.length - idx }}
                    className="flex flex-wrap sm:flex-nowrap items-center gap-2 bg-[var(--bg-surface)] p-2.5 rounded-input border border-[var(--border-medium)] relative"
                  >
                    {/* Chọn nhóm hàng */}
                    <div className="w-36 shrink-0">
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
                    <ProductSelect
                      products={availableProducts}
                      value={row.product_id}
                      onChange={(newId) => handleItemChange(idx, 'product_id', newId)}
                      placeholder="Gõ tên hoặc chữ cái đầu (VD: blv)..."
                      className="min-w-[170px]"
                    />

                    <div className="w-24">
                      <input
                        type="number"
                        min="1"
                        value={row.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                        placeholder="Số lượng"
                        className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input p-2 text-center font-mono font-bold text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)]"
                        required
                      />
                    </div>
                    <div className="w-32">
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
                    <div className="w-28 text-right font-mono font-bold text-xs text-[var(--text-primary)] pr-1">
                      {((Number(row.quantity) || 0) * (Number(row.unit_price) || 0)).toLocaleString()} đ
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveItemRow(idx)}
                      disabled={items.length <= 1}
                      className="text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn p-1.5 cursor-pointer disabled:opacity-30 disabled:pointer-events-none transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-[var(--border-medium)] flex items-center justify-between text-xs">
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
            <div className="grid grid-cols-2 gap-3 p-3.5 bg-[var(--bg-surface-warm)] rounded-card border border-[var(--border-medium)]">
              <div>
                <span className="text-[var(--text-muted)] block">Nhà cung cấp:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.supplier?.name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Ngày tạo:</span>
                <span className="font-semibold font-mono text-[var(--text-primary)]">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Người thực hiện:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.creator?.full_name || 'Hệ thống'}</span>
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
