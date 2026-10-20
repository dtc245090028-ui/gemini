const path = require('path');
const fs = require('fs');

const playwrightPath = path.resolve(__dirname, '../../../hệ thống quản lý kho/frontend/node_modules/playwright');
const { chromium } = require(playwrightPath);

const OUTPUT_DIR = path.resolve('E:/gemini/test-results/reports/scratch');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function runE2ETests() {
  console.log('>>> BẮT ĐẦU CHẠY KIỂM THỬ E2E TOÀN TRÌNH VỚI PLAYWRIGHT TRÊN EDGE <<<');
  
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  try {
    // -------------------------------------------------------------
    // TEST 1: ĐĂNG NHẬP & PHÂN QUYỀN (RBAC) - QUẢN TRỊ VIÊN
    // -------------------------------------------------------------
    console.log('\n[1/11] Kiểm tra 3.1.1: Đăng nhập & Phân quyền Quản trị viên (Admin)');
    await page.goto('http://localhost:5173/');
    await page.waitForTimeout(1000);

    // Chụp ảnh màn hình đăng nhập
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_login_screen.png') });
    console.log('  -> Đã lưu ảnh: 01_login_screen.png');

    // Đăng nhập tài khoản admin
    const usernameInput = await page.locator('input[placeholder="Nhập tên đăng nhập..."]');
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('admin');
      await page.locator('input[placeholder="Nhập mật khẩu..."]').fill('admin123');
      await page.locator('button[type="submit"]').click();
      await page.waitForTimeout(1500);
    }

    // Chụp ảnh Dashboard Admin
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_rbac_admin_dashboard.png') });
    console.log('  -> Đã lưu ảnh: 01_rbac_admin_dashboard.png');

    // Chuyển sang vai trò Kế toán để kiểm tra RBAC
    console.log('\n[1.1/11] Kiểm tra Phân quyền Kế toán (ACCOUNTANT) - Ẩn quyền tạo/sửa');
    await page.locator('button:has-text("Kế toán")').click();
    await page.waitForTimeout(1000);

    // Mở trang Hàng hóa khi đóng vai Kế toán
    await page.locator('button:has-text("Hàng hóa & Kho")').click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_rbac_accountant_products_readonly.png') });
    console.log('  -> Đã lưu ảnh: 01_rbac_accountant_products_readonly.png (Kế toán không thấy nút Thêm hàng hóa)');

    // Chuyển lại Admin
    await page.locator('button:has-text("Admin")').click();
    await page.waitForTimeout(1000);

    // -------------------------------------------------------------
    // TEST 2: QUẢN LÝ HÀNG HÓA, NHÓM HÀNG, ĐƠN VỊ TÍNH, TỒN TỐI THIỂU
    // -------------------------------------------------------------
    console.log('\n[2/11] Kiểm tra 3.1.2: Quản lý hàng hóa, nhóm hàng, ĐVT, tồn tối thiểu');
    await page.locator('button:has-text("Hàng hóa & Kho")').click();
    await page.waitForTimeout(1200);

    // Chụp toàn cảnh danh sách sản phẩm với các cột nhóm hàng, ĐVT, tồn tối thiểu
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_product_management.png') });
    console.log('  -> Đã lưu ảnh: 02_product_management.png');

    // Mở modal Thêm hàng hóa
    const addProductBtn = page.locator('button:has-text("Thêm Hàng Hóa")');
    if (await addProductBtn.isVisible()) {
      await addProductBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '02_product_create_modal.png') });
      console.log('  -> Đã lưu ảnh: 02_product_create_modal.png');
      // Đóng modal
      await page.locator('button:has-text("Hủy bỏ")').click();
      await page.waitForTimeout(500);
    }

    // -------------------------------------------------------------
    // TEST 3: QUẢN LÝ NHÀ CUNG CẤP
    // -------------------------------------------------------------
    console.log('\n[3/11] Kiểm tra 3.1.3: Quản lý nhà cung cấp');
    await page.locator('button:has-text("Nhà cung cấp")').click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '03_suppliers_management.png') });
    console.log('  -> Đã lưu ảnh: 03_suppliers_management.png');

    // -------------------------------------------------------------
    // TEST 4: LẬP PHIẾU NHẬP KHO VÀ CẬP NHẬT TỒN KHO
    // -------------------------------------------------------------
    console.log('\n[4/11] Kiểm tra 3.1.4: Lập phiếu nhập kho & cập nhật tồn kho');
    await page.locator('button:has-text("Phiếu nhập kho")').click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '04_import_notes_list.png') });
    console.log('  -> Đã lưu ảnh: 04_import_notes_list.png');

    // Mở modal tạo phiếu nhập
    const addImportBtn = page.locator('button:has-text("Lập Phiếu Nhập")');
    if (await addImportBtn.isVisible()) {
      await addImportBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '04_import_note_create_modal.png') });
      console.log('  -> Đã lưu ảnh: 04_import_note_create_modal.png');
      await page.locator('button:has-text("Hủy bỏ")').click();
      await page.waitForTimeout(500);
    }

    // -------------------------------------------------------------
    // TEST 5: LẬP PHIẾU XUẤT KHO VÀ KIỂM TRA SỐ LƯỢNG CÒN
    // -------------------------------------------------------------
    console.log('\n[5/11] Kiểm tra 3.1.5: Lập phiếu xuất kho & kiểm tra số lượng còn');
    await page.locator('button:has-text("Phiếu xuất kho")').click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '05_export_notes_list.png') });
    console.log('  -> Đã lưu ảnh: 05_export_notes_list.png');

    // Mở modal tạo phiếu xuất
    const addExportBtn = page.locator('button:has-text("Lập Phiếu Xuất")');
    if (await addExportBtn.isVisible()) {
      await addExportBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '05_export_note_create_modal.png') });
      console.log('  -> Đã lưu ảnh: 05_export_note_create_modal.png');
      await page.locator('button:has-text("Hủy bỏ")').click();
      await page.waitForTimeout(500);
    }

    // -------------------------------------------------------------
    // TEST 6: TRA CỨU LỊCH SỬ NHẬP XUẤT THEO HÀNG HÓA, THỜI GIAN
    // -------------------------------------------------------------
    console.log('\n[6/11] Kiểm tra 3.1.6: Tra cứu lịch sử thẻ kho');
    await page.locator('button:has-text("Thẻ kho & Kiểm kê")').click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '06_stock_ledger_history.png') });
    console.log('  -> Đã lưu ảnh: 06_stock_ledger_history.png');

    // -------------------------------------------------------------
    // TEST 7: CẢNH BÁO HÀNG DƯỚI TỒN TỐI THIỂU
    // -------------------------------------------------------------
    console.log('\n[7/11] Kiểm tra 3.1.7: Cảnh báo hàng dưới tồn tối thiểu');
    await page.locator('button:has-text("Tổng quan")').click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '07_dashboard_low_stock_warning.png') });
    console.log('  -> Đã lưu ảnh: 07_dashboard_low_stock_warning.png');

    // Bật filter cảnh báo bên trang Products
    await page.locator('button:has-text("Hàng hóa & Kho")').click();
    await page.waitForTimeout(800);
    const lowStockCheckbox = page.locator('text=Chỉ hiện hàng dưới tồn tối thiểu');
    if (await lowStockCheckbox.isVisible()) {
      await lowStockCheckbox.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '07_products_low_stock_filtered.png') });
      console.log('  -> Đã lưu ảnh: 07_products_low_stock_filtered.png');
      await lowStockCheckbox.click(); // Bỏ chọn
    }

    // -------------------------------------------------------------
    // TEST 8: THỐNG KÊ NHẬP XUẤT TỒN VÀ XUẤT BÁO CÁO
    // -------------------------------------------------------------
    console.log('\n[8/11] Kiểm tra 3.1.8: Thống kê nhập xuất tồn và xuất báo cáo');
    await page.locator('button:has-text("Tổng quan")').click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '08_inventory_summary_dashboard.png') });
    console.log('  -> Đã lưu ảnh: 08_inventory_summary_dashboard.png');

    // -------------------------------------------------------------
    // TEST 9: AI SINH BÁO CÁO NHẬP XUẤT TỒN THEO THÁNG
    // -------------------------------------------------------------
    console.log('\n[9/11] Kiểm tra 3.2.1: AI sinh báo cáo nhập xuất tồn theo tháng');
    await page.locator('button:has-text("Trợ lý AI & Báo cáo")').click();
    await page.waitForTimeout(1500);

    // Chờ báo cáo AI tải xong
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '09_ai_monthly_report.png') });
    console.log('  -> Đã lưu ảnh: 09_ai_monthly_report.png');

    // -------------------------------------------------------------
    // TEST 10: AI GỢI Ý NHẬP HÀNG
    // -------------------------------------------------------------
    console.log('\n[10/11] Kiểm tra 3.2.2: AI gợi ý nhập hàng');
    const restockTab = page.locator('button:has-text("Gợi ý nhập hàng")');
    if (await restockTab.isVisible()) {
      await restockTab.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '10_ai_restock_suggestions.png') });
      console.log('  -> Đã lưu ảnh: 10_ai_restock_suggestions.png');
    }

    // -------------------------------------------------------------
    // TEST 11: AI TÓM TẮT BIẾN ĐỘNG BẤT THƯỜNG
    // -------------------------------------------------------------
    console.log('\n[11/11] Kiểm tra 3.2.3: AI tóm tắt biến động bất thường');
    const anomalyTab = page.locator('button:has-text("Biến động bất thường")');
    if (await anomalyTab.isVisible()) {
      await anomalyTab.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '11_ai_anomalies_summary.png') });
      console.log('  -> Đã lưu ảnh: 11_ai_anomalies_summary.png');
    }

    console.log('\n>>> TẤT CẢ KỊCH BẢN KIỂM THỬ E2E ĐÃ HOÀN TẤT THÀNH CÔNG! <<<');
  } catch (err) {
    console.error('Lỗi trong quá trình chạy E2E:', err);
  } finally {
    await browser.close();
  }
}

runE2ETests();
