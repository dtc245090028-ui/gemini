import React, { useState, useEffect } from 'react';
import {
  ArrowDownToLine,
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  FileText,
  Calendar,
  DollarSign,
  Ban,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export const ImportNotes = () => {
  const { user } = useAuth();
  const [importNotes, setImportNotes] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [supplierId, setSupplierId] = useState('');
  const [noteText, setNoteText] = useState('');
  const [items, setItems] = useState([]);
  const [formError, setFormError] = useState(null);

  // Detail Modal State
  const [selectedNote, setSelectedNote] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const canCreate = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';

  const fetchData = async () => {
    setLoading(true);
    try {
      const [notesRes, supRes, prodRes] = await Promise.all([
        apiClient.importNotes.getAll(),
        apiClient.suppliers.getAll(),
        apiClient.products.getAll({ limit: 100 }),
      ]);
      setImportNotes(Array.isArray(notesRes.data) ? notesRes.data : (notesRes.data.items || []));
      setSuppliers(Array.isArray(supRes.data) ? supRes.data : (supRes.data.items || []));
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
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
    setSupplierId(suppliers[0]?.id || '');
    setNoteText('');
    setItems([
      {
        product_id: products[0]?.id || '',
        quantity: 10,
        unit_price: Math.round((products[0]?.standard_price || 100000) * 0.75),
      },
    ]);
    setFormError(null);
    setIsCreateOpen(true);
  };

  const handleAddItemRow = () => {
    setItems([
      ...items,
      {
        product_id: products[0]?.id || '',
        quantity: 1,
        unit_price: Math.round((products[0]?.standard_price || 100000) * 0.75),
      },
    ]);
  };

  const handleRemoveItemRow = (idx) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleItemChange = (idx, field, val) => {
    const updated = [...items];
    updated[idx][field] = val;
    // Tự động gợi ý đơn giá nếu đổi sản phẩm
    if (field === 'product_id') {
      const p = products.find((prod) => prod.id === Number(val));
      if (p) {
        updated[idx].unit_price = Math.round(p.standard_price * 0.75);
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
    if (!window.confirm(`Bạn có chắc muốn HỦY phiếu nhập ${note.code}? Tồn kho tương ứng sẽ bị trừ đi an toàn.`)) return;
    try {
      await apiClient.importNotes.cancel(note.id);
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
          <h2 className="text-xl font-bold text-slate-900">Quản Lý Phiếu Nhập Kho</h2>
          <p className="text-xs text-slate-500 mt-0.5">Lập phiếu nhập hàng nhà cung cấp, tăng tồn kho và ghi nhận thẻ kho tự động</p>
        </div>

        {canCreate && (
          <button
            onClick={handleOpenCreate}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Lập Phiếu Nhập Mới</span>
          </button>
        )}
      </div>

      {/* Import Notes Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Mã phiếu</th>
                <th className="py-3 px-4">Nhà cung cấp</th>
                <th className="py-3 px-4">Ngày chứng từ</th>
                <th className="py-3 px-4">Người lập</th>
                <th className="py-3 px-4 text-right">Tổng tiền (đ)</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Đang tải danh sách phiếu nhập...
                  </td>
                </tr>
              ) : importNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Chưa có phiếu nhập kho nào.
                  </td>
                </tr>
              ) : (
                importNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-emerald-600">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-slate-800">{n.supplier?.name || 'N/A'}</td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(n.note_date).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">{n.creator?.full_name || 'Hệ thống'}</td>
                    <td className="py-3.5 px-4 text-right font-bold text-slate-800">
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
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {canCreate && n.status === 'COMPLETED' && (
                          <button
                            onClick={() => handleCancelNote(n)}
                            title="Hủy phiếu nhập (Hoàn trừ kho)"
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
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
        {formError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Đối tác Nhà cung cấp</label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                required
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Ghi chú chứng từ</label>
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="VD: Nhập lô bàn phím Akko đợt 2..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
              />
            </div>
          </div>

          {/* Dòng hàng chi tiết */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-slate-700">Danh sách hàng hóa nhập</label>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-emerald-600 hover:text-emerald-700 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng hàng</span>
              </button>
            </div>

            <div className="space-y-2 border border-slate-200 rounded-xl p-3 bg-slate-50/50">
              {items.map((row, idx) => {
                const subtotal = (Number(row.quantity) || 0) * (Number(row.unit_price) || 0);
                return (
                  <div key={idx} className="flex items-center gap-2 bg-white p-2.5 rounded-lg border border-slate-200 text-xs">
                    <div className="flex-1">
                      <select
                        value={row.product_id}
                        onChange={(e) => handleItemChange(idx, 'product_id', e.target.value)}
                        className="w-full px-2 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                      >
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.code} - {p.name} (Tồn: {p.current_stock})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="w-24">
                      <input
                        type="number"
                        min="1"
                        value={row.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                        placeholder="Số lượng"
                        className="w-full px-2 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-center"
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
                        placeholder="Đơn giá nhập"
                        className="w-full px-2 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-right"
                        required
                      />
                    </div>

                    <div className="w-28 text-right font-semibold text-slate-700">
                      {subtotal.toLocaleString()} đ
                    </div>

                    {items.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveItemRow(idx)}
                        className="text-slate-400 hover:text-rose-500 p-1 rounded cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Tổng tiền */}
          <div className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
            <span className="text-xs font-semibold text-emerald-800">Tổng giá trị đơn nhập:</span>
            <span className="text-base font-bold text-emerald-700">{totalCalculated.toLocaleString()} đ</span>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              Hủy
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors cursor-pointer"
            >
              Xác Nhận Nhập Kho
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Nhập */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi Tiết Phiếu Nhập: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <span className="text-slate-400">Nhà cung cấp:</span>{' '}
                <strong className="text-slate-800">{selectedNote.supplier?.name}</strong>
              </div>
              <div>
                <span className="text-slate-400">Ngày lập:</span>{' '}
                <strong className="text-slate-800">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</strong>
              </div>
              <div>
                <span className="text-slate-400">Người tạo:</span>{' '}
                <strong className="text-slate-800">{selectedNote.creator?.full_name || 'Hệ thống'}</strong>
              </div>
              <div>
                <span className="text-slate-400">Trạng thái:</span>{' '}
                <Badge variant={selectedNote.status === 'COMPLETED' ? 'green' : 'red'}>
                  {selectedNote.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã hủy'}
                </Badge>
              </div>
            </div>

            <table className="w-full text-left border border-slate-200 rounded-xl overflow-hidden">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Mã hàng</th>
                  <th className="py-2.5 px-3">Tên sản phẩm</th>
                  <th className="py-2.5 px-3 text-center">Số lượng</th>
                  <th className="py-2.5 px-3 text-right">Đơn giá nhập</th>
                  <th className="py-2.5 px-3 text-right">Thành tiền</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {selectedNote.details?.map((d) => (
                  <tr key={d.id}>
                    <td className="py-2.5 px-3 font-mono text-blue-600">{d.product?.code}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{d.product?.name}</td>
                    <td className="py-2.5 px-3 text-center font-bold text-slate-700">{d.quantity}</td>
                    <td className="py-2.5 px-3 text-right">{d.unit_price?.toLocaleString()} đ</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-800">{d.subtotal?.toLocaleString()} đ</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="text-right p-3 bg-slate-50 rounded-xl">
              <span className="text-xs text-slate-500 mr-2">Tổng thanh toán:</span>
              <span className="text-base font-bold text-emerald-600">{selectedNote.total_amount?.toLocaleString()} đ</span>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ImportNotes;
