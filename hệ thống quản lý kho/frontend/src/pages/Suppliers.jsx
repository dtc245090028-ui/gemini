import React, { useState, useEffect } from 'react';
import {
  Truck,
  Plus,
  Search,
  Edit2,
  Trash2,
  Phone,
  Mail,
  MapPin,
  AlertCircle,
  Building2,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export const Suppliers = () => {
  const { user } = useAuth();
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create');
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
  }, []);

  const handleOpenCreate = () => {
    setModalMode('create');
    setFormData({
      code: `NCC_${String(suppliers.length + 1).padStart(3, '0')}`,
      name: '',
      phone: '',
      email: '',
      address: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (s) => {
    setModalMode('edit');
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
    setFormError(null);
    try {
      if (modalMode === 'create') {
        await apiClient.suppliers.create(formData);
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
          <h2 className="font-serif text-2xl font-bold text-wood-900 tracking-tight">Đối Tác Nhà Cung Cấp</h2>
          <p className="text-xs text-wood-600 mt-0.5">Quản lý mạng lưới các đối tác cung ứng thiết bị và nguyên vật liệu</p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm Nhà Cung Cấp</span>
          </button>
        )}
      </div>

      {/* Search */}
      <div className="card-wood p-4">
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-wood-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo mã hoặc tên nhà cung cấp..."
            className="w-full pl-9 pr-3.5 py-2 bg-wood-50/70 border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20 focus:border-wood-500"
          />
        </div>
      </div>

      {/* Supplier Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-12 text-center text-xs text-wood-400">
            Đang tải dữ liệu nhà cung cấp...
          </div>
        ) : filteredSuppliers.length === 0 ? (
          <div className="col-span-full py-12 text-center text-xs text-wood-400">
            Không tìm thấy nhà cung cấp nào.
          </div>
        ) : (
          filteredSuppliers.map((s) => (
            <div
              key={s.id}
              className="card-wood p-5 flex flex-col justify-between hover:shadow-md hover:border-wood-300 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-wood-100 border border-wood-200 flex items-center justify-center text-wood-700">
                      <Building2 className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-serif font-bold text-wood-900 text-sm leading-tight">{s.name}</h4>
                      <span className="font-mono text-[11px] text-wood-500 font-semibold">{s.code}</span>
                    </div>
                  </div>
                  <Badge variant={s.is_active ? 'green' : 'gray'}>
                    {s.is_active ? 'Đang hợp tác' : 'Ngưng hợp tác'}
                  </Badge>
                </div>

                <div className="space-y-1.5 text-xs text-wood-700 mt-4 border-t border-wood-100 pt-3">
                  <div className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-wood-400 shrink-0" />
                    <span>{s.phone || 'Chưa cập nhật'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-wood-400 shrink-0" />
                    <span className="truncate">{s.email || 'Chưa cập nhật'}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <MapPin className="w-3.5 h-3.5 text-wood-400 shrink-0 mt-0.5" />
                    <span className="line-clamp-2 text-wood-600">{s.address || 'Chưa cập nhật'}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-1 mt-4 pt-3 border-t border-wood-100">
                {canEdit && (
                  <button
                    onClick={() => handleOpenEdit(s)}
                    className="p-1.5 text-wood-400 hover:text-wood-800 hover:bg-wood-100 rounded-btn transition-colors cursor-pointer"
                    title="Sửa thông tin"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                )}
                {canDelete && (
                  <button
                    onClick={() => handleDeleteSupplier(s)}
                    className="p-1.5 text-wood-400 hover:text-rust-600 hover:bg-rust-50 rounded-btn transition-colors cursor-pointer"
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
        title={modalMode === 'create' ? 'Thêm Nhà Cung Cấp Mới' : 'Cập Nhật Nhà Cung Cấp'}
      >
        <form onSubmit={handleSaveSupplier} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rust-50 border border-rust-200 text-rust-700 rounded-xl text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rust-500 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-wood-800 mb-1">Mã nhà cung cấp</label>
            <input
              type="text"
              disabled={modalMode === 'edit'}
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="input-wood disabled:bg-wood-100/60 disabled:text-wood-400"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-wood-800 mb-1">Tên nhà cung cấp</label>
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
              <label className="block text-xs font-semibold text-wood-800 mb-1">Số điện thoại</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="0912345678"
                className="input-wood"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Email</label>
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
            <label className="block text-xs font-semibold text-wood-800 mb-1">Địa chỉ</label>
            <textarea
              rows="3"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="Địa chỉ trụ sở hoặc kho..."
              className="input-wood"
            ></textarea>
          </div>

          <div className="pt-4 flex items-center justify-end gap-2 border-t border-wood-200">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="btn-outline"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              className="btn-primary"
            >
              {modalMode === 'create' ? 'Tạo mới' : 'Cập nhật'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Suppliers;
