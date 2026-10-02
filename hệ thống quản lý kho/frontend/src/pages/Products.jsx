import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Package,
  Plus,
  Search,
  AlertTriangle,
  Edit2,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  Image as ImageIcon,
  Upload,
  ArrowDownToLine,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { draftStorage } from '../utils/draftStorage';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import { useDelayedLoading } from '../hooks/useDelayedLoading';
import { Loader } from '../components/Loader';

export const Products = ({ onSelectProductLedger }) => {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(false);
  const showTableLoader = useDelayedLoading(loading);

  // Synchronous submit lock Ref
  const isSubmittingRef = useRef(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState(null);

  // Filters State
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [filterLowStock, setFilterLowStock] = useState(false);

  // Debounce tìm kiếm 300ms chống spam API khi gõ phím
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Pagination & Sorting State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit'
  const [isDraftRestored, setIsDraftRestored] = useState(false);
  const [draftSavedTime, setDraftSavedTime] = useState('');
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
    has_initial_import: false,
    initial_supplier_id: '',
    initial_quantity: 10,
    initial_unit_price: 70000,
    initial_note: '',
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

  const fetchSuppliers = async () => {
    try {
      const res = await apiClient.suppliers.getAll();
      setSuppliers(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error('Lỗi tải nhà cung cấp:', err);
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (selectedCategory) params.category_id = selectedCategory;
      if (filterLowStock) params.is_low_stock = true;
      params.limit = 500;

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
    fetchSuppliers();
    // Tự động khôi phục từ khóa tìm kiếm dở trong vòng 24h nếu có
    const searchDraft = draftStorage.load(user?.username, 'product_search');
    if (searchDraft && searchDraft.data) {
      setSearch(searchDraft.data);
    }
  }, []);

  // Tự động lưu từ khóa tìm kiếm vào draft (xóa khi để trống)
  useEffect(() => {
    if (user?.username) {
      if (search) {
        draftStorage.save(user.username, 'product_search', search);
      } else {
        draftStorage.clear(user.username, 'product_search');
      }
    }
  }, [search, user?.username]);

  useEffect(() => {
    fetchProducts();
  }, [debouncedSearch, selectedCategory, filterLowStock]);

  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearch, selectedCategory, filterLowStock]);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        setNotification(null);
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  // Sắp xếp dữ liệu
  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        if (prev.direction === 'asc') {
          return { key, direction: 'desc' };
        }
        return { key: null, direction: 'asc' };
      }
      return { key, direction: 'asc' };
    });
  };

  const sortedProducts = useMemo(() => {
    if (!sortConfig.key) return products;
    return [...products].sort((a, b) => {
      if (sortConfig.key === 'name') {
        const comp = (a.name || '').localeCompare(b.name || '', 'vi', { sensitivity: 'base' });
        return sortConfig.direction === 'asc' ? comp : -comp;
      }
      if (sortConfig.key === 'standard_price') {
        const diff = (a.standard_price || 0) - (b.standard_price || 0);
        return sortConfig.direction === 'asc' ? diff : -diff;
      }
      if (sortConfig.key === 'current_stock') {
        const diff = (a.current_stock || 0) - (b.current_stock || 0);
        return sortConfig.direction === 'asc' ? diff : -diff;
      }
      return 0;
    });
  }, [products, sortConfig]);

  // Phân trang dữ liệu
  const totalItems = sortedProducts.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedProducts = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * pageSize;
    return sortedProducts.slice(startIndex, startIndex + pageSize);
  }, [sortedProducts, safeCurrentPage, pageSize]);

  const startItem = totalItems === 0 ? 0 : (safeCurrentPage - 1) * pageSize + 1;
  const endItem = Math.min(totalItems, safeCurrentPage * pageSize);

  const getPageNumbers = () => {
    const pages = [];
    const maxPagesToShow = 5;
    if (totalPages <= maxPagesToShow) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      let start = Math.max(1, safeCurrentPage - 2);
      let end = Math.min(totalPages, start + maxPagesToShow - 1);
      if (end - start < maxPagesToShow - 1) {
        start = Math.max(1, end - maxPagesToShow + 1);
      }
      for (let i = start; i <= end; i++) pages.push(i);
    }
    return pages;
  };

  const renderSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return (
        <ArrowUpDown className="w-3.5 h-3.5 text-wood-400 group-hover:text-wood-600 transition-colors shrink-0" />
      );
    }
    return sortConfig.direction === 'asc' ? (
      <ArrowUp className="w-3.5 h-3.5 text-forest-700 font-bold shrink-0" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-rust-700 font-bold shrink-0" />
    );
  };

  const handleOpenCreate = () => {
    isSubmittingRef.current = false;
    setModalMode('create');
    setCurrentProduct(null);
    setImageFile(null);
    setImagePreview(null);
    const defaultPrice = 100000;

    // Kiểm tra bản nháp tạo sản phẩm trong vòng 24h
    const draft = draftStorage.load(user?.username, 'product_create');
    if (draft && draft.data) {
      setFormData(draft.data);
      setIsDraftRestored(true);
      setDraftSavedTime(draftStorage.formatSavedTime(draft.saved_at));
    } else {
      setFormData({
        code: `SP${String(products.length + 1).padStart(3, '0')}`,
        name: '',
        category_id: categories[0]?.id || '',
        unit: 'Chiếc',
        min_stock: 10,
        standard_price: defaultPrice,
        image_url: '',
        has_initial_import: false,
        initial_supplier_id: suppliers[0]?.id || '',
        initial_quantity: 10,
        initial_unit_price: Math.round(defaultPrice * 0.7),
        initial_note: '',
      });
      setIsDraftRestored(false);
      setDraftSavedTime('');
    }
    setFormError(null);
    setIsModalOpen(true);
  };

  // Tự động lưu bản nháp tạo mặt hàng khi người dùng nhập liệu dở
  useEffect(() => {
    if (isModalOpen && modalMode === 'create' && user?.username) {
      const timer = setTimeout(() => {
        draftStorage.save(user.username, 'product_create', formData);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isModalOpen, modalMode, formData, user?.username]);

  // Hủy bản nháp tạo mặt hàng
  const handleDiscardDraft = () => {
    draftStorage.clear(user?.username, 'product_create');
    setIsDraftRestored(false);
    const defaultPrice = 100000;
    setFormData({
      code: `SP${String(products.length + 1).padStart(3, '0')}`,
      name: '',
      category_id: categories[0]?.id || '',
      unit: 'Chiếc',
      min_stock: 10,
      standard_price: defaultPrice,
      image_url: '',
      has_initial_import: false,
      initial_supplier_id: suppliers[0]?.id || '',
      initial_quantity: 10,
      initial_unit_price: Math.round(defaultPrice * 0.7),
      initial_note: '',
    });
  };

  const handleOpenEdit = (p) => {
    isSubmittingRef.current = false;
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
      has_initial_import: false,
      initial_supplier_id: '',
      initial_quantity: 10,
      initial_unit_price: '',
      initial_note: '',
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
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setFormError(null);
    setIsSubmitting(true);
    try {
      let productId;
      let createdProductData = null;
      if (modalMode === 'create') {
        const payload = {
          code: formData.code,
          name: formData.name,
          category_id: Number(formData.category_id),
          unit: formData.unit,
          min_stock: Number(formData.min_stock),
          standard_price: Number(formData.standard_price),
          image_url: formData.image_url || undefined,
        };

        if (formData.has_initial_import) {
          if (!formData.initial_supplier_id) {
            setFormError('Vui lòng chọn nhà cung cấp cho phiếu nhập ban đầu.');
            isSubmittingRef.current = false;
            setIsSubmitting(false);
            return;
          }
          if (Number(formData.initial_quantity) <= 0) {
            setFormError('Số lượng nhập kho ban đầu phải lớn hơn 0.');
            isSubmittingRef.current = false;
            setIsSubmitting(false);
            return;
          }
          payload.initial_supplier_id = Number(formData.initial_supplier_id);
          payload.initial_quantity = Number(formData.initial_quantity);
          payload.initial_unit_price = Number(formData.initial_unit_price) || 0;
          if (formData.initial_note) {
            payload.initial_note = formData.initial_note;
          }
        }

        const res = await apiClient.products.create(payload);
        createdProductData = res.data;
        productId = res.data?.id;
        // Xóa bản nháp sau khi tạo thành công
        draftStorage.clear(user?.username, 'product_create');
        setIsDraftRestored(false);
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

      if (modalMode === 'create' && createdProductData) {
        if (createdProductData.initial_import_note_code) {
          setNotification({
            type: 'success',
            message: `Tạo mặt hàng [${createdProductData.code}] "${createdProductData.name}" thành công và tự động lập Phiếu nhập kho ${createdProductData.initial_import_note_code} (+${formData.initial_quantity} ${formData.unit})!`,
          });
        } else {
          setNotification({
            type: 'success',
            message: `Tạo mới mặt hàng [${createdProductData.code}] "${createdProductData.name}" thành công!`,
          });
        }
      } else {
        setNotification({
          type: 'success',
          message: 'Cập nhật thông tin mặt hàng thành công!',
        });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Đã có lỗi xảy ra khi lưu mặt hàng.';
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
      isSubmittingRef.current = false;
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
      {/* Thông báo thao tác */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between transition-all duration-300 shadow-2xs ${
            notification.type === 'success'
              ? 'bg-forest-50 border-forest-200 text-forest-800'
              : 'bg-rust-50 border-rust-200 text-rust-800'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <CheckCircle className="w-5 h-5 text-forest-600 shrink-0" />
            <span className="text-xs sm:text-sm font-medium">{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="p-1 hover:bg-forest-100 rounded-lg text-forest-600 transition-colors cursor-pointer"
          >
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[var(--text-primary)] tracking-tight">Hàng hóa & kho</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">Quản lý danh mục hàng hóa, đơn vị tính, định mức tồn kho an toàn và giá niêm yết</p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm hàng hóa mới</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="card-wood p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm theo tên hàng hóa..."
              className="w-full pl-9 pr-3.5 py-2 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="py-2 px-3 bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer"
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
        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)] cursor-pointer select-none bg-[var(--bg-surface-warm)] px-3 py-2 rounded-input border border-[var(--border-medium)]">
          <input
            type="checkbox"
            checked={filterLowStock}
            onChange={(e) => setFilterLowStock(e.target.checked)}
            className="rounded text-[var(--wood-500)] focus:ring-[var(--wood-500)] w-4 h-4 cursor-pointer accent-[var(--wood-500)]"
          />
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--semantic-alert)]" />
          <span>Chỉ hiện hàng dưới tồn tối thiểu</span>
        </label>
      </div>

      {/* Products Table */}
      <div className="card-wood overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--bg-surface-warm)] text-[var(--text-primary)] font-semibold border-b border-[var(--border-medium)]">
              <tr>
                <th className="py-3.5 px-4 text-center w-24">Ảnh</th>
                <th
                  onClick={() => handleSort('name')}
                  className="py-3.5 px-4 cursor-pointer select-none group hover:bg-[var(--bg-surface-hover)] transition-colors"
                  title="Bấm để sắp xếp theo Tên hàng hóa"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Tên hàng hóa</span>
                    {renderSortIcon('name')}
                  </div>
                </th>
                <th className="py-3.5 px-4">Nhóm hàng</th>
                <th className="py-3.5 px-4 text-center">ĐVT</th>
                <th
                  onClick={() => handleSort('current_stock')}
                  className="py-3.5 px-4 text-center cursor-pointer select-none group hover:bg-[var(--bg-surface-hover)] transition-colors"
                  title="Bấm để sắp xếp theo Tồn hiện tại"
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>Tồn hiện tại</span>
                    {renderSortIcon('current_stock')}
                  </div>
                </th>
                <th className="py-3.5 px-4 text-center">Tồn an toàn</th>
                <th
                  onClick={() => handleSort('standard_price')}
                  className="py-3.5 px-4 text-right cursor-pointer select-none group hover:bg-[var(--bg-surface-hover)] transition-colors"
                  title="Bấm để sắp xếp theo Giá niêm yết"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>Giá niêm yết</span>
                    {renderSortIcon('standard_price')}
                  </div>
                </th>
                <th className="py-3.5 px-4 text-center">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] font-sans">
              {showTableLoader ? (
                <Loader variant="table" columns={9} rows={8} />
              ) : paginatedProducts.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center py-10 text-[var(--text-muted)]">
                    Không tìm thấy sản phẩm nào khớp với bộ lọc.
                  </td>
                </tr>
              ) : (
                paginatedProducts.map((p) => {
                  const isLow = p.current_stock <= p.min_stock;
                  return (
                    <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                      <td className="py-3 px-4 text-center align-middle">
                        <div
                          onClick={() => p.image_url && setZoomImage({ url: p.image_url, name: p.name, code: p.code })}
                          className={`w-16 h-16 min-w-[64px] min-h-[64px] rounded-input bg-[var(--bg-surface-warm)] border border-[var(--border-medium)] overflow-hidden inline-flex items-center justify-center transition-all ${
                            p.image_url ? 'cursor-pointer hover:border-[var(--wood-500)] hover:ring-2 hover:ring-[var(--wood-500)]/20 shadow-xs group' : ''
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
                            className="w-full h-full flex flex-col items-center justify-center text-[var(--text-muted)] bg-[var(--bg-surface-warm)] text-xs"
                            style={{ display: p.image_url ? 'none' : 'flex' }}
                          >
                            <Package className="w-6 h-6 text-[var(--text-muted)] mb-0.5" />
                            <span>Trống</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--text-primary)] align-middle">
                        <div className="leading-snug">{p.name}</div>
                        <span className="font-mono text-xs text-[var(--text-secondary)]">{p.code}</span>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--text-secondary)] align-middle">{p.category?.name || 'Chưa phân loại'}</td>
                      <td className="py-3.5 px-4 text-center text-[var(--text-secondary)] align-middle">{p.unit}</td>
                      <td className="py-3.5 px-4 text-center align-middle">
                        <span
                          className={`font-mono text-xs font-bold px-2 py-0.5 rounded-sm border ${
                            isLow
                              ? 'bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] border-[var(--semantic-alert-border)]'
                              : 'bg-[var(--semantic-success-bg)] text-[var(--semantic-success)] border-[var(--semantic-success-border)]'
                          }`}
                        >
                          {p.current_stock}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center text-[var(--text-secondary)] font-mono text-xs align-middle">{p.min_stock}</td>
                      <td className="py-3.5 px-4 text-right font-mono text-xs font-semibold text-[var(--text-primary)] align-middle">
                        {p.standard_price.toLocaleString()} đ
                      </td>
                      <td className="py-3.5 px-4 text-center align-middle">
                        <Badge variant={p.status === 'ACTIVE' ? 'success' : 'inactive'}>
                          {p.status === 'ACTIVE' ? 'Kinh doanh' : 'Ngưng bán'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right align-middle">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onSelectProductLedger(p.id)}
                            title="Xem lịch sử thẻ kho"
                            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] rounded-btn transition-colors cursor-pointer"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => handleOpenEdit(p)}
                              title="Sửa hàng hóa"
                              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] rounded-btn transition-colors cursor-pointer"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          )}
                          {canDelete && (
                            <button
                              onClick={() => handleDeleteProduct(p)}
                              title="Ngưng kinh doanh"
                              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--semantic-alert)] hover:bg-[var(--semantic-alert-bg)] rounded-btn transition-colors cursor-pointer"
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

        {/* Pagination Footer */}
        <div className="px-4 py-3.5 bg-[var(--bg-surface-warm)] border-t border-[var(--border-medium)] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--text-secondary)]">
          {/* Thông tin số lượng & Chọn pageSize */}
          <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-start">
            <span>
              Hiển thị <span className="font-semibold text-[var(--text-primary)]">{startItem} - {endItem}</span> trong tổng số{' '}
              <span className="font-semibold text-[var(--text-primary)]">{totalItems}</span> mặt hàng
            </span>

            <div className="flex items-center gap-1.5 ml-2">
              <span className="text-[var(--text-muted)] text-xs">Dòng/trang:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="py-1 px-2 bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded-input text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--wood-500)] cursor-pointer shadow-xs"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          {/* Cụm nút điều hướng phân trang */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safeCurrentPage <= 1}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-btn border border-[var(--border-medium)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
              title="Trang trước"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Trước</span>
            </button>

            <div className="flex items-center gap-1">
              {getPageNumbers().map((pageNum) => (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-7 h-7 rounded-btn text-xs font-semibold transition-colors cursor-pointer ${
                    pageNum === safeCurrentPage
                      ? 'bg-[var(--wood-800)] text-white shadow-xs'
                      : 'bg-[var(--bg-surface)] border border-[var(--border-medium)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)]'
                  }`}
                >
                  {pageNum}
                </button>
              ))}
            </div>

            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safeCurrentPage >= totalPages}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-btn border border-[var(--border-medium)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
              title="Trang sau"
            >
              <span className="hidden sm:inline">Sau</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal Thêm / Sửa Mặt Hàng */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalMode === 'create' ? 'Thêm hàng hóa mới' : 'Cập nhật hàng hóa'}
      >
        {isDraftRestored && modalMode === 'create' && (
          <div className="mb-4 p-3.5 bg-[var(--semantic-ai-bg)] border border-[var(--semantic-ai-border)] rounded-input flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--semantic-ai)]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--semantic-ai-btn)] shrink-0" />
              <span>
                <strong>Đã khôi phục bản nháp mặt hàng</strong> (lưu lúc {draftSavedTime}). Hệ thống lưu tối đa 1 ngày.
              </span>
            </div>
            <button
              type="button"
              onClick={handleDiscardDraft}
              className="text-xs font-bold text-[var(--semantic-alert)] hover:underline cursor-pointer shrink-0"
              title="Xóa nội dung nháp này để nhập từ đầu"
            >
              Xóa bản nháp
            </button>
          </div>
        )}

        <form onSubmit={handleSubmitForm} className="space-y-4">
          {formError && (
            <div className="p-3 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] text-[var(--semantic-alert)] rounded-input text-xs flex items-center gap-2 font-medium">
              <AlertTriangle className="w-4 h-4 text-[var(--semantic-alert)] shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Mã hàng hóa</label>
              <input
                type="text"
                disabled={modalMode === 'edit'}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="VD: SP001..."
                className="input-wood disabled:opacity-60"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Nhóm hàng</label>
              <select
                value={formData.category_id}
                onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                className="input-wood cursor-pointer"
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
            <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Tên mặt hàng</label>
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
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Đơn vị tính</label>
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
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Tồn an toàn</label>
              <input
                type="number"
                min="0"
                value={formData.min_stock}
                onChange={(e) => setFormData({ ...formData, min_stock: e.target.value })}
                className="input-wood font-mono"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">Giá niêm yết (đ)</label>
              <input
                type="number"
                min="0"
                step="1000"
                value={formData.standard_price}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData({
                    ...formData,
                    standard_price: val,
                    initial_unit_price: formData.has_initial_import
                      ? formData.initial_unit_price
                      : Math.round(Number(val || 0) * 0.7),
                  });
                }}
                className="input-wood font-mono"
                required
              />
            </div>
          </div>

          {/* Khởi tạo tồn kho ban đầu (Tự động tạo Phiếu nhập kho) */}
          {modalMode === 'create' && (
            <div className="p-3.5 bg-[var(--semantic-success-bg)]/40 rounded-card border border-[var(--semantic-success-border)] space-y-3">
              <label className="flex items-center gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={formData.has_initial_import}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setFormData({
                      ...formData,
                      has_initial_import: checked,
                      initial_supplier_id: checked ? (formData.initial_supplier_id || suppliers[0]?.id || '') : '',
                      initial_unit_price: checked ? (formData.initial_unit_price || Math.round(Number(formData.standard_price || 0) * 0.7)) : '',
                    });
                  }}
                  className="w-4 h-4 rounded text-[var(--semantic-success)] focus:ring-[var(--semantic-success)] accent-[var(--semantic-success)] cursor-pointer"
                />
                <span className="text-xs font-bold text-[var(--semantic-success)] flex items-center gap-1.5">
                  <ArrowDownToLine className="w-4 h-4 text-[var(--semantic-success)]" />
                  Khởi tạo tồn kho ban đầu (Tự động lập phiếu nhập kho)
                </span>
              </label>

              {formData.has_initial_import && (
                <div className="pt-2.5 border-t border-[var(--semantic-success-border)]/60 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                        Nhà cung cấp <span className="text-[var(--semantic-alert)]">*</span>
                      </label>
                      <select
                        value={formData.initial_supplier_id}
                        onChange={(e) => setFormData({ ...formData, initial_supplier_id: e.target.value })}
                        className="input-wood bg-[var(--bg-surface)] text-xs cursor-pointer"
                        required={formData.has_initial_import}
                      >
                        <option value="">-- Chọn nhà cung cấp --</option>
                        {suppliers.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                          Số lượng nhập <span className="text-[var(--semantic-alert)]">*</span>
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={formData.initial_quantity}
                          onChange={(e) => setFormData({ ...formData, initial_quantity: e.target.value })}
                          className="input-wood bg-[var(--bg-surface)] text-xs font-mono"
                          required={formData.has_initial_import}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                          Đơn giá nhập (đ) <span className="text-[var(--semantic-alert)]">*</span>
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="1000"
                          value={formData.initial_unit_price}
                          onChange={(e) => setFormData({ ...formData, initial_unit_price: e.target.value })}
                          className="input-wood bg-[var(--bg-surface)] text-xs font-mono"
                          required={formData.has_initial_import}
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                      Ghi chú phiếu nhập ban đầu
                    </label>
                    <input
                      type="text"
                      value={formData.initial_note}
                      onChange={(e) => setFormData({ ...formData, initial_note: e.target.value })}
                      placeholder="VD: Nhập kho ban đầu khi tạo danh mục..."
                      className="input-wood bg-[var(--bg-surface)] text-xs"
                    />
                  </div>

                  <div className="p-2.5 bg-[var(--semantic-success-bg)] border border-[var(--semantic-success-border)] rounded-btn text-xs text-[var(--semantic-success)] flex items-center justify-between font-medium">
                    <span>Tổng tiền phiếu nhập dự kiến:</span>
                    <span className="font-bold font-mono text-sm">
                      {((Number(formData.initial_quantity) || 0) * (Number(formData.initial_unit_price) || 0)).toLocaleString('vi-VN')} đ
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Hình ảnh mặt hàng */}
          <div className="p-3.5 bg-[var(--bg-surface-warm)] rounded-card border border-[var(--border-medium)] space-y-2.5">
            <label className="block text-xs font-semibold text-[var(--text-primary)]">
              Hình ảnh mặt hàng
            </label>
            <div className="flex items-center gap-3.5">
              {/* Box xem trước ảnh */}
              <div className="w-16 h-16 rounded-input border border-[var(--border-medium)] bg-[var(--bg-surface)] overflow-hidden flex items-center justify-center shrink-0 shadow-xs">
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
                  className="w-full h-full flex flex-col items-center justify-center text-[var(--text-muted)] text-xs p-1 text-center"
                  style={{ display: (imagePreview || formData.image_url) ? 'none' : 'flex' }}
                >
                  <ImageIcon className="w-5 h-5 text-[var(--text-muted)] mb-0.5" />
                  <span>Trống</span>
                </div>
              </div>

              {/* Nút Upload & Input URL */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <label className="btn-secondary text-xs cursor-pointer shadow-xs">
                    <Upload className="w-3.5 h-3.5 text-[var(--wood-500)]" />
                    <span>Tải ảnh từ máy...</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageFileChange}
                    />
                  </label>
                  {imageFile && (
                    <span className="text-xs text-[var(--semantic-success)] font-medium truncate max-w-[180px]">
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
                  className="input-wood bg-[var(--bg-surface)]"
                />
              </div>
            </div>
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

      {/* Modal Xem Ảnh Phóng To */}
      {zoomImage && (
        <Modal
          isOpen={!!zoomImage}
          onClose={() => setZoomImage(null)}
          title={`Hình ảnh: [${zoomImage.code}] ${zoomImage.name}`}
        >
          <div className="flex flex-col items-center justify-center p-3 space-y-3">
            <div className="w-full max-h-[60vh] overflow-hidden rounded-card bg-[var(--bg-surface-warm)] flex items-center justify-center border border-[var(--border-medium)] shadow-sm">
              <img
                src={zoomImage.url}
                alt={zoomImage.name}
                className="max-h-[58vh] max-w-full object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                  if (e.currentTarget.nextSibling) e.currentTarget.nextSibling.style.display = 'flex';
                }}
              />
              <div className="hidden flex-col items-center justify-center p-10 text-[var(--text-muted)]">
                <Package className="w-12 h-12 mb-2 text-[var(--text-muted)]" />
                <span className="text-xs">Không thể tải file ảnh này</span>
              </div>
            </div>
            <p className="text-xs text-[var(--text-muted)] font-mono text-center">
              Đường dẫn: {zoomImage.url}
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default Products;
