import React, { useState, useEffect } from 'react';
import {
  ArrowUpFromLine,
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  AlertTriangle,
  Ban,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export const ExportNotes = () => {
  const { user } = useAuth();
  const [exportNotes, setExportNotes] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [recipientName, setRecipientName] = useState('');
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
      const [expRes, prodRes] = await Promise.all([
        apiClient.exportNotes.getAll(),
        apiClient.products.getAll({ limit: 100 }),
      ]);
      setExportNotes(Array.isArray(expRes.data) ? expRes.data : (expRes.data.items || []));
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
    } catch (err) {
      console.error('Lỗi tải phiếu xuất:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenCreate = () => {
    setRecipientName('');
    setNoteText('');
    setItems([
      {
        product_id: products[0]?.id || '',
        quantity: 1,
        unit_price: products[0]?.standard_price || 100000,
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
        unit_price: products[0]?.standard_price || 100000,
      },
    ]);
  };

  const handleRemoveItemRow = (idx) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const handleItemChange = (idx, field, val) => {
    const updated = [...items];
    updated[idx][field] = val;
    if (field === 'product_id') {
      const p = products.find((prod) => prod.id === Number(val));
      if (p) {
        updated[idx].unit_price = p.standard_price;
      }
    }
    setItems(updated);
  };

  // Kiểm tra vi phạm tồn kho âm theo thời gian thực trên Client (Defensive UI)
  const stockViolations = items
    .map((it, idx) => {
      const p = products.find((prod) => prod.id === Number(it.product_id));
      const currentStock = p ? p.current_stock : 0;
      const requestedQty = Number(it.quantity) || 0;
      if (requestedQty > currentStock) {
        return {
          row: idx + 1,
          productName: p?.name || 'Sản phẩm',
          currentStock,
          requestedQty,
          deficit: requestedQty - currentStock,
        };
      }
      return null;
    })
    .filter(Boolean);

  const totalCalculated = items.reduce(
    (acc, it) => acc + (Number(it.quantity) || 0) * (Number(it.unit_price) || 0),
    0
  );

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (items.length === 0) {
      setFormError('Vui lòng thêm ít nhất một mặt hàng xuất kho');
      return;
    }

    if (stockViolations.length > 0) {
      setFormError(
        `Chặn xuất âm: Dòng ${stockViolations[0].row} (${stockViolations[0].productName}) yêu cầu xuất ${stockViolations[0].requestedQty} nhưng chỉ còn tồn ${stockViolations[0].currentStock}!`
      );
      return;
    }

    try {
      await apiClient.exportNotes.create({
        recipient_name: recipientName,
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
      setFormError(err.response?.data?.detail || 'Không thể tạo phiếu xuất kho');
    }
  };

  const handleViewDetail = async (note) => {
    try {
      const res = await apiClient.exportNotes.getById(note.id);
      setSelectedNote(res.data);
      setIsDetailOpen(true);
    } catch (err) {
      alert('Không thể tải chi tiết phiếu xuất');
    }
  };

  const handleCancelNote = async (note) => {
    if (!window.confirm(`Bạn có chắc muốn HỦY phiếu xuất ${note.code}? Tồn kho sẽ được hoàn trả lại.`)) return;
    try {
      await apiClient.exportNotes.cancel(note.id);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể hủy phiếu xuất');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Quản Lý Phiếu Xuất Kho</h2>
          <p className="text-xs text-slate-500 mt-0.5">Xuất kho bán lẻ, phân phối đối tác với cơ chế tự động chặn tồn kho âm (ACID)</p>
        </div>

        {canCreate && (
          <button
            onClick={handleOpenCreate}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Lập Phiếu Xuất Mới</span>
          </button>
        )}
      </div>

      {/* Export Notes Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Mã phiếu</th>
                <th className="py-3 px-4">Người nhận / Khách hàng</th>
                <th className="py-3 px-4">Ngày xuất</th>
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
                    Đang tải danh sách phiếu xuất...
                  </td>
                </tr>
              ) : exportNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Chưa có phiếu xuất kho nào.
                  </td>
                </tr>
              ) : (
                exportNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-indigo-600">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-slate-800">{n.recipient_name}</td>
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
                            title="Hủy phiếu xuất (Hoàn trả kho)"
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

      {/* Modal Lập Phiếu Xuất */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Lập Phiếu Xuất Kho (Chống Tồn Âm)" maxWidth="max-w-3xl">
        {formError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{formError}</span>
          </div>
        )}

        {/* Cảnh báo tồn âm tức thời */}
        {stockViolations.length > 0 && (
          <div className="mb-4 p-3.5 bg-rose-50 border-2 border-rose-300 rounded-xl space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-rose-700">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>CẢNH BÁO: Phát hiện số lượng xuất vượt quá tồn kho hiện có!</span>
            </div>
            {stockViolations.map((v, i) => (
              <p key={i} className="text-xs text-rose-600 pl-6">
                • Dòng {v.row}: <strong>{v.productName}</strong> chỉ còn tồn <strong>{v.currentStock}</strong>, yêu cầu xuất <strong>{v.requestedQty}</strong> (Thiếu {v.deficit} sản phẩm).
              </p>
            ))}
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Người nhận / Khách hàng</label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="VD: Công ty CP Alpha, Trường FPT..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Ghi chú xuất kho</label>
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="VD: Xuất hàng theo hợp đồng số 05..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
              />
            </div>
          </div>

          {/* Dòng hàng chi tiết */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-slate-700">Danh sách hàng hóa xuất</label>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng hàng</span>
              </button>
            </div>

            <div className="space-y-2 border border-slate-200 rounded-xl p-3 bg-slate-50/50">
              {items.map((row, idx) => {
                const p = products.find((prod) => prod.id === Number(row.product_id));
                const currentStock = p ? p.current_stock : 0;
                const isOverStock = Number(row.quantity) > currentStock;
                const subtotal = (Number(row.quantity) || 0) * (Number(row.unit_price) || 0);

                return (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs transition-colors ${
                      isOverStock ? 'bg-rose-50/80 border-rose-300' : 'bg-white border-slate-200'
                    }`}
                  >
                    <div className="flex-1">
                      <select
                        value={row.product_id}
                        onChange={(e) => handleItemChange(idx, 'product_id', e.target.value)}
                        className="w-full px-2 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                      >
                        {products.map((prod) => (
                          <option key={prod.id} value={prod.id}>
                            {prod.code} - {prod.name} (Tồn: {prod.current_stock} {prod.unit})
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
                        className={`w-full px-2 py-1.5 rounded-lg text-xs text-center border ${
                          isOverStock
                            ? 'bg-rose-100 border-rose-400 text-rose-700 font-bold'
                            : 'bg-slate-50 border-slate-200'
                        }`}
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
                        placeholder="Đơn giá xuất"
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
          <div className="flex items-center justify-between p-3 bg-indigo-50 border border-indigo-200 rounded-xl">
            <span className="text-xs font-semibold text-indigo-800">Tổng giá trị đơn xuất:</span>
            <span className="text-base font-bold text-indigo-700">{totalCalculated.toLocaleString()} đ</span>
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
              disabled={stockViolations.length > 0}
              className={`px-4 py-2 rounded-xl text-xs font-semibold shadow-sm transition-colors cursor-pointer ${
                stockViolations.length > 0
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              }`}
            >
              {stockViolations.length > 0 ? 'Bị Chặn (Xuất Quá Tồn)' : 'Xác Nhận Xuất Kho'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Xuất */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi Tiết Phiếu Xuất: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <span className="text-slate-400">Người nhận:</span>{' '}
                <strong className="text-slate-800">{selectedNote.recipient_name}</strong>
              </div>
              <div>
                <span className="text-slate-400">Ngày xuất:</span>{' '}
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
                  <th className="py-2.5 px-3 text-right">Đơn giá xuất</th>
                  <th className="py-2.5 px-3 text-right">Thành tiền</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {selectedNote.details?.map((d) => (
                  <tr key={d.id}>
                    <td className="py-2.5 px-3 font-mono text-indigo-600">{d.product?.code}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{d.product?.name}</td>
                    <td className="py-2.5 px-3 text-center font-bold text-slate-700">{d.quantity}</td>
                    <td className="py-2.5 px-3 text-right">{d.unit_price?.toLocaleString()} đ</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-800">{d.subtotal?.toLocaleString()} đ</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="text-right p-3 bg-slate-50 rounded-xl">
              <span className="text-xs text-slate-500 mr-2">Tổng giá trị phiếu:</span>
              <span className="text-base font-bold text-indigo-600">{selectedNote.total_amount?.toLocaleString()} đ</span>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ExportNotes;
