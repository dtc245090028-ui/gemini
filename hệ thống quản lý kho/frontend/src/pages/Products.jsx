import React, { useState, useEffect } from 'react';
import {
  Package,
  Plus,
  Search,
  Filter,
  AlertTriangle,
  Edit2,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  Image as ImageIcon,
  Upload,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export const Products = ({ onSelectProductLedger }) => {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filters State
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [filterLowStock, setFilterLowStock] = useState(false);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit'
  const [currentProduct, setCurrentProduct] = useState(null);
  const [zoomImage, setZoomImage] = useState(null); // Preview ảnh phóng to
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    category_id: '',
    unit: 'Chiếc',
    min_stock: 10,
    standard_price: 100000,
    image_url: '',
  });
  const [formError, setFormError] = useState(null);

  const canEdit = user?.role === 'ADMIN' || user?.role === 'WAREHOUSE_KEEPER';
  const canDelete = user?.role === 'ADMIN';

  const fetchCategories = async () => {
    try {
      const res = await apiClient.categories.getAll();
      setCategories(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error('Lỗi tải nhóm hàng:', err);
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (selectedCategory) params.category_id = selectedCategory;
      if (filterLowStock) params.is_low_stock = true;
      params.limit = 100;

      const res = await apiClient.products.getAll(params);
      setProducts(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error('Lỗi tải hàng hóa:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [search, selectedCategory, filterLowStock]);

  const handleOpenCreate = () => {
    setModalMode('create');
    setCurrentProduct(null);
    setImageFile(null);
    setImagePreview(null);
    setFormData({
      code: `SP${String(products.length + 1).padStart(3, '0')}`,
      name: '',
      category_id: categories[0]?.id || '',
      unit: 'Chiếc',
      min_stock: 10,
      standard_price: 100000,
      image_url: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (p) => {
    setModalMode('edit');
    setCurrentProduct(p);
    setImageFile(null);
    setImagePreview(p.image_url || null);
    setFormData({
      code: p.code,
      name: p.name,
      category_id: p.category_id,
      unit: p.unit,
      min_stock: p.min_stock,
      standard_price: p.standard_price,
      image_url: p.image_url || '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleImageFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSubmitForm = async (e) => {
    e.preventDefault();
    setFormError(null);
    try {
      let productId;
      if (modalMode === 'create') {
        const res = await apiClient.products.create({
          ...formData,
          category_id: Number(formData.category_id),
          min_stock: Number(formData.min_stock),
          standard_price: Number(formData.standard_price),
          image_url: formData.image_url || undefined,
        });
        productId = res.data?.id;
      } else {
        const res = await apiClient.products.update(currentProduct.id, {
          name: formData.name,
          category_id: Number(formData.category_id),
          unit: formData.unit,
          min_stock: Number(formData.min_stock),
          standard_price: Number(formData.standard_price),
          image_url: formData.image_url || undefined,
        });
        productId = currentProduct.id;
      }

      // Nếu có chọn file ảnh từ máy tính -> upload ngay
      if (imageFile && productId) {
        const fd = new FormData();
        fd.append('file', imageFile);
        await apiClient.products.uploadImage(productId, fd);
      }

      setIsModalOpen(false);
      fetchProducts();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Đã có lỗi xảy ra khi lưu mặt hàng.';
      setFormError(msg);
    }
  };

  const handleDeleteProduct = async (p) => {
    if (!window.confirm(`Bạn có chắc chắn muốn ngưng kinh doanh mặt hàng "${p.name}"?`)) return;
    try {
      await apiClient.products.delete(p.id);
      fetchProducts();
    } catch (err) {
      alert(err.response?.data?.detail || 'Không thể xóa mặt hàng này.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-wood-900 tracking-tight">Danh Mục Hàng Hóa</h2>
          <p className="text-xs text-wood-600 mt-0.5">Quản lý mã SKU, đơn vị tính, định mức tồn kho an toàn và giá chuẩn</p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm Mặt Hàng Mới</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="card-wood p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-wood-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm theo mã SKU hoặc tên hàng..."
              className="w-full pl-9 pr-3.5 py-2 bg-wood-50/70 border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20 focus:border-wood-500"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="py-2 px-3 bg-wood-50/70 border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20"
          >
            <option value="">Tất cả nhóm hàng</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* Low Stock Toggle */}
        <label className="flex items-center gap-2 text-xs font-medium text-wood-800 cursor-pointer select-none bg-wood-50/70 px-3 py-2 rounded-xl border border-wood-200">
          <input
            type="checkbox"
            checked={filterLowStock}
            onChange={(e) => setFilterLowStock(e.target.checked)}
            className="rounded text-wood-600 focus:ring-wood-500 w-4 h-4 cursor-pointer accent-wood-500"
          />
          <AlertTriangle className="w-3.5 h-3.5 text-rust-500" />
          <span>Chỉ hiện hàng dưới tồn tối thiểu</span>
        </label>
      </div>

      {/* Products Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
              <tr>
                <th className="py-3.5 px-4 text-center w-24">Ảnh</th>
                <th className="py-3.5 px-4">Mã SKU</th>
                <th className="py-3.5 px-4">Tên hàng hóa</th>
                <th className="py-3.5 px-4">Nhóm hàng</th>
                <th className="py-3.5 px-4 text-center">ĐVT</th>
                <th className="py-3.5 px-4 text-center">Tồn hiện tại</th>
                <th className="py-3.5 px-4 text-center">Tồn an toàn</th>
                <th className="py-3.5 px-4 text-right">Giá chuẩn</th>
                <th className="py-3.5 px-4 text-center">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-wood-100">
              {loading ? (
                <tr>
                  <td colSpan="10" className="text-center py-10 text-wood-400">
                    Đang tải danh sách hàng hóa...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="10" className="text-center py-10 text-wood-400">
                    Không tìm thấy sản phẩm nào khớp với bộ lọc.
                  </td>
                </tr>
              ) : (
                products.map((p) => {
                  const isLow = p.current_stock <= p.min_stock;
                  return (
                    <tr key={p.id} className="hover:bg-wood-50/80 transition-colors">
                      <td className="py-3 px-4 text-center align-middle">
                        <div
                          onClick={() => p.image_url && setZoomImage({ url: p.image_url, name: p.name, code: p.code })}
                          className={`w-20 h-20 min-w-[80px] min-h-[80px] rounded-xl bg-wood-100 border border-wood-200 overflow-hidden inline-flex items-center justify-center transition-all ${
                            p.image_url ? 'cursor-pointer hover:border-wood-500 hover:ring-2 hover:ring-wood-500/20 shadow-2xs group' : ''
                          }`}
                          title={p.image_url ? 'Bấm để xem ảnh phóng to' : 'Chưa có ảnh'}
                        >
                          {p.image_url ? (
                            <img
                              src={p.image_url}
                              alt={p.name}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                              onError={(e) => {
                                e.currentTarget.style.display = 'none';
                                if (e.currentTarget.nextSibling) {
                                  e.currentTarget.nextSibling.style.display = 'flex';
                                }
                              }}
                            />
                          ) : null}
                          <div
                            className="w-full h-full flex flex-col items-center justify-center text-wood-400 bg-wood-50 text-[10px]"
                            style={{ display: p.image_url ? 'none' : 'flex' }}
                          >
                            <Package className="w-7 h-7 text-wood-400 mb-1" />
                            <span>Trống</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold text-wood-700 align-middle">{p.code}</td>
                      <td className="py-3.5 px-4 font-medium text-wood-900 align-middle">{p.name}</td>
                      <td className="py-3.5 px-4 text-wood-600 align-middle">{p.category?.name || 'N/A'}</td>
                      <td className="py-3.5 px-4 text-center text-wood-600 align-middle">{p.unit}</td>
                      <td className="py-3.5 px-4 text-center align-middle">
                        <span
                          className={`font-bold px-2 py-0.5 rounded ${
                            isLow
                              ? 'bg-rust-50 text-rust-600 border border-rust-200'
                              : 'bg-forest-50 text-forest-700 border border-forest-200'
                          }`}
                        >
                          {p.current_stock}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center text-wood-600 font-medium align-middle">{p.min_stock}</td>
                      <td className="py-3.5 px-4 text-right font-medium text-wood-800 align-middle">
                        {p.standard_price.toLocaleString()} đ
                      </td>
                      <td className="py-3.5 px-4 text-center align-middle">
                        <Badge variant={p.status === 'ACTIVE' ? 'green' : 'gray'}>
                          {p.status === 'ACTIVE' ? 'Kinh doanh' : 'Ngưng bán'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right align-middle">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onSelectProductLedger(p.id)}
                            title="Xem lịch sử thẻ kho"
                            className="p-1.5 text-wood-400 hover:text-wood-800 hover:bg-wood-100 rounded-btn transition-colors cursor-pointer"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => handleOpenEdit(p)}
                              title="Sửa hàng hóa"
                              className="p-1.5 text-wood-400 hover:text-wood-800 hover:bg-wood-100 rounded-btn transition-colors cursor-pointer"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          )}
                          {canDelete && (
                            <button
                              onClick={() => handleDeleteProduct(p)}
                              title="Ngưng kinh doanh"
                              className="p-1.5 text-wood-400 hover:text-rust-600 hover:bg-rust-50 rounded-btn transition-colors cursor-pointer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Thêm / Sửa Mặt Hàng */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalMode === 'create' ? 'Thêm Mặt Hàng Mới' : 'Cập Nhật Hàng Hóa'}
      >
        <form onSubmit={handleSubmitForm} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rust-50 border border-rust-200 text-rust-700 rounded-xl text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rust-500 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Mã SKU</label>
              <input
                type="text"
                disabled={modalMode === 'edit'}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="VD: SP001..."
                className="input-wood disabled:bg-wood-100/60 disabled:text-wood-400"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Nhóm hàng</label>
              <select
                value={formData.category_id}
                onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                className="input-wood"
                required
              >
                <option value="">Chọn nhóm hàng</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-wood-800 mb-1">Tên mặt hàng</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="VD: Bàn làm việc gỗ sồi tự nhiên..."
              className="input-wood"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Đơn vị tính</label>
              <input
                type="text"
                value={formData.unit}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                placeholder="Chiếc, Bộ..."
                className="input-wood"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Tồn an toàn</label>
              <input
                type="number"
                min="0"
                value={formData.min_stock}
                onChange={(e) => setFormData({ ...formData, min_stock: e.target.value })}
                className="input-wood"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-wood-800 mb-1">Giá chuẩn (đ)</label>
              <input
                type="number"
                min="0"
                step="1000"
                value={formData.standard_price}
                onChange={(e) => setFormData({ ...formData, standard_price: e.target.value })}
                className="input-wood"
                required
              />
            </div>
          </div>

          {/* Hình ảnh mặt hàng */}
          <div className="p-3.5 bg-wood-50/70 rounded-xl border border-wood-200 space-y-2.5">
            <label className="block text-xs font-semibold text-wood-800">
              Hình ảnh mặt hàng
            </label>
            <div className="flex items-center gap-3.5">
              {/* Box xem trước ảnh */}
              <div className="w-16 h-16 rounded-xl border border-wood-300 bg-white overflow-hidden flex items-center justify-center shrink-0 shadow-2xs">
                {imagePreview || formData.image_url ? (
                  <img
                    src={imagePreview || formData.image_url}
                    alt="Preview"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      if (e.currentTarget.nextSibling) e.currentTarget.nextSibling.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="w-full h-full flex flex-col items-center justify-center text-wood-400 text-[9px] p-1 text-center"
                  style={{ display: (imagePreview || formData.image_url) ? 'none' : 'flex' }}
                >
                  <ImageIcon className="w-5 h-5 text-wood-400 mb-0.5" />
                  <span>Chưa có ảnh</span>
                </div>
              </div>

              {/* Nút Upload & Input URL */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-wood-300 hover:bg-wood-100 rounded-btn text-xs font-medium text-wood-800 cursor-pointer transition-colors shadow-2xs">
                    <Upload className="w-3.5 h-3.5 text-wood-600" />
                    <span>Tải ảnh từ máy...</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageFileChange}
                    />
                  </label>
                  {imageFile && (
                    <span className="text-[11px] text-forest-700 font-medium truncate max-w-[180px]">
                      {imageFile.name}
                    </span>
                  )}
                </div>

                <input
                  type="text"
                  value={formData.image_url || ''}
                  onChange={(e) => {
                    setFormData({ ...formData, image_url: e.target.value });
                    setImagePreview(null);
                  }}
                  placeholder="Hoặc dán URL: https://... hoặc /static/products/SP001.jpg"
                  className="w-full px-3 py-1.5 bg-white border border-wood-200 rounded-xl text-xs text-wood-900 focus:outline-none focus:ring-2 focus:ring-wood-500/20"
                />
              </div>
            </div>
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

      {/* Modal Xem Ảnh Phóng To */}
      {zoomImage && (
        <Modal
          isOpen={!!zoomImage}
          onClose={() => setZoomImage(null)}
          title={`Hình ảnh: [${zoomImage.code}] ${zoomImage.name}`}
        >
          <div className="flex flex-col items-center justify-center p-3 space-y-3">
            <div className="w-full max-h-[60vh] overflow-hidden rounded-xl bg-wood-100 flex items-center justify-center border border-wood-200 shadow-sm">
              <img
                src={zoomImage.url}
                alt={zoomImage.name}
                className="max-h-[58vh] max-w-full object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  if (e.currentTarget.nextSibling) e.currentTarget.nextSibling.style.display = 'flex';
                }}
              />
              <div className="hidden flex-col items-center justify-center p-10 text-wood-400">
                <Package className="w-12 h-12 mb-2 text-wood-300" />
                <span className="text-xs">Không thể tải file ảnh này</span>
              </div>
            </div>
            <p className="text-xs text-wood-500 font-mono text-center">
              Đường dẫn: {zoomImage.url}
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default Products;
