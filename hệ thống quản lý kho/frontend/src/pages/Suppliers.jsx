import React, { useState, useEffect } from 'react';
import { Truck, Plus, Search, Edit2, Trash2, Phone, Mail, MapPin, AlertCircle } from 'lucide-react';
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
          <h2 className="text-xl font-bold text-slate-900">Đối Tác Nhà Cung Cấp</h2>
          <p className="text-xs text-slate-500 mt-0.5">Quản lý mạng lưới các đối tác cung ứng thiết bị và linh kiện</p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm Nhà Cung Cấp</span>
          </button>
        )}
      </div>

      {/* Search */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên hoặc mã nhà cung cấp..."
            className="w-full pl-9 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Suppliers Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Mã đối tác</th>
                <th className="py-3 px-4">Tên nhà cung cấp</th>
                <th className="py-3 px-4">Điện thoại</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Địa chỉ trụ sở</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Đang tải danh sách nhà cung cấp...
                  </td>
                </tr>
              ) : filteredSuppliers.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-10 text-slate-400">
                    Không có nhà cung cấp nào.
                  </td>
                </tr>
              ) : (
                filteredSuppliers.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-blue-600">{s.code}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-800">{s.name}</td>
                    <td className="py-3.5 px-4 text-slate-600 flex items-center gap-1.5 mt-2">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      <span>{s.phone || 'Chưa cập nhật'}</span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <Mail className="w-3.5 h-3.5 text-slate-400" />
                        <span>{s.email || 'Chưa cập nhật'}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate max-w-[200px]">{s.address || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={s.is_active ? 'green' : 'gray'}>
                        {s.is_active ? 'Đang hợp tác' : 'Ngưng hợp tác'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {canEdit && (
                          <button
                            onClick={() => handleOpenEdit(s)}
                            title="Sửa thông tin"
                            className="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors cursor-pointer"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        )}
                        {canDelete && (
                          <button
                            onClick={() => handleDeleteSupplier(s)}
                            title="Ngưng hợp tác"
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
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

      {/* Modal Thêm/Sửa */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalMode === 'create' ? 'Thêm Nhà Cung Cấp Mới' : 'Cập Nhật Nhà Cung Cấp'}
      >
        {formError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleSaveSupplier} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Mã NCC</label>
              <input
                type="text"
                disabled={modalMode === 'edit'}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono uppercase disabled:opacity-60"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Tên nhà cung cấp</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="VD: Công ty TNHH Viễn Đông..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Số điện thoại</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="0243..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Địa chỉ Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="contact@company.com"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Địa chỉ trụ sở</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="Số nhà, đường, thành phố..."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
            />
          </div>

          <div className="pt-4 flex items-center justify-end gap-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors cursor-pointer"
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
