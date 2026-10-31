import React, { useState, useEffect, useRef } from 'react';
import { stockEvents } from '../utils/stockEvents';
import { usePageSync } from '../hooks/usePageSync';
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
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';

export const ExportNotes = ({ isActive = true }) => {
  const { user } = useAuth();
  const { showSuccess, showError, showInfo } = useToast();
  const { confirm } = useConfirm();
  const [exportNotes, setExportNotes] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
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

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState('');
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

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [expRes, prodRes, catRes, supRes] = await Promise.all([
        apiClient.exportNotes.getAll(),
        apiClient.products.getAll({ limit: 500 }),
        apiClient.categories.getAll(),
        apiClient.suppliers.getAll(),
      ]);
      setExportNotes(Array.isArray(expRes.data) ? expRes.data : (expRes.data.items || []));
      setProducts(Array.isArray(prodRes.data) ? prodRes.data : (prodRes.data.items || []));
      setCategories(Array.isArray(catRes.data) ? catRes.data : (catRes.data.items || []));
      setSuppliers(Array.isArray(supRes.data) ? supRes.data : (supRes.data.items || []));
    } catch (err) {
      console.error('Lỗi tải phiếu xuất:', err);
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
    resource: ['export_notes', 'products'],
  });

  const handleOpenCreate = () => {
    isSubmittingRef.current = false;
    const newKey = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `ek-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setIdempotencyKey(newKey);

    // Kiểm tra xem có bản nháp phiếu xuất trong vòng 24h không
    const draft = draftStorage.load(user?.username, 'export_note');
    if (draft && draft.data) {
      setRecipientName(draft.data.recipientName || '');
      setNoteText(draft.data.noteText || '');
      setAiSuggestion(null);
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
            unit_price: it.unit_price !== undefined ? it.unit_price : (prod?.standard_price || 0),
          };
        });
      setItems(
        validItems.length > 0
          ? validItems
          : [
              {
                category_id: '',
                supplier_id: '',
                product_id: '',
                quantity: 1,
                unit_price: 0,
              },
            ]
      );
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setRecipientName('');
      setNoteText('');
      setAiSuggestion(null);
      setItems([
        {
          category_id: '',
          supplier_id: '',
          product_id: '',
          quantity: 1,
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
    setItems([
      {
        category_id: '',
        supplier_id: '',
        product_id: '',
        quantity: 1,
        unit_price: 0,
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
          supplier_id: matchedProd?.supplier_id || '',
          product_id: order.product_id,
          quantity: order.quantity,
          unit_price: order.unit_price,
        },
      ]);
      setIsCreateOpen(true);
    } catch (err) {
      console.error('Lỗi khi gọi AI sinh đơn hàng:', err);
      showError(err.response?.data?.detail || 'Không thể sinh đơn hàng AI vào lúc này.');
    } finally {
      setAiGenerating(false);
    }
  };

  const handleAddItemRow = () => {
    setItems([
      ...items,
      {
        category_id: '',
        supplier_id: '',
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
          updated[idx].unit_price = p.standard_price || 0;
          // Tự động điền ngược Nhóm hàng & Nhà cung cấp
          if (p.category_id) {
            updated[idx].category_id = p.category_id;
          }
          if (p.supplier_id) {
            updated[idx].supplier_id = p.supplier_id;
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
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setFormError(null);

    if (items.length === 0) {
      setFormError('Vui lòng thêm ít nhất một mặt hàng xuất kho');
      isSubmittingRef.current = false;
      return;
    }

    const unselected = items.some((it) => !it.product_id);
    if (unselected) {
      setFormError('Vui lòng chọn sản phẩm cho tất cả các dòng trước khi lưu phiếu');
      isSubmittingRef.current = false;
      return;
    }

    if (stockViolations.length > 0) {
      setFormError(
        `Chặn xuất âm: Dòng ${stockViolations[0].row} (${stockViolations[0].productName}) yêu cầu xuất ${stockViolations[0].requestedQty} nhưng chỉ còn tồn ${stockViolations[0].currentStock}!`
      );
      isSubmittingRef.current = false;
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.exportNotes.create(
        {
          recipient_name: recipientName,
          note: noteText,
          details: items.map((it) => ({
            product_id: Number(it.product_id),
            quantity: Number(it.quantity),
            unit_price: Number(it.unit_price),
          })),
        },
        idempotencyKey ? { headers: { 'X-Idempotency-Key': idempotencyKey } } : {}
      );
      // Xóa bản nháp khi tạo thành công
      draftStorage.clear(user?.username, 'export_note');
      setIsDraftRestored(false);
      setIsCreateOpen(false);
      setIdempotencyKey('');
      fetchData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Không thể tạo phiếu xuất kho');
    } finally {
      setIsSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  const handleViewDetail = async (note) => {
    try {
      const res = await apiClient.exportNotes.getById(note.id);
      setSelectedNote(res.data);
      setIsDetailOpen(true);
    } catch (err) {
      showError('Không thể tải chi tiết phiếu xuất');
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
    const res = await confirm({
      title: `Bắt đầu giao hàng cho phiếu ${note.code}?`,
      message: 'Hệ thống sẽ trừ tồn kho thực tế của các mặt hàng và ghi nhận biến động tức thời vào Sổ cái Thẻ kho.',
      confirmText: 'Bắt đầu giao hàng',
      cancelText: 'Giữ lại',
      variant: 'primary',
    });
    if (!res.confirmed) return;

    try {
      await apiClient.exportNotes.ship(note.id);
      showSuccess(`Phiếu xuất ${note.code} đã bắt đầu giao hàng (đã trừ tồn kho)!`);
      fetchData();
      if (selectedNote?.id === note.id) {
        setIsDetailOpen(false);
      }
    } catch (err) {
      showError(err.response?.data?.detail || 'Không thể bắt đầu giao hàng');
    }
  };

  const handleCompleteNote = async (note) => {
    const res = await confirm({
      title: `Hoàn thành phiếu xuất ${note.code}?`,
      message: 'Xác nhận khách hàng đã nhận đủ hàng và hoàn tất quy trình phân phối cho đơn này.',
      confirmText: 'Xác nhận hoàn thành',
      cancelText: 'Giữ lại',
      variant: 'primary',
    });
    if (!res.confirmed) return;

    try {
      await apiClient.exportNotes.complete(note.id);
      showSuccess(`Phiếu xuất ${note.code} đã hoàn thành thành công!`);
      fetchData();
      if (selectedNote?.id === note.id) {
        setIsDetailOpen(false);
      }
    } catch (err) {
      showError(err.response?.data?.detail || 'Không thể hoàn thành phiếu xuất');
    }
  };

  const handleDeleteOrCancelNote = async (note) => {
    if (note.status === 'CONFIRMED') {
      const res = await confirm({
        title: `Xóa phiếu xuất ${note.code}?`,
        message: `Phiếu xuất ${note.code} chưa xuất kho. Bạn có chắc muốn hủy và xóa vĩnh viễn phiếu này khỏi hệ thống không?`,
        confirmText: 'Xác nhận xóa',
        cancelText: 'Giữ lại',
        variant: 'danger',
      });
      if (!res.confirmed) return;

      try {
        await apiClient.exportNotes.delete(note.id);
        showSuccess(`Đã xóa vĩnh viễn phiếu xuất ${note.code}!`);
        fetchData();
        if (selectedNote?.id === note.id) {
          setIsDetailOpen(false);
        }
      } catch (err) {
        showError(err.response?.data?.detail || 'Không thể xóa phiếu xuất');
      }
    } else if (note.status === 'SHIPPING') {
      const res = await confirm({
        title: `Hủy đơn hàng ${note.code}?`,
        message: 'Hệ thống sẽ hoàn trả số lượng vào tồn kho, ghi nhận Thẻ kho điều chỉnh và lưu vết phiếu đã hủy.',
        confirmText: 'Xác nhận hủy',
        cancelText: 'Giữ lại',
        variant: 'danger',
        showReasonInput: true,
        reasonPlaceholder: 'Nhập lý do hủy (ví dụ: Khách đổi ý, sai địa chỉ giao, sản phẩm lỗi...)...',
      });
      if (!res.confirmed) return;

      try {
        await apiClient.exportNotes.cancel(note.id, res.reason);
        showSuccess(`Đã hủy phiếu xuất ${note.code} và hoàn trả tồn kho thành công!`);
        fetchData();
        if (selectedNote?.id === note.id) {
          setIsDetailOpen(false);
        }
      } catch (err) {
        showError(err.response?.data?.detail || 'Không thể hủy phiếu xuất');
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
                    <td className="py-3.5 px-4 text-[var(--text-secondary)]">{n.creator_name || n.creator?.full_name || 'Hệ thống'}</td>
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
      <Modal isOpen={isCreateOpen} onClose={handleCloseCreate} title="Lập phiếu xuất kho mới" maxWidth="max-w-4xl">
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
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
          <div className="border border-[var(--border-subtle)] rounded-card p-3 sm:p-3.5 bg-[var(--bg-linen)]">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
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

                // 3. Sản phẩm khả dụng cho dòng này
                const rowProducts = pool.filter((p) => {
                  if (row.category_id && p.category_id !== Number(row.category_id)) return false;
                  if (row.supplier_id && Number(p.supplier_id) !== Number(row.supplier_id)) return false;
                  return true;
                });

                const currentProd = products.find((p) => p.id === Number(row.product_id));
                const availableStock = currentProd ? currentProd.current_stock : 0;
                const isOverStock = (Number(row.quantity) || 0) > availableStock;

                return (
                  <div
                    key={idx}
                    style={{ zIndex: items.length - idx }}
                    className={`p-2.5 sm:p-3 rounded-card border transition-colors relative space-y-2.5 shadow-xs ${
                      isOverStock
                        ? 'bg-[var(--semantic-alert-bg)] border-[var(--semantic-alert-border)]'
                        : 'bg-[var(--bg-surface)] border-[var(--border-medium)]'
                    }`}
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

                      {/* Ô 2: Nhà cung cấp (dùng hỗ trợ lọc tìm kiếm) */}
                      <div className="sm:col-span-4 min-w-0">
                        <div className="relative flex items-center">
                          <select
                            value={row.supplier_id || ''}
                            onChange={(e) => handleItemChange(idx, 'supplier_id', e.target.value)}
                            className="w-full text-xs bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input pl-2.5 pr-7 py-2 text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer truncate"
                            title="Lọc theo nhà cung cấp (nguồn hàng)"
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

                    {/* Hàng 2: [SL (Tồn)] [Đơn giá] [Thành tiền] [Xóa dòng] */}
                    <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[var(--border-subtle)]">
                      <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[200px]">
                        <div className="flex items-center gap-1.5">
                          <label className="text-[11px] font-medium text-[var(--text-muted)] shrink-0">SL xuất:</label>
                          <input
                            type="number"
                            min="1"
                            value={row.quantity}
                            onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                            placeholder="SL"
                            className={`w-20 text-xs rounded-input p-1.5 text-center font-mono font-bold focus:outline-none border ${
                              isOverStock
                                ? 'bg-[var(--semantic-alert-bg)] border-[var(--semantic-alert)] text-[var(--semantic-alert)]'
                                : 'bg-[var(--bg-surface-warm)] border-[var(--border-medium)] text-[var(--text-primary)] focus:border-[var(--wood-500)]'
                            }`}
                            required
                          />
                          <span className={`text-[11px] font-mono shrink-0 ${isOverStock ? 'text-[var(--semantic-alert)] font-bold' : 'text-[var(--text-muted)]'}`}>
                            (Tồn: {availableStock})
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <label className="text-[11px] font-medium text-[var(--text-muted)] shrink-0">Giá bán:</label>
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
                  </div>
                );
              })}
            </div>

            {/* Total Footer */}
            <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-[var(--text-secondary)]">Tổng giá trị đơn xuất dự tính:</span>
              <span className="font-mono font-bold text-base text-[var(--text-primary)]">{totalCalculated.toLocaleString()} đ</span>
            </div>
          </div>

          <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-card text-xs text-[var(--text-secondary)] flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
            <span className="font-bold text-[var(--text-primary)] shrink-0">Quy trình xuất kho:</span>
            <span>Phiếu mới lập sẽ ở trạng thái <strong>Chờ xuất kho</strong> (chưa trừ tồn kho). Tồn kho và Thẻ kho chỉ được ghi nhận khi bạn bấm <strong>Giao hàng</strong>.</span>
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-[var(--bg-linen)] rounded-card border border-[var(--border-subtle)]">
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
                <span className="font-semibold text-[var(--text-primary)]">{selectedNote.creator_name || selectedNote.creator?.full_name || 'Hệ thống'}</span>
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
