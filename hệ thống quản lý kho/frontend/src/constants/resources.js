/**
 * Định danh tài nguyên sự kiện SSE chuẩn mực (Single Source of Truth phía Frontend).
 * Đồng bộ 1:1 với EventResource phía backend (app/core/events.py).
 */
export const RESOURCES = {
  PRODUCTS: 'products',
  CATEGORIES: 'categories',
  SUPPLIERS: 'suppliers',
  IMPORT_NOTES: 'import_notes',
  EXPORT_NOTES: 'export_notes',
  STOCK_LEDGER: 'stock_ledger',
  REPORTS: 'reports',
};

export default RESOURCES;
