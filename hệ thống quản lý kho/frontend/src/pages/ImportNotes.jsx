import React, { useState, useEffect } from 'react';
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

export const ImportNotes = () => {
  const { user } = useAuth();
  const [importNotes, setImportNotes] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
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
    setFormError(null);

    if (items.length === 0) {
      setFormError('Vui lòng thêm ít nhất một mặt hàng nhập kho');
      return;
    }

    try {
      await apiClient.importNotes.create({
        supplier_id: Number(supplierId),
        note: noteText,
        details: items.map((it) => ({
          product_id: Number(it.product_id),
          quantity: Number(it.quantity),
          unit_price: Number(it.unit_price),
        })),
      });
      // Xóa bản nháp khi đã lưu thành công
      draftStorage.clear(user?.username, 'import_note');
      setIsDraftRestored(false);
      setIsCreateOpen(false);
      fetchData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Không thể tạo phiếu nhập kho');
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
          <h2 className="font-serif text-2xl font-bold text-wood-900 tracking-tight">Quản Lý Phiếu Nhập Kho</h2>
          <p className="text-xs text-wood-600 mt-0.5">Lập phiếu nhập hàng nhà cung cấp, tăng tồn kho và ghi nhận thẻ kho tự động</p>
        </div>

        {canCreate && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Lập Phiếu Nhập Mới</span>
          </button>
        )}
      </div>

      {/* Import Notes Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
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
            <tbody className="divide-y divide-wood-100">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-wood-400">
                    Đang tải danh sách phiếu nhập...
                  </td>
                </tr>
              ) : importNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-wood-400">
                    Chưa có phiếu nhập kho nào.
                  </td>
                </tr>
              ) : (
                importNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-wood-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-wood-700">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-wood-900">{n.supplier?.name || 'N/A'}</td>
                    <td className="py-3.5 px-4 text-wood-600">
                      {new Date(n.note_date).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-wood-600">{n.creator?.full_name || 'Hệ thống'}</td>
                    <td className="py-3.5 px-4 text-right font-bold text-wood-900">
                      {n.total_amount?.toLocaleString()} đ
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={n.status === 'COMPLETED' ? 'green' : 'red'}>
                        {n.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã hủy'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleViewDetail(n)}
                          title="Xem chi tiết"
                          className="p-1.5 text-wood-400 hover:text-wood-800 hover:bg-wood-100 rounded-btn transition-colors cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {canCreate && n.status === 'COMPLETED' && (
                          <button
                            onClick={() => handleCancelNote(n)}
                            title="Hủy phiếu nhập (Hoàn trừ kho)"
                            className="p-1.5 text-wood-400 hover:text-rust-600 hover:bg-rust-50 rounded-btn transition-colors cursor-pointer"
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
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Lập Phiếu Nhập Kho Mới" maxWidth="max-w-3xl">
        {isDraftRestored && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-300 rounded-xl flex flex-wrap items-center justify-between gap-2 text-xs text-amber-950">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <strong>Đã khôi phục bản nháp tự động</strong> (lưu lúc {draftSavedTime}). Hệ thống lưu tối đa 1 ngày.
              </span>
            </div>
            <button
              type="button"
              onClick={handleDiscardDraft}
              className="text-xs font-bold text-rust-600 hover:text-rust-800 underline cursor-pointer shrink-0"
              title="Xóa nội dung nháp này để nhập từ đầu"
            >
              Xóa bản nháp
            </button>
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-rust-50 border border-rust-200 rounded-xl flex items-center gap-2 text-xs text-rust-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rust-500" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Nhà cung cấp đối tác</label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="input-wood"
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
              <label className="block text-xs font-semibold text-wood-800 mb-1">Ghi chú chứng từ</label>
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
          <div className="border border-wood-200 rounded-xl p-3 bg-wood-50/50">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-wood-900 uppercase tracking-wider">Danh mục sản phẩm nhập kho</h4>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-wood-600 hover:text-wood-800 font-semibold flex items-center gap-1 cursor-pointer"
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
                    className="flex flex-wrap sm:flex-nowrap items-center gap-2 bg-white p-2 rounded-xl border border-wood-200 relative"
                  >
                    {/* Chọn nhóm hàng */}
                    <div className="w-36 shrink-0">
                      <select
                        value={row.category_id || ''}
                        onChange={(e) => handleItemChange(idx, 'category_id', e.target.value)}
                        className="w-full text-xs bg-wood-50/70 border border-wood-200 rounded-lg p-1.5 focus:outline-none"
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
                        className="w-full text-xs bg-wood-50/70 border border-wood-200 rounded-lg p-1.5 text-center focus:outline-none"
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
                        className="w-full text-xs bg-wood-50/70 border border-wood-200 rounded-lg p-1.5 text-right focus:outline-none"
                        required
                      />
                    </div>
                    <div className="w-28 text-right font-medium text-xs text-wood-900 pr-1">
                      {((Number(row.quantity) || 0) * (Number(row.unit_price) || 0)).toLocaleString()} đ
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveItemRow(idx)}
                      disabled={items.length <= 1}
                      className="text-wood-400 hover:text-rust-500 disabled:opacity-30 p-1 cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-wood-200 flex items-center justify-between text-xs">
              <span className="font-semibold text-wood-700">Tổng giá trị đơn nhập dự tính:</span>
              <span className="font-bold text-base text-wood-900">{totalCalculated.toLocaleString()} đ</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="btn-outline"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              className="btn-primary"
            >
              Lưu & Nhập kho
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Nhập */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi Tiết Phiếu Nhập: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-wood-50 rounded-xl border border-wood-200">
              <div>
                <span className="text-wood-500 block">Nhà cung cấp:</span>
                <span className="font-semibold text-wood-900">{selectedNote.supplier?.name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-wood-500 block">Ngày tạo:</span>
                <span className="font-semibold text-wood-900">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span className="text-wood-500 block">Người thực hiện:</span>
                <span className="font-semibold text-wood-900">{selectedNote.creator?.full_name || 'Hệ thống'}</span>
              </div>
              <div>
                <span className="text-wood-500 block">Trạng thái:</span>
                <Badge variant={selectedNote.status === 'COMPLETED' ? 'green' : 'red'}>
                  {selectedNote.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã hủy'}
                </Badge>
              </div>
            </div>

            <div>
              <h5 className="font-bold text-wood-900 uppercase tracking-wider mb-2">Chi tiết sản phẩm đã nhập:</h5>
              <div className="border border-wood-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
                    <tr>
                      <th className="p-2.5">Sản phẩm</th>
                      <th className="p-2.5 text-center">Số lượng</th>
                      <th className="p-2.5 text-right">Đơn giá nhập</th>
                      <th className="p-2.5 text-right">Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-wood-100">
                    {selectedNote.details?.map((d) => (
                      <tr key={d.id}>
                        <td className="p-2.5">
                          <p className="font-medium text-wood-900">{d.product_name}</p>
                        </td>
                        <td className="p-2.5 text-center font-bold text-wood-900">{d.quantity}</td>
                        <td className="p-2.5 text-right text-wood-700">{d.unit_price?.toLocaleString()} đ</td>
                        <td className="p-2.5 text-right font-bold text-wood-900">{d.subtotal?.toLocaleString()} đ</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-wood-50 font-bold border-t border-wood-200">
                    <tr>
                      <td colSpan="3" className="p-2.5 text-right text-wood-700">Tổng cộng:</td>
                      <td className="p-2.5 text-right text-wood-900">{selectedNote.total_amount?.toLocaleString()} đ</td>
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
