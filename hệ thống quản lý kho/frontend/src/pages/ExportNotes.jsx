import React, { useState, useEffect } from 'react';
import {
  Plus,
  Trash2,
  Eye,
  AlertCircle,
  Ban,
  AlertTriangle,
  Sparkles,
  Loader2,
  Truck,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { draftStorage } from '../utils/draftStorage';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import ProductSelect from '../components/ProductSelect';
import Loader from '../components/Loader';
import useDelayedLoading from '../hooks/useDelayedLoading';

export const ExportNotes = () => {
  const { user } = useAuth();
  const [exportNotes, setExportNotes] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const showTableLoader = useDelayedLoading(loading);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [recipientName, setRecipientName] = useState('');
  const [noteText, setNoteText] = useState('');
  const [items, setItems] = useState([]);
  const [formError, setFormError] = useState(null);
  const [isDraftRestored, setIsDraftRestored] = useState(false);
  const [draftSavedTime, setDraftSavedTime] = useState('');

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
      const [expRes, prodRes, catRes] = await Promise.all([
        apiClient.exportNotes.getAll(),
        apiClient.products.getAll({ limit: 500 }),
        apiClient.categories.getAll(),
      ]);
      setExportNotes(Array.isArray(expRes.data) ? expRes.data : (expRes.data.items || []));
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
      setCategories(Array.isArray(catRes.data) ? catRes.data : (catRes.data.items || []));
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
    // Kiểm tra xem có bản nháp phiếu xuất trong vòng 24h không
    const draft = draftStorage.load(user?.username, 'export_note');
    if (draft && draft.data) {
      setRecipientName(draft.data.recipientName || '');
      setNoteText(draft.data.noteText || '');
      setAiSuggestion(null);
      setItems(
        draft.data.items && draft.data.items.length > 0
          ? draft.data.items
          : [
              {
                category_id: products[0]?.category_id || '',
                product_id: products[0]?.id || '',
                quantity: 1,
                unit_price: products[0]?.standard_price || 100000,
              },
            ]
      );
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setRecipientName('');
      setNoteText('');
      setAiSuggestion(null);
      const defaultProd = products[0];
      setItems([
        {
          category_id: defaultProd?.category_id || '',
          product_id: defaultProd?.id || '',
          quantity: 1,
          unit_price: defaultProd?.standard_price || 100000,
        },
      ]);
      setIsDraftRestored(false);
      setDraftSavedTime('');
    }
    setFormError(null);
    setIsCreateOpen(true);
  };

  // Tự động lưu bản nháp phiếu xuất ngầm khi người dùng nhập liệu
  useEffect(() => {
    if (isCreateOpen && user?.username) {
      const timer = setTimeout(() => {
        draftStorage.save(user.username, 'export_note', { recipientName, noteText, items });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isCreateOpen, recipientName, noteText, items, user?.username]);

  // Hủy bản nháp phiếu xuất
  const handleDiscardDraft = () => {
    draftStorage.clear(user?.username, 'export_note');
    setIsDraftRestored(false);
    setRecipientName('');
    setNoteText('');
    const defaultProd = products[0];
    setItems([
      {
        category_id: defaultProd?.category_id || '',
        product_id: defaultProd?.id || '',
        quantity: 1,
        unit_price: defaultProd?.standard_price || 100000,
      },
    ]);
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

      const matchedProd = products.find((p) => p.id === order.product_id);
      setItems([
        {
          category_id: matchedProd?.category_id || '',
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
        category_id: defaultProd?.category_id || '',
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

    // Xử lý khi thay đổi nhóm hàng: Tự động lọc và chọn mặt hàng phù hợp
    if (field === 'category_id') {
      const catId = val;
      const available = catId
        ? products.filter((p) => p.category_id === Number(catId))
        : products;
      if (available.length > 0 && !available.some((p) => p.id === Number(updated[idx].product_id))) {
        updated[idx].product_id = available[0].id;
        updated[idx].unit_price = available[0].standard_price;
      }
    }

    // Tự gợi ý giá chuẩn và đồng bộ nhóm hàng nếu đổi sản phẩm
    if (field === 'product_id') {
      const p = products.find((prod) => prod.id === Number(val));
      if (p) {
        updated[idx].unit_price = p.standard_price;
        if (p.category_id && updated[idx].category_id !== p.category_id) {
          updated[idx].category_id = p.category_id;
        }
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

    setIsSubmitting(true);
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
      // Xóa bản nháp khi tạo thành công
      draftStorage.clear(user?.username, 'export_note');
      setIsDraftRestored(false);
      setIsCreateOpen(false);
      fetchData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Không thể tạo phiếu xuất kho');
    } finally {
      setIsSubmitting(false);
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

  const renderStatusBadge = (status) => {
    switch (status) {
      case 'CONFIRMED':
        return <Badge variant="amber">Chờ xuất kho</Badge>;
      case 'SHIPPING':
        return <Badge variant="wood">Đang giao hàng</Badge>;
      case 'COMPLETED':
        return <Badge variant="success">Hoàn thành</Badge>;
      case 'CANCELLED':
        return <Badge variant="canceled">Đã hủy</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
    }
  };

  const handleShipNote = async (note) => {
    if (
      !window.confirm(
        `Xác nhận bắt đầu giao hàng cho phiếu xuất ${note.code}? Hệ thống sẽ trừ tồn kho thực tế và ghi Thẻ kho.`
      )
    )
      return;

    try {
      await apiClient.exportNotes.ship(note.id);
      alert(`Phiếu xuất ${note.code} đã bắt đầu giao hàng (đã trừ tồn kho)!`);
      fetchData();
      if (selectedNote?.id === note.id) {
        setIsDetailOpen(false);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể bắt đầu giao hàng');
    }
  };

  const handleCompleteNote = async (note) => {
    if (
      !window.confirm(
        `Xác nhận khách đã nhận đủ hàng và hoàn thành phiếu xuất ${note.code}?`
      )
    )
      return;

    try {
      await apiClient.exportNotes.complete(note.id);
      alert(`Phiếu xuất ${note.code} đã hoàn thành thành công!`);
      fetchData();
      if (selectedNote?.id === note.id) {
        setIsDetailOpen(false);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể hoàn thành phiếu xuất');
    }
  };

  const handleDeleteOrCancelNote = async (note) => {
    if (note.status === 'CONFIRMED') {
      if (
        !window.confirm(
          `Phiếu xuất ${note.code} chưa xuất kho. Bạn có chắc muốn hủy và xóa vĩnh viễn phiếu này không?`
        )
      )
        return;

      try {
        await apiClient.exportNotes.delete(note.id);
        alert(`Đã xóa vĩnh viễn phiếu xuất ${note.code}!`);
        fetchData();
        if (selectedNote?.id === note.id) {
          setIsDetailOpen(false);
        }
      } catch (err) {
        alert(err.response?.data?.detail || 'Không thể xóa phiếu xuất');
      }
    } else if (note.status === 'SHIPPING') {
      if (
        !window.confirm(
          `Xác nhận hủy đơn hàng đang giao ${note.code}? Hệ thống sẽ hoàn trả số lượng vào tồn kho và lưu vết phiếu đã hủy.`
        )
      )
        return;

      try {
        await apiClient.exportNotes.cancel(note.id);
        alert(`Đã hủy phiếu xuất ${note.code} và hoàn trả tồn kho thành công!`);
        fetchData();
        if (selectedNote?.id === note.id) {
          setIsDetailOpen(false);
        }
      } catch (err) {
        alert(err.response?.data?.detail || 'Không thể hủy phiếu xuất');
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[var(--text-primary)] tracking-tight">Phiếu xuất kho</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Xuất kho bán lẻ, phân phối đối tác với cơ chế tự động chặn tồn kho âm (ACID)</p>
        </div>

        {canCreate && (
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleGenerateAIOrder}
              disabled={aiGenerating}
              className="btn-ai min-w-[155px] justify-center"
              title="AI tự động đọc kịch bản khách hàng, phân tích tồn kho và lập đơn hàng đề xuất (có cache trong ngày)"
            >
              {aiGenerating ? (
                <Loader variant="inline" />
              ) : (
                <Sparkles className="w-4 h-4 text-[var(--semantic-ai-btn-text)]" />
              )}
              <span>{aiGenerating ? 'AI đang tạo đơn...' : 'Tạo đơn hàng AI'}</span>
            </button>

            <button
              onClick={handleOpenCreate}
              className="btn-primary"
            >
              <Plus className="w-4 h-4" />
              <span>Lập phiếu xuất mới</span>
            </button>
          </div>
        )}
      </div>

      {/* Export Notes Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-medium)]">
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
            <tbody className="divide-y divide-[var(--border-subtle)] font-sans">
              {showTableLoader ? (
                <Loader variant="table" columns={7} rows={8} />
              ) : exportNotes.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-[var(--text-muted)]">
                    Chưa có phiếu xuất kho nào.
                  </td>
                </tr>
              ) : (
                exportNotes.map((n) => (
                  <tr key={n.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-[var(--wood-500)]">{n.code}</td>
                    <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">{n.recipient_name}</td>
                    <td className="py-3.5 px-4 font-mono text-xs text-[var(--text-secondary)]">
                      {new Date(n.note_date).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--text-secondary)]">{n.creator?.full_name || 'Hệ thống'}</td>
                    <td className="py-3.5 px-4 text-right font-mono text-xs font-bold text-[var(--text-primary)]">
                      {n.total_amount?.toLocaleString()} đ
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {renderStatusBadge(n.status)}
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

                        {canCreate && n.status === 'CONFIRMED' && (
                          <>
                            <button
                              onClick={() => handleShipNote(n)}
                              title="Bắt đầu giao hàng (Trừ tồn kho)"
                              className="btn-secondary text-xs px-2.5 py-1"
                            >
                              <Truck className="w-3.5 h-3.5" />
                              <span>Giao hàng</span>
                            </button>
                            <button
                              onClick={() => handleDeleteOrCancelNote(n)}
                              title="Hủy & Xóa vĩnh viễn phiếu"
                              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn transition-colors cursor-pointer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}

                        {canCreate && n.status === 'SHIPPING' && (
                          <>
                            <button
                              onClick={() => handleCompleteNote(n)}
                              title="Xác nhận hoàn thành giao hàng"
                              className="btn-primary text-xs px-2.5 py-1"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Hoàn thành</span>
                            </button>
                            <button
                              onClick={() => handleDeleteOrCancelNote(n)}
                              title="Hủy đơn giao (Hoàn trả tồn kho)"
                              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn transition-colors cursor-pointer"
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          </>
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
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Lập phiếu xuất kho mới" maxWidth="max-w-3xl">
        {isDraftRestored && (
          <div className="mb-4 p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-card flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-primary)]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--semantic-ai)] shrink-0" />
              <span>
                <strong>Đã khôi phục bản nháp tự động</strong> (lưu lúc {draftSavedTime}). Hệ thống lưu tối đa 1 ngày.
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

        {/* Hộp thông tin gợi ý từ AI nếu đơn được sinh bởi AI */}
        {aiSuggestion && (
          <div className="mb-4 p-3.5 bg-[var(--bg-linen)] border border-[var(--border-subtle)] rounded-card space-y-2 text-xs text-[var(--text-primary)]">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-2 font-serif font-semibold text-[var(--text-primary)]">
                <Sparkles className="w-4 h-4 text-[var(--semantic-ai)] shrink-0" />
                <span>
                  Đơn hàng đề xuất bởi AI ({aiSuggestion.provider === 'gemini' ? 'Google Gemini' : 'Heuristic Engine'})
                </span>
              </div>
              <div className="flex items-center gap-2">
                {aiSuggestion.is_cached && (
                  <span className="text-xs bg-[var(--bg-card)] text-[var(--semantic-ai)] border border-[var(--border-subtle)] px-2 py-0.5 rounded-pill font-medium inline-flex items-center gap-1">
                    <Zap className="w-3 h-3 text-[var(--semantic-ai)]" />
                    Đã lưu cache trong ngày
                  </span>
                )}
                <span className="text-xs bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-subtle)] px-2 py-0.5 rounded-pill font-medium">
                  Khách: {aiSuggestion.role}
                </span>
              </div>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              <strong>Lý do AI chọn:</strong> {aiSuggestion.reason}
            </p>

            {aiSuggestion.discount_percent > 0 && (
              <div className="p-2.5 bg-[var(--bg-card)] rounded-btn border border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                <span className="text-[var(--text-primary)] font-medium inline-flex items-center gap-1.5 flex-wrap">
                  <Sparkles className="w-3.5 h-3.5 text-[var(--semantic-ai)] shrink-0" />
                  <strong>Gợi ý chiết khấu:</strong> Đề xuất giảm giá <strong>{aiSuggestion.discount_percent}%</strong> (Đơn giá tham khảo sau giảm: <span className="font-mono">{Number(aiSuggestion.suggested_unit_price).toLocaleString()} đ</span>)
                </span>
                <span className="text-[var(--text-muted)] italic text-xs">
                  (Chỉ gợi ý - Không tự động trừ, bạn có thể chỉnh đơn giá tùy ý)
                </span>
              </div>
            )}
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card flex items-center gap-2 text-xs text-[var(--semantic-alert)] font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        {/* Cảnh báo xuất âm Realtime (Defensive UI) */}
        {stockViolations.length > 0 && (
          <div className="mb-4 p-3.5 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--semantic-alert)]">
              <AlertTriangle className="w-4 h-4" />
              <span>Cảnh báo chống tồn kho âm (Defensive Guard Active):</span>
            </div>
            {stockViolations.map((v, i) => (
              <p key={i} className="text-xs text-[var(--text-primary)] pl-6">
                • Dòng {v.row}: <strong>{v.productName}</strong> yêu cầu xuất {v.requestedQty} cái nhưng chỉ còn tồn kho {v.currentStock} cái (Thiếu hụt {v.shortage} cái).
              </p>
            ))}
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Người nhận / Đơn vị nhận hàng</label>
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
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Ghi chú mục đích xuất</label>
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
          <div className="border border-[var(--border-subtle)] rounded-card p-3 bg-[var(--bg-linen)]">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">Danh mục sản phẩm xuất kho</h4>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs text-[var(--wood-accent)] hover:underline font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng sản phẩm</span>
              </button>
            </div>

            <div className="space-y-2 pr-1">
              {items.map((row, idx) => {
                const availableProducts = row.category_id
                  ? products.filter((p) => p.category_id === Number(row.category_id))
                  : products;
                const currentProd = products.find((p) => p.id === Number(row.product_id));
                const availableStock = currentProd ? currentProd.current_stock : 0;
                const isOverStock = (Number(row.quantity) || 0) > availableStock;

                return (
                  <div
                    key={idx}
                    style={{ zIndex: items.length - idx }}
                    className={`flex flex-wrap sm:flex-nowrap items-center gap-2 p-2 rounded-card border transition-colors relative ${
                      isOverStock ? 'bg-[var(--semantic-alert)]/10 border-[var(--semantic-alert)]' : 'bg-[var(--bg-card)] border-[var(--border-subtle)]'
                    }`}
                  >
                    {/* Chọn nhóm hàng */}
                    <div className="w-36 shrink-0">
                      <select
                        value={row.category_id || ''}
                        onChange={(e) => handleItemChange(idx, 'category_id', e.target.value)}
                        className="w-full text-xs input-wood p-1.5"
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

                    <div className="w-28 text-center">
                      <div className="relative">
                        <input
                          type="number"
                          min="1"
                          value={row.quantity}
                          onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                          placeholder="SL"
                          className={`w-full text-xs rounded-btn p-1.5 text-center focus:outline-none border ${
                            isOverStock
                              ? 'bg-[var(--semantic-alert)]/10 border-[var(--semantic-alert)] text-[var(--semantic-alert)] font-bold'
                              : 'input-wood'
                          }`}
                          required
                        />
                      </div>
                      <span className="text-xs text-[var(--text-muted)] block mt-0.5">Tồn: {availableStock}</span>
                    </div>

                    <div className="w-32">
                      <input
                        type="number"
                        min="0"
                        step="1000"
                        value={row.unit_price}
                        onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                        placeholder="Giá bán"
                        className="w-full text-xs input-wood p-1.5 text-right font-mono"
                        required
                      />
                    </div>

                    <div className="w-28 text-right font-mono font-medium text-xs text-[var(--text-primary)] pr-1">
                      {((Number(row.quantity) || 0) * (Number(row.unit_price) || 0)).toLocaleString()} đ
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRemoveItemRow(idx)}
                      disabled={items.length <= 1}
                      className="text-[var(--text-muted)] hover:text-[var(--semantic-alert)] disabled:opacity-30 p-1 cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-between text-xs">
              <span className="font-semibold text-[var(--text-secondary)]">Tổng giá trị đơn xuất dự tính:</span>
              <span className="font-serif font-bold text-base text-[var(--text-primary)]">{totalCalculated.toLocaleString()} đ</span>
            </div>
          </div>

          <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-card text-xs text-[var(--text-secondary)] flex items-start sm:items-center gap-2">
            <span className="font-bold text-[var(--text-primary)] shrink-0">Quy trình xuất kho:</span>
            <span>Phiếu mới lập sẽ ở trạng thái <strong>Chờ xuất kho</strong> (chưa trừ tồn kho). Tồn kho và Thẻ kho chỉ được ghi nhận khi bạn bấm <strong>Giao hàng</strong>.</span>
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
              disabled={stockViolations.length > 0 || isSubmitting}
              className={`btn-primary flex items-center justify-center gap-2 min-w-[170px] ${stockViolations.length > 0 || isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isSubmitting && <Loader variant="inline" />}
              <span>{isSubmitting ? 'Đang lập phiếu...' : 'Lập phiếu (Xác nhận)'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Xem Chi Tiết Phiếu Xuất */}
      <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title={`Chi tiết phiếu xuất: ${selectedNote?.code}`}>
        {selectedNote && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-[var(--bg-linen)] rounded-card border border-[var(--border-subtle)]">
              <div>
                <span className="text-[var(--text-muted)] block text-xs">Người nhận / Đơn vị:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.recipient_name}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block text-xs">Ngày xuất:</span>
                <span className="font-semibold text-[var(--text-primary)]">{new Date(selectedNote.note_date).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block text-xs">Người lập phiếu:</span>
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.creator?.full_name || 'Hệ thống'}</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block text-xs">Trạng thái:</span>
                {renderStatusBadge(selectedNote.status)}
              </div>
            </div>

            <div>
              <h5 className="font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2 text-xs">Chi tiết sản phẩm đã xuất:</h5>
              <div className="border border-[var(--border-subtle)] rounded-card overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[var(--bg-linen)] text-[var(--text-secondary)] font-medium border-b border-[var(--border-subtle)]">
                    <tr>
                      <th className="p-2.5">Sản phẩm</th>
                      <th className="p-2.5 text-center">Số lượng</th>
                      <th className="p-2.5 text-right">Đơn giá</th>
                      <th className="p-2.5 text-right">Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-card)]">
                    {selectedNote.details?.map((d) => (
                      <tr key={d.id}>
                        <td className="p-2.5">
                          <p className="font-medium text-[var(--text-primary)]">{d.product_name}</p>
                        </td>
                        <td className="p-2.5 text-center font-bold text-[var(--text-primary)] font-mono">{d.quantity}</td>
                        <td className="p-2.5 text-right font-mono text-[var(--text-secondary)]">{d.unit_price?.toLocaleString()} đ</td>
                        <td className="p-2.5 text-right font-mono font-bold text-[var(--text-primary)]">{d.subtotal?.toLocaleString()} đ</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-[var(--bg-linen)] font-bold border-t border-[var(--border-subtle)]">
                    <tr>
                      <td colSpan="3" className="p-2.5 text-right text-[var(--text-secondary)]">Tổng cộng:</td>
                      <td className="p-2.5 text-right font-serif font-bold text-sm text-[var(--text-primary)]">{selectedNote.total_amount?.toLocaleString()} đ</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Quick Actions in Detail Modal */}
            {canCreate && (selectedNote.status === 'CONFIRMED' || selectedNote.status === 'SHIPPING') && (
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-subtle)]">
                {selectedNote.status === 'CONFIRMED' && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleDeleteOrCancelNote(selectedNote)}
                      className="btn-outline text-[var(--semantic-alert)] border-[var(--semantic-alert)]/40 hover:bg-[var(--semantic-alert)]/10"
                    >
                      Hủy & xóa phiếu
                    </button>
                    <button
                      type="button"
                      onClick={() => handleShipNote(selectedNote)}
                      className="btn-primary inline-flex items-center gap-1.5"
                    >
                      <Truck className="w-4 h-4" />
                      <span>Bắt đầu giao hàng (Trừ kho)</span>
                    </button>
                  </>
                )}
                {selectedNote.status === 'SHIPPING' && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleDeleteOrCancelNote(selectedNote)}
                      className="btn-outline text-[var(--semantic-alert)] border-[var(--semantic-alert)]/40 hover:bg-[var(--semantic-alert)]/10"
                    >
                      Hủy đơn & hoàn kho
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCompleteNote(selectedNote)}
                      className="btn-secondary inline-flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Xác nhận hoàn thành</span>
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ExportNotes;
