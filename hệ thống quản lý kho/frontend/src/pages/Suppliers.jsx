import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  Phone,
  Mail,
  MapPin,
  AlertCircle,
  Building2,
  RotateCcw,
  Clock,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import { draftStorage } from '../utils/draftStorage';
import { useDelayedLoading } from '../hooks/useDelayedLoading';
import { Loader } from '../components/Loader';

export const Suppliers = () => {
  const { user } = useAuth();
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(false);
  const showLoader = useDelayedLoading(loading);
  const [search, setSearch] = useState('');

  // Synchronous submit lock Ref
  const isSubmittingRef = useRef(false);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDraftRestored, setIsDraftRestored] = useState(false);
  const [draftSavedTime, setDraftSavedTime] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    phone: '',
    email: '',
    address: '',
  });
  const [formError, setFormError] = useState(null);

  const canEdit = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';
  const canDelete = user?.role === 'ADMIN';

  const fetchSuppliers = async () => {
    setLoading(true);
    try {
      const res = await apiClient.suppliers.getAll();
      setSuppliers(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error('Lỗi tải nhà cung cấp:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
    // Tự động khôi phục từ khóa tìm kiếm dở trong vòng 24h nếu có
    const searchDraft = draftStorage.load(user?.username, 'supplier_search');
    if (searchDraft && searchDraft.data) {
      setSearch(searchDraft.data);
    }
  }, [user?.username]);

  // Tự động lưu từ khóa tìm kiếm
  useEffect(() => {
    if (!user?.username) return;
    const timer = setTimeout(() => {
      if (search) {
        draftStorage.save(user.username, 'supplier_search', search);
      } else {
        draftStorage.clear(user.username, 'supplier_search');
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search, user?.username]);

  // Tự động lưu bản nháp tạo nhà cung cấp (debounce 500ms)
  useEffect(() => {
    if (!isModalOpen || modalMode !== 'create' || !user?.username) return;
    const timer = setTimeout(() => {
      if (formData.name || formData.phone || formData.email || formData.address) {
        draftStorage.save(user.username, 'supplier_form', formData);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [formData, isModalOpen, modalMode, user?.username]);

  const handleOpenCreate = () => {
    isSubmittingRef.current = false;
    setModalMode('create');
    setFormError(null);
    const draft = draftStorage.load(user?.username, 'supplier_form');
    if (draft && draft.data && draft.data.name) {
      setFormData(draft.data);
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setFormData({
        code: `NCC_${String(suppliers.length + 1).padStart(3, '0')}`,
        name: '',
        phone: '',
        email: '',
        address: '',
      });
      setIsDraftRestored(false);
      setDraftSavedTime('');
    }
    setIsModalOpen(true);
  };

  const handleClearDraft = () => {
    draftStorage.clear(user?.username, 'supplier_form');
    setFormData({
      code: `NCC_${String(suppliers.length + 1).padStart(3, '0')}`,
      name: '',
      phone: '',
      email: '',
      address: '',
    });
    setIsDraftRestored(false);
    setDraftSavedTime('');
  };

  const handleOpenEdit = (s) => {
    isSubmittingRef.current = false;
    setModalMode('edit');
    setIsDraftRestored(false);
    setDraftSavedTime('');
    setSelectedSupplier(s);
    setFormData({
      code: s.code,
      name: s.name,
      phone: s.phone || '',
      email: s.email || '',
      address: s.address || '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveSupplier = async (e) => {
    e.preventDefault();
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setFormError(null);
    setIsSubmitting(true);
    try {
      if (modalMode === 'create') {
        await apiClient.suppliers.create(formData);
        draftStorage.clear(user?.username, 'supplier_form');
        setIsDraftRestored(false);
      } else {
        await apiClient.suppliers.update(selectedSupplier.id, {
          name: formData.name,
          phone: formData.phone,
          email: formData.email,
          address: formData.address,
        });
      }
      setIsModalOpen(false);
      fetchSuppliers();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Không thể lưu nhà cung cấp');
    } finally {
      setIsSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  const handleDeleteSupplier = async (s) => {
    if (!window.confirm(`Bạn có chắc muốn ngưng hợp tác với "${s.name}"?`)) return;
    try {
      await apiClient.suppliers.delete(s.id);
      fetchSuppliers();
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể xóa nhà cung cấp này');
    }
  };

  const filteredSuppliers = suppliers.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[var(--text-primary)] tracking-tight">Nhà cung cấp</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Quản lý mạng lưới các đối tác cung ứng thiết bị và nguyên vật liệu</p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm nhà cung cấp</span>
          </button>
        )}
      </div>

      {/* Search */}
      <div className="card-wood p-4">
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm theo tên nhà cung cấp..."
            className="w-full pl-9 pr-3.5 py-2 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] placeholder:text-[var(--text-muted)]"
          />
        </div>
      </div>

      {/* Supplier Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {showLoader ? (
          [...Array(6)].map((_, i) => (
            <div key={i} className="card-wood p-5 flex flex-col justify-between space-y-4 sk-skeleton-pulse">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-input bg-[var(--border-medium)]/60 shrink-0" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-4 bg-[var(--border-medium)]/70 rounded-sm w-3/4" />
                  <div className="h-3 bg-[var(--border-medium)]/50 rounded-sm w-1/3" />
                </div>
              </div>
              <div className="space-y-2 pt-2 border-t border-[var(--border-subtle)]">
                <div className="h-3 bg-[var(--border-medium)]/50 rounded-sm w-5/6" />
                <div className="h-3 bg-[var(--border-medium)]/50 rounded-sm w-2/3" />
              </div>
            </div>
          ))
        ) : filteredSuppliers.length === 0 ? (
          <div className="col-span-full py-12 text-center text-xs text-[var(--text-muted)]">
            Không tìm thấy nhà cung cấp nào.
          </div>
        ) : (
          filteredSuppliers.map((s) => (
            <div
              key={s.id}
              className="card-wood p-5 flex flex-col justify-between hover:shadow-md hover:border-[var(--border-strong)] transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-input bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] flex items-center justify-center text-[var(--wood-500)] shadow-xs">
                      <Building2 className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-serif font-bold text-[var(--text-primary)] text-sm leading-tight">{s.name}</h4>
                      <span className="font-mono text-xs text-[var(--text-secondary)]">{s.code}</span>
                    </div>
                  </div>
                  <Badge variant={s.is_active ? 'success' : 'inactive'}>
                    {s.is_active ? 'Đang hợp tác' : 'Ngưng hợp tác'}
                  </Badge>
                </div>

                <div className="space-y-2 text-xs text-[var(--text-secondary)] mt-4 border-t border-[var(--border-subtle)] pt-3">
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                    <span>{s.phone || 'Chưa cập nhật'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                    <span className="truncate">{s.email || 'Chưa cập nhật'}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0 mt-0.5" />
                    <span className="line-clamp-2 text-[var(--text-secondary)]">{s.address || 'Chưa cập nhật'}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-1 mt-4 pt-3 border-t border-[var(--border-subtle)]">
                {canEdit && (
                  <button
                    onClick={() => handleOpenEdit(s)}
                    className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] rounded-btn transition-colors cursor-pointer"
                    title="Sửa thông tin"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                )}
                {canDelete && (
                  <button
                    onClick={() => handleDeleteSupplier(s)}
                    className="p-1.5 text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn transition-colors cursor-pointer"
                    title="Ngưng hợp tác"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal Add/Edit Supplier */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalMode === 'create' ? 'Thêm nhà cung cấp mới' : 'Cập nhật nhà cung cấp'}
      >
        <form onSubmit={handleSaveSupplier} className="space-y-4">
          {modalMode === 'create' && isDraftRestored && (
            <div className="p-3 bg-[var(--semantic-ai-bg)] border border-[var(--semantic-ai-border)] rounded-input text-xs text-[var(--semantic-ai)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[var(--semantic-ai-btn)] shrink-0" />
                <span>Đã khôi phục dữ liệu nhập dở lúc <b>{draftSavedTime}</b> (hạn lưu 24h).</span>
              </div>
              <button
                type="button"
                onClick={handleClearDraft}
                className="text-[var(--semantic-alert)] underline font-semibold cursor-pointer flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                Xóa bản nháp
              </button>
            </div>
          )}

          {formError && (
            <div className="p-3 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] text-[var(--semantic-alert)] rounded-input text-xs flex items-center gap-2 font-medium">
              <AlertCircle className="w-4 h-4 text-[var(--semantic-alert)] shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <input type="hidden" value={formData.code} />

          <div>
            <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Tên nhà cung cấp</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="VD: Công ty TNHH Gỗ Lâm Nghiệp..."
              className="input-wood"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Số điện thoại</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="0912345678"
                className="input-wood font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="contact@supplier.com"
                className="input-wood"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Địa chỉ</label>
            <textarea
              rows="3"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="Địa chỉ trụ sở hoặc kho..."
              className="input-wood"
            ></textarea>
          </div>

          <div className="pt-4 flex items-center justify-end gap-2 border-t border-[var(--border-medium)]">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="btn-outline"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary flex items-center justify-center gap-2 min-w-[120px]"
            >
              {isSubmitting && <Loader variant="inline" />}
              <span>{isSubmitting ? 'Đang lưu...' : (modalMode === 'create' ? 'Tạo mới' : 'Cập nhật')}</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Suppliers;
