import React, { useState, useEffect } from 'react';
import {
  ArrowUpFromLine,
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  Ban,
  AlertTriangle,
  UserCheck,
  Sparkles,
  Loader2,
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

  // AI Order Generation State
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState(null);

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
    setAiSuggestion(null);
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

  const handleGenerateAIOrder = async () => {
    setAiGenerating(true);
    setFormError(null);
    try {
      const res = await apiClient.ai.generateOrder();
      const order = res.data;
      setAiSuggestion(order);
      setRecipientName(order.recipient_name || '');
      setNoteText(order.note || '');

      setItems([
        {
          product_id: order.product_id,
          quantity: order.quantity,
          unit_price: order.unit_price,
        },
      ]);
      setIsCreateOpen(true);
    } catch (err) {
      console.error('Lỗi khi gọi AI sinh đơn hàng:', err);
      alert(err.response?.data?.detail || 'Không thể sinh đơn hàng AI vào lúc này.');
    } finally {
      setAiGenerating(false);
    }
  };

  const handleAddItemRow = () => {
    if (products.length === 0) return;
    const defaultProd = products[0];
    setItems([
      ...items,
      {
        product_id: defaultProd.id,
        quantity: 1,
        unit_price: defaultProd.standard_price,
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
    // Tự gợi ý giá chuẩn nếu đổi sản phẩm
    if (field === 'product_id') {
      const p = products.find((prod) => prod.id === Number(val));
      if (p) {
        updated[idx].unit_price = p.standard_price;
      }
    }
    setItems(updated);
  };

  // Defensive UI Check: Phát hiện bất kỳ dòng nào yêu cầu xuất > tồn hiện có
  const stockViolations = items
    .map((it, idx) => {
      const p = products.find((prod) => prod.id === Number(it.product_id));
      const requestedQty = Number(it.quantity) || 0;
      const currentStock = p ? p.current_stock : 0;
      if (p && requestedQty > currentStock) {
        return {
          row: idx + 1,
          productName: p.name,
          requestedQty,
          currentStock,
          shortage: requestedQty - currentStock,
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
    if (
      !window.confirm(
        `Xác nhận hủy phiếu xuất ${note.code}? Hệ thống sẽ hoàn trả lượng tồn vào kho.`
      )
    )
      return;

    try {
      await apiClient.exportNotes.cancel(note.id);
      alert('Đã hủy phiếu xuất và hoàn trả tồn kho thành công!');
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
          <h2 className="font-serif text-2xl font-bold text-wood-900 tracking-tight">Quản Lý Phiếu Xuất Kho</h2>
          <p className="text-xs text-wood-600 mt-0.5">Xuất kho bán lẻ, phân phối đối tác với cơ chế tự động chặn tồn kho âm (ACID)</p>
        </div>

        {canCreate && (
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleGenerateAIOrder}
              disabled={aiGenerating}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white rounded-btn text-xs font-semibold shadow-sm hover:shadow transition-all disabled:opacity-50 cursor-pointer"
              title="AI tự động đọc kịch bản khách hàng, phân tích tồn kho và lập đơn hàng đề xuất (có cache trong ngày)"
            >
              {aiGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin text-amber-200" />
              ) : (
                <Sparkles className="w-4 h-4 text-amber-200" />
              )}
              <span>{aiGenerating ? 'AI đang tạo đơn...' : '✨ Tạo Đơn Hàng (AI)'}</span>
            </button>

            <button
              onClick={handleOpenCreate}
              className="btn-primary"
            >
              <Plus className="w-4 h-4" />
              <span>Lập Phiếu Xuất Mới</span>
            </button>
          </div>
        )}
      </div>

      {/* Export Notes Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
              <tr>
                <th className="py-3.5 px-4">Mã phiếu</th>
                <th className="py-3.5 px-4">Người nhận / Khách hàng</th>
                <th className="py-3.5 px-4">Ngày xuất</th>
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
                    Đang tải danh sách phiếu xuất...
                  </td>
                </tr>
              ) : exportNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-wood-400">
                    Chưa có phiếu xuất kho nào.
                  </td>
                </tr>
              ) : (
                exportNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-wood-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-wood-700">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-wood-900">{n.recipient_name}</td>
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
                            title="Hủy phiếu xuất (Hoàn trả kho)"
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

      {/* Modal Lập Phiếu Xuất */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Lập Phiếu Xuất Kho Mới" maxWidth="max-w-3xl">
        {/* Hộp thông tin gợi ý từ AI nếu đơn được sinh bởi AI */}
        {aiSuggestion && (
          <div className="mb-4 p-3.5 bg-amber-50/90 border border-amber-300 rounded-xl space-y-2 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-amber-200">
              <div className="flex items-center gap-2 font-bold text-amber-950">
                <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  Đơn Hàng Đề Xuất Bởi AI ({aiSuggestion.provider === 'gemini' ? 'Google Gemini' : 'Heuristic Engine'})
                </span>
              </div>
              <div className="flex items-center gap-2">
                {aiSuggestion.is_cached && (
                  <span className="text-[10px] bg-amber-200/90 text-amber-900 px-2 py-0.5 rounded-full font-medium">
                    ⚡ Đã lưu cache trong ngày
                  </span>
                )}
                <span className="text-[10px] bg-wood-200 text-wood-800 px-2 py-0.5 rounded-full uppercase font-bold">
                  Khách: {aiSuggestion.role}
                </span>
              </div>
            </div>

            <p className="text-amber-900 text-[11px] leading-relaxed">
              <strong>Lý do AI chọn:</strong> {aiSuggestion.reason}
            </p>

            {aiSuggestion.discount_percent > 0 && (
              <div className="p-2.5 bg-white/90 rounded-lg border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                <span className="text-amber-950 font-medium">
                  💡 <strong>Gợi ý chiết khấu:</strong> Đề xuất giảm giá <strong>{aiSuggestion.discount_percent}%</strong> (Đơn giá tham khảo sau giảm: <strong>{Number(aiSuggestion.suggested_unit_price).toLocaleString()} đ</strong>)
                </span>
                <span className="text-wood-500 italic text-[10px]">
                  (Chỉ gợi ý - Không tự động trừ, bạn có thể chỉnh đơn giá tùy ý)
                </span>
              </div>
            )}
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-rust-50 border border-rust-200 rounded-xl flex items-center gap-2 text-xs text-rust-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rust-500" />
            <span>{formError}</span>
          </div>
        )}

        {/* Cảnh báo xuất âm Realtime (Defensive UI) */}
        {stockViolations.length > 0 && (
          <div className="mb-4 p-3.5 bg-rust-50 border border-rust-200 rounded-xl space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-rust-700">
              <AlertTriangle className="w-4 h-4 text-rust-500" />
              <span>Cảnh báo chống tồn kho âm (Defensive Guard Active):</span>
            </div>
            {stockViolations.map((v, i) => (
              <p key={i} className="text-[11px] text-rust-600 pl-6">
                • Dòng {v.row}: <strong>{v.productName}</strong> yêu cầu xuất {v.requestedQty} cái nhưng chỉ còn tồn kho {v.currentStock} cái (Thiếu hụt {v.shortage} cái).
              </p>
            ))}
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Người nhận / Đơn vị nhận hàng</label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="VD: Showroom Nội Thất Gỗ Quận 1..."
                className="input-wood"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Ghi chú mục đích xuất</label>
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="VD: Xuất hàng trưng bày mẫu..."
                className="input-wood"
              />
            </div>
          </div>

          {/* Chi tiết mặt hàng xuất */}
          <div className="border border-wood-200 rounded-xl p-3 bg-wood-50/50">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-wood-900 uppercase tracking-wider">Danh mục sản phẩm xuất kho</h4>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-wood-600 hover:text-wood-800 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng sản phẩm</span>
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {items.map((row, idx) => {
                const currentProd = products.find((p) => p.id === Number(row.product_id));
                const availableStock = currentProd ? currentProd.current_stock : 0;
                const isOverStock = (Number(row.quantity) || 0) > availableStock;

                return (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 p-2 rounded-xl border transition-colors ${
                      isOverStock ? 'bg-rust-50/60 border-rust-300' : 'bg-white border-wood-200'
                    }`}
                  >
                    <div className="flex-1">
                      <select
                        value={row.product_id}
                        onChange={(e) => handleItemChange(idx, 'product_id', e.target.value)}
                        className="w-full text-xs bg-wood-50/70 border border-wood-200 rounded-lg p-1.5 focus:outline-none"
                        required
                      >
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.code} - {p.name} (Tồn: {p.current_stock})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="w-28 text-center">
                      <div className="relative">
                        <input
                          type="number"
                          min="1"
                          value={row.quantity}
                          onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                          placeholder="SL"
                          className={`w-full text-xs rounded-lg p-1.5 text-center focus:outline-none border ${
                            isOverStock
                              ? 'bg-rust-50 border-rust-400 text-rust-700 font-bold'
                              : 'bg-wood-50/70 border-wood-200'
                          }`}
                          required
                        />
                      </div>
                      <span className="text-[10px] text-wood-500 block mt-0.5">Tồn: {availableStock}</span>
                    </div>

                    <div className="w-32">
                      <input
                        type="number"
                        min="0"
                        step="1000"
                        value={row.unit_price}
                        onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                        placeholder="Giá bán"
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
            </div>

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-wood-200 flex items-center justify-between text-xs">
              <span className="font-semibold text-wood-700">Tổng giá trị đơn xuất dự tính:</span>
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
              disabled={stockViolations.length > 0}
              className={`btn-primary ${stockViolations.length > 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Xác nhận & Xuất kho
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Xuất */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi Tiết Phiếu Xuất: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-wood-50 rounded-xl border border-wood-200">
              <div>
                <span className="text-wood-500 block">Người nhận / Đơn vị:</span>
                <span className="font-semibold text-wood-900">{selectedNote.recipient_name}</span>
              </div>
              <div>
                <span className="text-wood-500 block">Ngày xuất:</span>
                <span className="font-semibold text-wood-900">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span className="text-wood-500 block">Người lập phiếu:</span>
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
              <h5 className="font-bold text-wood-900 uppercase tracking-wider mb-2">Chi tiết sản phẩm đã xuất:</h5>
              <div className="border border-wood-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
                    <tr>
                      <th className="p-2.5">Sản phẩm</th>
                      <th className="p-2.5 text-center">Số lượng</th>
                      <th className="p-2.5 text-right">Đơn giá</th>
                      <th className="p-2.5 text-right">Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-wood-100">
                    {selectedNote.details?.map((d) => (
                      <tr key={d.id}>
                        <td className="p-2.5">
                          <p className="font-medium text-wood-900">{d.product_name}</p>
                          <p className="text-[11px] font-mono text-wood-500">{d.product_code}</p>
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

export default ExportNotes;
