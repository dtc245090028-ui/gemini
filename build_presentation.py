import sys
import os
import pptx
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Color definitions
BG_DARK = RGBColor(15, 23, 42)        # #0F172A Dark Navy Slate
BG_DARK_CARD = RGBColor(30, 41, 59)   # #1E293B
BG_LIGHT = RGBColor(248, 250, 252)    # #F8FAFC Crisp Light
WHITE = RGBColor(255, 255, 255)
TEXT_DARK = RGBColor(15, 23, 42)      # #0F172A
TEXT_MUTED = RGBColor(71, 85, 105)    # #475569 Slate Muted
TEXT_LIGHT = RGBColor(241, 245, 249)  # #F1F5F9

# Accents
WOOD_PRIMARY = RGBColor(180, 83, 9)    # #B45309 Warm Wood Amber
WOOD_ACCENT = RGBColor(217, 119, 6)    # #D97706 Bright Amber
WOOD_LIGHT = RGBColor(254, 243, 199)   # #FEF3C7 Warm Light
TEAL_PRIMARY = RGBColor(13, 148, 136)  # #0D9488 Tech Teal
TEAL_LIGHT = RGBColor(240, 253, 250)   # #F0FDFA
BLUE_PRIMARY = RGBColor(2, 132, 199)   # #0284C7 Sky Blue
BLUE_LIGHT = RGBColor(239, 246, 255)   # #EFF6FF
SUCCESS_GREEN = RGBColor(16, 185, 129) # #10B981 Emerald
DANGER_RED = RGBColor(239, 68, 68)     # #EF4444 Alert Red
BORDER_LIGHT = RGBColor(226, 232, 240) # #E2E8F0
BORDER_DARK = RGBColor(51, 65, 85)     # #334155
CARD_GRAY = RGBColor(241, 245, 249)    # #F1F5F9

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_slide_background(slide, color):
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = color
    bg_shape.line.fill.background()
    return bg_shape

def add_header(slide, tag, title, subtitle):
    # Top Tag
    tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.32))
    tf_tag = tag_box.text_frame
    tf_tag.word_wrap = True
    tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag.upper()
    p_tag.font.name = FONT_HEADING
    p_tag.font.size = Pt(10)
    p_tag.font.bold = True
    p_tag.font.color.rgb = WOOD_PRIMARY
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.733), Inches(0.52))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_DARK
    
    # Subtitle
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.24), Inches(11.733), Inches(0.35))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED

    # Header Divider Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.65), Inches(11.733), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER_LIGHT
    line.line.fill.background()

def add_footer(slide, current_slide, total_slides=16):
    foot_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(7.0), Inches(11.733), Inches(0.012))
    foot_line.fill.solid()
    foot_line.fill.fore_color.rgb = BORDER_LIGHT
    foot_line.line.fill.background()
    
    # Left footer: document label
    foot_box_l = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(8.0), Inches(0.3))
    tf_l = foot_box_l.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_top = tf_l.margin_right = tf_l.margin_bottom = 0
    p_l = tf_l.paragraphs[0]
    p_l.text = "Hệ thống Quản lý Kho Thông minh (WMS AI) — Đề tài 07 | Phiên bản chuẩn hóa 2026"
    p_l.font.name = FONT_BODY
    p_l.font.size = Pt(9)
    p_l.font.color.rgb = TEXT_MUTED
    
    # Right footer: slide index
    foot_box_r = slide.shapes.add_textbox(Inches(9.533), Inches(7.05), Inches(3.0), Inches(0.3))
    tf_r = foot_box_r.text_frame
    tf_r.word_wrap = True
    tf_r.margin_left = tf_r.margin_top = tf_r.margin_right = tf_r.margin_bottom = 0
    p_r = tf_r.paragraphs[0]
    p_r.text = f"Trang {current_slide} / {total_slides}"
    p_r.alignment = PP_ALIGN.RIGHT
    p_r.font.name = FONT_BODY
    p_r.font.size = Pt(9)
    p_r.font.bold = True
    p_r.font.color.rgb = WOOD_PRIMARY

def add_card(slide, left, top, width, height, bg_color=WHITE, border_color=BORDER_LIGHT):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)
    else:
        shape.line.fill.background()
    return shape

def add_speaker_notes(slide, notes_text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = notes_text

# ==============================================================================
# SLIDE 1: TRANG BÌA (TITLE SLIDE)
# ==============================================================================
def build_slide_1(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_DARK)
    
    # Decorative Top Accent Bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(11.733), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = WOOD_ACCENT
    bar.line.fill.background()
    
    # Organization Header
    org_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.9), Inches(11.733), Inches(0.8))
    tf_org = org_box.text_frame
    tf_org.word_wrap = True
    p1 = tf_org.paragraphs[0]
    p1.text = "BỘ GIÁO DỤC VÀ ĐÀO TẠO — TRƯỜNG ĐẠI HỌC CÔNG NGHỆ"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = WOOD_LIGHT
    
    p2 = tf_org.add_paragraph()
    p2.text = "KHOA CÔNG NGHỆ THÔNG TIN • BỘ MÔN CÔNG NGHỆ PHẦN MỀM & TRÍ TUỆ NHÂN TẠO"
    p2.font.name = FONT_BODY
    p2.font.size = Pt(11)
    p2.font.color.rgb = RGBColor(203, 213, 225)
    
    # Topic Badge
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.0), Inches(4.5), Inches(0.42))
    badge.fill.solid()
    badge.fill.fore_color.rgb = BG_DARK_CARD
    badge.line.color.rgb = WOOD_ACCENT
    badge.line.width = Pt(1.5)
    tf_b = badge.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "ĐỀ TÀI NGHIÊN CỨU & PHÁT TRIỂN 07"
    p_b.font.name = FONT_HEADING
    p_b.font.size = Pt(11)
    p_b.font.bold = True
    p_b.font.color.rgb = WOOD_LIGHT
    p_b.alignment = PP_ALIGN.CENTER
    
    # Main Report Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.6), Inches(11.733), Inches(2.1))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    
    p_sub = tf_t.paragraphs[0]
    p_sub.text = "BÁO CÁO ĐẶC TẢ YÊU CẦU & THIẾT KẾ KIẾN TRÚC HỆ THỐNG"
    p_sub.font.name = FONT_HEADING
    p_sub.font.size = Pt(18)
    p_sub.font.bold = True
    p_sub.font.color.rgb = RGBColor(148, 163, 184)
    
    p_main = tf_t.add_paragraph()
    p_main.text = "HỆ THỐNG QUẢN LÝ KHO THÔNG MINH\nTÍCH HỢP TRÍ TUỆ NHÂN TẠO (WMS AI)"
    p_main.font.name = FONT_HEADING
    p_main.font.size = Pt(32)
    p_main.font.bold = True
    p_main.font.color.rgb = WHITE
    
    # Metadata Cards (2 Columns)
    # Card Left: Execution Info
    card_l = add_card(slide, Inches(0.8), Inches(4.9), Inches(5.6), Inches(1.8), BG_DARK_CARD, BORDER_DARK)
    tf_cl = card_l.text_frame
    tf_cl.margin_left = Inches(0.25)
    tf_cl.margin_top = Inches(0.2)
    
    p_cl1 = tf_cl.paragraphs[0]
    p_cl1.text = "THÔNG TIN HỌC PHẦN & TÁC GIẢ"
    p_cl1.font.name = FONT_HEADING
    p_cl1.font.size = Pt(11)
    p_cl1.font.bold = True
    p_cl1.font.color.rgb = WOOD_LIGHT
    
    items_l = [
        "Học phần: Triển khai Phần mềm & AI trong CNPM",
        "Nhóm tác giả: Nhóm Nghiên cứu & Phát triển WMS AI",
        "Phiên bản: Chuẩn hóa 2026 (Nghiệm thu Tháng 09/2026)"
    ]
    for it in items_l:
        p = tf_cl.add_paragraph()
        p.text = "• " + it
        p.font.name = FONT_BODY
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(226, 232, 240)
        
    # Card Right: Tech Stack
    card_r = add_card(slide, Inches(6.8), Inches(4.9), Inches(5.733), Inches(1.8), BG_DARK_CARD, BORDER_DARK)
    tf_cr = card_r.text_frame
    tf_cr.margin_left = Inches(0.25)
    tf_cr.margin_top = Inches(0.2)
    
    p_cr1 = tf_cr.paragraphs[0]
    p_cr1.text = "NỀN TẢNG CÔNG NGHỆ CHỦ ĐẠO"
    p_cr1.font.name = FONT_HEADING
    p_cr1.font.size = Pt(11)
    p_cr1.font.bold = True
    p_cr1.font.color.rgb = TEAL_PRIMARY
    
    items_r = [
        "Backend: FastAPI (Python 3.14), SQLAlchemy ORM, Uvicorn ASGI",
        "Frontend: React 18 SPA, Vite Bundler, Tailwind CSS (Warm Wood)",
        "AI Engine: Google Gemini LLM tích hợp Heuristic Fallback 24/7",
        "Cơ sở dữ liệu: SQLite / PostgreSQL chuẩn hóa 3NF, ACID an toàn"
    ]
    for it in items_r:
        p = tf_cr.add_paragraph()
        p.text = "• " + it
        p.font.name = FONT_BODY
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(226, 232, 240)
        
    add_speaker_notes(slide, 
        "Kính chào Quý Thầy Cô trong Hội đồng đánh giá và các bạn sinh viên.\n"
        "Hôm nay, nhóm chúng em xin đại diện báo cáo kết quả nghiên cứu và thiết kế kiến trúc kỹ thuật của Đề tài 07: "
        "'Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI)'.\n"
        "Đề tài được xây dựng trên nền tảng công nghệ hiện đại nhất hiện nay: FastAPI chạy trên Python 3.14, React 18 SPA "
        "kết hợp công nghệ Generative AI từ Google Gemini và bộ động cơ dự phòng Heuristic nội tại. "
        "Sau đây, chúng em xin đi vào chi tiết cấu trúc và giải pháp kỹ thuật của hệ thống."
    )

# ==============================================================================
# SLIDE 2: 3 BÀI TOÁN CỐT LÕI
# ==============================================================================
def build_slide_2(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 2: Bối Cảnh & Thách Thức", 
               "3 Bài Toán Nhức Nhối Của Kho Bãi Truyền Thống",
               "Hệ thống giải quyết triệt để 3 vấn đề gây thất thoát, nghẽn dòng chảy và sai lệch số liệu")
    add_footer(slide, 2)
    
    card_w = Inches(3.7)
    card_h = Inches(4.9)
    top_pos = Inches(1.9)
    
    # Column 1: Lỗi tồn âm
    c1 = add_card(slide, Inches(0.8), top_pos, card_w, card_h, WHITE, BORDER_LIGHT)
    tf1 = c1.text_frame
    tf1.margin_left = tf1.margin_right = Inches(0.25)
    tf1.margin_top = Inches(0.25)
    
    # Badge inside card
    p = tf1.paragraphs[0]
    p.text = "VẤN ĐỀ 1"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = DANGER_RED
    
    p = tf1.add_paragraph()
    p.text = "Lỗi Tồn Kho Âm (Negative Stock)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    bullets1 = [
        ("Nỗi đau thực tế: ", "Thủ kho xuất quá số lượng tồn thực tế hoặc race-condition do nhiều người cùng tạo phiếu xuất đồng thời."),
        ("Hậu quả nghiêm trọng: ", "Sai lệch sổ sách kế toán, giao thiếu hàng cho đối tác, vỡ cam kết đơn hàng, thất thoát tài chính."),
        ("Giải pháp Đề tài 07: ", "Thiết lập CHỐT CHẶN KÉP: Kiểm tra nguyên tử (Atomic Check) ở tầng Service và CheckConstraint('current_stock >= 0') ở tầng đĩa CSDL.")
    ]
    for b_title, b_desc in bullets1:
        p_t = tf1.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_c = tf1.add_paragraph()
        p_c.text = "  " + b_desc
        p_c.font.name = FONT_BODY
        p_c.font.size = Pt(9.5)
        p_c.font.color.rgb = TEXT_MUTED

    # Column 2: Giam hàng ảo
    c2 = add_card(slide, Inches(4.8), top_pos, card_w, card_h, WHITE, BORDER_LIGHT)
    tf2 = c2.text_frame
    tf2.margin_left = tf2.margin_right = Inches(0.25)
    tf2.margin_top = Inches(0.25)
    
    p = tf2.paragraphs[0]
    p.text = "VẤN ĐỀ 2"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p = tf2.add_paragraph()
    p.text = "Giam Giữ Hàng Ảo (Ghost Lock)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    bullets2 = [
        ("Nỗi đau thực tế: ", "Hệ thống cũ vừa bấm tạo đơn là lập tức trừ kho, dù hàng chưa đóng gói và chưa rời kho vật lý."),
        ("Hậu quả nghiêm trọng: ", "Khi khách hủy đơn hoặc đơn giao thất bại, hàng bị kẹt trạng thái ảo, đơn hàng khác không thể lấy hàng để xuất."),
        ("Giải pháp Đề tài 07: ", "CỖ MÁY TRẠNG THÁI 3 BƯỚC: Phân tách rạch ròi CONFIRMED (không giam hàng) -> SHIPPING (trừ kho thực tế) -> COMPLETED. Hủy đơn tự động hoàn kho 100%.")
    ]
    for b_title, b_desc in bullets2:
        p_t = tf2.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_c = tf2.add_paragraph()
        p_c.text = "  " + b_desc
        p_c.font.name = FONT_BODY
        p_c.font.size = Pt(9.5)
        p_c.font.color.rgb = TEXT_MUTED

    # Column 3: Thao tác rườm rà
    c3 = add_card(slide, Inches(8.8), top_pos, card_w, card_h, WHITE, BORDER_LIGHT)
    tf3 = c3.text_frame
    tf3.margin_left = tf3.margin_right = Inches(0.25)
    tf3.margin_top = Inches(0.25)
    
    p = tf3.paragraphs[0]
    p.text = "VẤN ĐỀ 3"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = TEAL_PRIMARY
    
    p = tf3.add_paragraph()
    p.text = "Thao Tác Nhập Liệu Chậm & Dễ Sai"
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    bullets3 = [
        ("Nỗi đau thực tế: ", "Bắt thủ kho phải nhớ mã SKU kỹ thuật dài dòng; dropdown chọn sản phẩm cuộn hàng trăm dòng hoa mắt mỏi tay."),
        ("Hậu quả nghiêm trọng: ", "Tốc độ xuất nhập bị chậm, dễ chọn nhầm chủng loại hàng hóa gây sai lệch kho vật lý."),
        ("Giải pháp Đề tài 07: ", "ĐỘT PHÁ PRODUCTSELECT: Tìm bằng chữ cái đầu (blv -> Bàn Làm Việc), khử dấu tiếng Việt NFD, tự bôi đen click, ẩn SKU kỹ thuật chỉ để Tên + Số tồn.")
    ]
    for b_title, b_desc in bullets3:
        p_t = tf3.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_c = tf3.add_paragraph()
        p_c.text = "  " + b_desc
        p_c.font.name = FONT_BODY
        p_c.font.size = Pt(9.5)
        p_c.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Ở slide này, nhóm xin làm rõ 3 bài toán lớn nhất mà thực tế các doanh nghiệp kho bãi đang đối mặt:\n"
        "1. Lỗi tồn kho âm: Khi nhiều thủ kho cùng xuất một mặt hàng, nếu không có cơ chế giao dịch ACID nghiêm ngặt, tồn kho sẽ bị âm.\n"
        "2. Hiện tượng giam giữ hàng ảo: Các phần mềm đơn giản thường trừ kho ngay khi lập đơn, khiến hàng bị treo dù đơn chưa giao đi.\n"
        "3. Trải nghiệm thao tác: Thủ kho là người làm việc chân tay, cần phần mềm gõ nhanh, tìm nhanh chứ không thể nhớ hàng trăm mã SKU phức tạp.\n"
        "Hệ thống WMS AI được thiết kế giải quyết triệt để cả 3 điểm nghẽn này ngay từ cấp độ kiến trúc."
    )

# ==============================================================================
# SLIDE 3: KIẾN TRÚC TỔNG THỂ 3-TIER CLEAN ARCHITECTURE
# ==============================================================================
def build_slide_3(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 8: Thiết Kế Cấu Trúc Hệ Thống",
               "Kiến Trúc Phân Tầng 3-Tier Clean Architecture",
               "Phân tách rạch ròi Presentation, Business Service và Persistence đảm bảo tính mở rộng cao")
    add_footer(slide, 3)
    
    layer_w = Inches(11.733)
    layer_h = Inches(1.48)
    
    # Layer 1: Presentation
    l1 = add_card(slide, Inches(0.8), Inches(1.9), layer_w, layer_h, WHITE, BORDER_LIGHT)
    tf1 = l1.text_frame
    tf1.margin_left = tf1.margin_right = Inches(0.3)
    tf1.margin_top = Inches(0.18)
    
    p = tf1.paragraphs[0]
    p.text = "TẦNG TRÌNH DIỄN (PRESENTATION LAYER) — REACT 18 SPA & VITE"
    p.font.name = FONT_HEADING
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = BLUE_PRIMARY
    
    p_body = tf1.add_paragraph()
    p_body.text = "• Công nghệ: React 18, Vite Bundler (Gzip bundle chỉ ~95KB tải tức thì), Tailwind CSS công thái học Warm Wood & Slate.\n" \
                  "• Cấu trúc module: components/ (ProductSelect, Modal, Badge), context/ (AuthContext), pages/ (Dashboard, Import, Export, StockLedger, AI Copilot), api/ (Axios client tích hợp JWT Interceptors)."
    p_body.font.name = FONT_BODY
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = TEXT_DARK
    
    # Layer 2: Business Service Layer
    l2 = add_card(slide, Inches(0.8), Inches(3.55), layer_w, layer_h, WHITE, BORDER_LIGHT)
    tf2 = l2.text_frame
    tf2.margin_left = tf2.margin_right = Inches(0.3)
    tf2.margin_top = Inches(0.18)
    
    p = tf2.paragraphs[0]
    p.text = "TẦNG DỊCH VỤ NGHIỆP VỤ (BUSINESS SERVICE LAYER) — FASTAPI (PYTHON 3.14)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p_body = tf2.add_paragraph()
    p_body.text = "• HTTP Router: Tầng API endpoints chỉ nhận request, xác thực RBAC dependencies (deps.py) và serialize response qua Pydantic.\n" \
                  "• Service Modules: inventory_service.py (quản trị toàn vẹn giao dịch ACID, chống tồn âm), ai_service.py (tích hợp Google Gemini LLM), fallback_service.py (động cơ phân tích Heuristic nội tại)."
    p_body.font.name = FONT_BODY
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = TEXT_DARK

    # Layer 3: Persistence Layer
    l3 = add_card(slide, Inches(0.8), Inches(5.2), layer_w, layer_h, WHITE, BORDER_LIGHT)
    tf3 = l3.text_frame
    tf3.margin_left = tf3.margin_right = Inches(0.3)
    tf3.margin_top = Inches(0.18)
    
    p = tf3.paragraphs[0]
    p.text = "TẦNG DỮ LIỆU & LƯU TRỮ (PERSISTENCE LAYER) — SQLALCHEMY & CSDL 3NF"
    p.font.name = FONT_HEADING
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = TEAL_PRIMARY
    
    p_body = tf3.add_paragraph()
    p_body.text = "• Cơ chế kiểm soát: 9 bảng thực thể chuẩn 3NF, PRAGMA foreign_keys = ON, CheckConstraint('current_stock >= 0') ở cấp bảng.\n" \
                  "• Quản lý phiên làm việc: SQLAlchemy Session tự động Rollback hoàn toàn khi gặp bất kỳ ngoại lệ nào; hỗ trợ chuyển đổi linh hoạt SQLite / PostgreSQL qua Connection Pooling."
    p_body.font.name = FONT_BODY
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Đây là sơ đồ kiến trúc 3 tầng chuẩn Clean Architecture của hệ thống:\n"
        "- Tầng Giao diện được tối ưu hóa cực kỳ nhẹ, kích thước bundle chỉ 95KB sau nén Gzip, giúp mở ứng dụng ngay tức thì trên các thiết bị máy tính bảng hoặc máy quét mã cầm tay của thủ kho.\n"
        "- Tầng Backend viết bằng FastAPI trên Python 3.14 tận dụng cơ chế Asynchronous I/O của Uvicorn, chia tách tri thức nghiệp vụ nằm hoàn toàn trong tầng Services thay vì để code lộn xộn trong Router.\n"
        "- Tầng Database áp dụng ORM SQLAlchemy, bảo đảm tính độc lập với hệ quản trị cơ sở dữ liệu."
    )

# ==============================================================================
# SLIDE 4: MA TRẬN PHÂN QUYỀN RBAC
# ==============================================================================
def build_slide_4(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 2: Nhóm Người Dùng & Phân Quyền",
               "Ma Trận Phân Quyền RBAC 3 Cấp Độ (Role-Based Access Control)",
               "Thiết lập nguyên tắc 'Đúng người - Đúng việc' & Bảo vệ an toàn dữ liệu nhạy cảm")
    add_footer(slide, 4)
    
    # Table layout
    rows = 6
    cols = 4
    left = Inches(0.8)
    top = Inches(1.9)
    width = Inches(11.733)
    height = Inches(3.6)
    
    table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    
    # Column widths
    table.columns[0].width = Inches(3.633)
    table.columns[1].width = Inches(2.7)
    table.columns[2].width = Inches(2.7)
    table.columns[3].width = Inches(2.7)
    
    table_data = [
        ["Phân Hệ / Nghiệp Vụ Chức Năng", "Quản Trị Viên (Admin)", "Thủ Kho (Warehouse Keeper)", "Kế Toán (Accountant)"],
        ["Quản lý người dùng & Cấu hình AI", "Toàn quyền (CRUD)", "Không có quyền", "Không có quyền"],
        ["Danh mục hàng hóa & Nhà cung cấp", "Toàn quyền (CRUD)", "Toàn quyền (CRUD)", "Chỉ xem (Read Only)"],
        ["Lập phiếu nhập & Lập phiếu xuất", "Toàn quyền thao tác", "Toàn quyền thao tác", "Không có quyền tạo / sửa"],
        ["Kiểm kê bù trừ kho (Stock Adjust)", "Toàn quyền thực hiện", "Toàn quyền thực hiện", "Không có quyền thực hiện"],
        ["Sổ cái thẻ kho & Báo cáo tổng hợp", "Toàn quyền xem / xuất", "Xem thẻ kho chi tiết", "Toàn quyền đối soát & báo cáo"]
    ]
    
    for r_idx, row in enumerate(table_data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(10.5)
            
            if r_idx == 0:
                p.font.bold = True
                p.font.name = FONT_HEADING
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = BG_DARK
            else:
                if c_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = TEXT_DARK
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = CARD_GRAY
                else:
                    cell.fill.solid()
                    if "Toàn quyền" in val:
                        p.font.color.rgb = WOOD_PRIMARY
                        p.font.bold = True
                        cell.fill.fore_color.rgb = WHITE
                    elif "Không có quyền" in val:
                        p.font.color.rgb = DANGER_RED
                        cell.fill.fore_color.rgb = WHITE
                    else:
                        p.font.color.rgb = TEAL_PRIMARY
                        p.font.bold = True
                        cell.fill.fore_color.rgb = WHITE

    # Callout bottom card
    c_note = add_card(slide, Inches(0.8), Inches(5.65), Inches(11.733), Inches(1.15), WOOD_LIGHT, WOOD_PRIMARY)
    tf_n = c_note.text_frame
    tf_n.margin_left = tf_n.margin_right = Inches(0.25)
    tf_n.margin_top = Inches(0.15)
    
    p = tf_n.paragraphs[0]
    p.text = "📌 NGUYÊN TẮC BẢO MẬT & PHÂN TÁCH TRÁCH NHIỆM (SEPARATION OF CONCERNS)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p2 = tf_n.add_paragraph()
    p2.text = "• Thủ kho chịu trách nhiệm vật lý về hàng hóa: Không nhìn thấy giá vốn nhạy cảm của doanh nghiệp trên giao diện để tránh rò rỉ thông tin.\n" \
              "• Kế toán chịu trách nhiệm số liệu tài chính: Không can thiệp sửa đổi kho vật lý nhưng có toàn quyền đối soát lịch sử biến động Thẻ kho 100% minh bạch."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Về phân quyền, đồ án cài đặt mô hình RBAC 3 cấp độ:\n"
        "- Admin: Quản lý hạ tầng, tài khoản và cấu hình prompt/API key của AI Copilot.\n"
        "- Thủ kho: Trực tiếp thao tác nhập, xuất và kiểm kê; tập trung vào số lượng vật lý.\n"
        "- Kế toán: Giám sát sổ cái thẻ kho, đối soát chênh lệch và khai thác các báo cáo tài chính.\n"
        "Cơ chế này giúp bảo mật tối đa, ngăn ngừa rủi ro gian lận và thông đồng số liệu."
    )

# ==============================================================================
# SLIDE 5: QUY TRÌNH NHẬP KHO
# ==============================================================================
def build_slide_5(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 3 & 5: Nghiệp Vụ Cốt Lõi",
               "Quy Trình Nghiệp Vụ Nhập Kho & Giao Dịch ACID",
               "Chu trình 5 bước bảo đảm tính toàn vẹn tuyệt đối giữa Chứng từ, Tồn kho và Thẻ kho")
    add_footer(slide, 5)
    
    steps = [
        ("BƯỚC 1: KHỞI TẠO", "Client gửi POST /import-notes", "Thủ kho chọn nhà cung cấp, chọn sản phẩm, nhập số lượng & đơn giá thực tế. Gửi kèm JWT Bearer."),
        ("BƯỚC 2: XÁC THỰC", "API Gateway & RBAC", "deps.py kiểm tra Bearer Token, kiểm tra quyền Thủ kho/Admin. Nếu hợp lệ, chuyển giao cho inventory_service."),
        ("BƯỚC 3: MỞ TRANSACTION", "Mã phiếu PN-YYYYMMDD-XXXX", "Mở Database Transaction nguyên tử. Tự sinh mã phiếu chuẩn hóa duy nhất chống trùng lặp."),
        ("BƯỚC 4: TĂNG TỒN & SỔ CÁI", "Cập nhật Current Stock & Thẻ kho", "Ghi ImportNote & Details (lưu giá vốn đợt nhập). Tăng current_stock và tạo bản ghi StockLedger(+qty)."),
        ("BƯỚC 5: COMMIT DỮ LIỆU", "Cam kết giao dịch thành công", "COMMIT Transaction. Trả về HTTP 201 Created. Nếu bất kỳ bước nào lỗi -> Tự động Rollback 100%.")
    ]
    
    col_w = Inches(2.23)
    col_gap = Inches(0.14)
    top_pos = Inches(1.9)
    col_h = Inches(4.8)
    
    for i, (s_tag, s_title, s_desc) in enumerate(steps):
        left_pos = Inches(0.8) + i * (col_w + col_gap)
        c = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.18)
        tf.margin_top = Inches(0.2)
        
        # Step tag badge
        p = tf.paragraphs[0]
        p.text = s_tag
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = WOOD_PRIMARY
        
        # Step Title
        p = tf.add_paragraph()
        p.text = s_title
        p.font.name = FONT_HEADING
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        # Divider inside card
        p_div = tf.add_paragraph()
        p_div.text = "——————————"
        p_div.font.size = Pt(8)
        p_div.font.color.rgb = BORDER_LIGHT
        
        # Description
        p = tf.add_paragraph()
        p.text = s_desc
        p.font.name = FONT_BODY
        p.font.size = Pt(9.5)
        p.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Quy trình nhập kho diễn ra theo chu trình 5 bước nghiêm ngặt:\n"
        "- Mã phiếu nhập được sinh tự động theo quy tắc PN-NămThángNgày-SốThứTự (ví dụ PN-20260925-0001).\n"
        "- Giá vốn của từng đợt nhập được lưu chi tiết trong bảng import_note_details để phục vụ tính giá vốn bình quân và đối soát kế toán.\n"
        "- Mọi biến động đều được bao bọc trong Database Transaction. Nếu kết nối CSDL bị đứt giữa chừng, toàn bộ thay đổi sẽ được Rollback, không có tình trạng phiếu tạo rồi mà tồn kho chưa tăng."
    )

# ==============================================================================
# SLIDE 6: CỖ MÁY TRẠNG THÁI XUẤT KHO 3 BƯỚC
# ==============================================================================
def build_slide_6(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 3 & 5: Đột Phá Nghiệp Vụ",
               "Cỗ Máy Trạng Thái Xuất Kho 3 Bước (3-Stage State Machine)",
               "Phân biệt rạch ròi giữa việc xác nhận đơn và xuất kho vật lý — Xóa bỏ giam giữ hàng ảo")
    add_footer(slide, 6)
    
    stages = [
        ("TRẠNG THÁI 1: TIẾP NHẬN", "CONFIRMED (Đã Xác Nhận)", BLUE_PRIMARY, BLUE_LIGHT, [
            ("Thời điểm: ", "Tạo phiếu khi có yêu cầu xuất từ phòng kinh doanh."),
            ("Trạng thái kho: ", "Kiểm tra hàng có sẵn nhưng CHƯA trừ tồn kho thực tế, không giam hàng ảo."),
            ("Cơ chế Hủy: ", "Nếu sai sót, bấm 'Hủy & Xóa phiếu' -> Hệ thống xóa sạch, không để lại bản ghi rác.")
        ]),
        ("TRẠNG THÁI 2: XUẤT KHO", "SHIPPING (Đang Giao)", WOOD_PRIMARY, WOOD_LIGHT, [
            ("Thời điểm: ", "Hàng rời cửa kho vật lý, thủ kho bấm 'Bắt đầu giao hàng'."),
            ("Trạng thái kho: ", "Thực thi Atomic Stock Check, chính thức trừ current_stock và ghi Thẻ kho."),
            ("Cơ chế Hoàn kho: ", "Giao thất bại/khách trả về -> Bấm 'Hủy đơn & Hoàn kho' -> Chuyển CANCELLED & hoàn trả 100% tồn kho tự động!")
        ]),
        ("TRẠNG THÁI 3: KẾT THÚC", "COMPLETED (Hoàn Thành)", SUCCESS_GREEN, TEAL_LIGHT, [
            ("Thời điểm: ", "Khách hàng đã ký biên bản bàn giao thành công."),
            ("Trạng thái kho: ", "Phiếu chuyển sang Hoàn thành và bị KHÓA VĨNH VIỄN (Immutable)."),
            ("Bảo đảm: ", "Không bất kỳ ai (kể cả Admin) được sửa/xóa dữ liệu sau khi đã Completed.")
        ])
    ]
    
    card_w = Inches(3.7)
    card_h = Inches(4.8)
    top_pos = Inches(1.9)
    
    for i, (tag, title, color_p, color_bg, details) in enumerate(stages):
        left_pos = Inches(0.8) + i * Inches(4.0)
        c = add_card(slide, left_pos, top_pos, card_w, card_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.25)
        
        # Top banner tag
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = color_p
        
        # State Name
        p = tf.add_paragraph()
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        # Divider
        p_div = tf.add_paragraph()
        p_div.text = "————————————————————"
        p_div.font.size = Pt(8)
        p_div.font.color.rgb = BORDER_LIGHT
        
        for d_lbl, d_txt in details:
            p_l = tf.add_paragraph()
            p_l.text = "• " + d_lbl
            p_l.font.name = FONT_BODY
            p_l.font.size = Pt(10)
            p_l.font.bold = True
            p_l.font.color.rgb = TEXT_DARK
            
            p_t = tf.add_paragraph()
            p_t.text = "  " + d_txt
            p_t.font.name = FONT_BODY
            p_t.font.size = Pt(9.5)
            p_t.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Đây là điểm sáng thiết kế nghiệp vụ của đề tài:\n"
        "- Thay vì chỉ có 1 bước xuất kho đơn điệu như các hệ thống cũ, chúng em xây dựng Cỗ máy trạng thái 3 bước.\n"
        "- Ở bước CONFIRMED: Hàng chưa trừ, tránh tình trạng giam hàng ảo làm các đơn hàng khác không xuất được.\n"
        "- Ở bước SHIPPING: Lúc này hàng mới rời khỏi kệ kho và chuyển lên xe giao hàng, tồn kho được trừ và ghi Thẻ kho.\n"
        "- Đặc biệt, nếu giao hàng thất bại, tính năng 'Hủy đơn & Hoàn kho' tự động cộng trả lại đúng số lượng đó vào kho và ghi nhận lịch sử hoàn kho rõ ràng."
    )

# ==============================================================================
# SLIDE 7: CHỐNG TỒN ÂM & CHỐT CHẶN KÉP
# ==============================================================================
def build_slide_7(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 2, 6 & 9: Toàn Vẹn Dữ Liệu",
               "Cơ Chế Chống Tồn Kho Âm: Chốt Chặn Kép (Two-Tier Defense)",
               "Bảo đảm tính toàn vẹn tuyệt đối ở cả 2 tầng: Service Logic và Database Constraints")
    add_footer(slide, 7)
    
    col_w = Inches(5.7)
    col_h = Inches(4.8)
    top_pos = Inches(1.9)
    
    # Left Card: Service Layer
    c_left = add_card(slide, Inches(0.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf_l = c_left.text_frame
    tf_l.margin_left = tf_l.margin_right = Inches(0.25)
    tf_l.margin_top = Inches(0.22)
    
    p = tf_l.paragraphs[0]
    p.text = "CHỐT CHẶN 1: ATOMIC CHECK TẦNG SERVICE"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p = tf_l.add_paragraph()
    p.text = "Thuật toán kiểm soát tồn kho nguyên tử"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    p_code = tf_l.add_paragraph()
    p_code.text = "BẮT ĐẦU TRANSACTION:\n" \
                  "  Với từng item trong phiếu xuất:\n" \
                  "    product = SELECT * FROM products\n" \
                  "              WHERE id = item.product_id\n" \
                  "    NẾU product.current_stock < item.quantity:\n" \
                  "        ROLLBACK TRANSACTION\n" \
                  "        NÉM LỖI 400 Bad Request:\n" \
                  "        'Không đủ tồn kho: Cần X, Có Y'\n" \
                  "    product.current_stock -= item.quantity\n" \
                  "    GHI StockLedger(type='EXPORT', -quantity)\n" \
                  "LƯU ExportNote (status = 'SHIPPING')\n" \
                  "COMMIT TRANSACTION"
    p_code.font.name = "Consolas"
    p_code.font.size = Pt(9)
    p_code.font.color.rgb = RGBColor(30, 41, 59)
    
    p_desc = tf_l.add_paragraph()
    p_desc.text = "• Ý nghĩa: Chặn đứng ngay từ tầng logic nghiệp vụ, trả về thông báo lỗi rõ ràng kèm số tồn thực tế cho thủ kho xử lý."
    p_desc.font.name = FONT_BODY
    p_desc.font.size = Pt(9.5)
    p_desc.font.color.rgb = TEXT_MUTED

    # Right Card: Database Constraint
    c_right = add_card(slide, Inches(6.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf_r = c_right.text_frame
    tf_r.margin_left = tf_r.margin_right = Inches(0.25)
    tf_r.margin_top = Inches(0.22)
    
    p = tf_r.paragraphs[0]
    p.text = "CHỐT CHẶN 2: CHECKCONSTRAINT TẦNG DATABASE"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = DANGER_RED
    
    p = tf_r.add_paragraph()
    p.text = "Ràng buộc toàn vẹn ở tầng đĩa vật lý (Hard Lock)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    p_db = tf_r.add_paragraph()
    p_db.text = "Cài đặt Schema SQLAlchemy:\n\n" \
                "class Product(Base):\n" \
                "    __tablename__ = 'products'\n" \
                "    __table_args__ = (\n" \
                "        CheckConstraint(\n" \
                "            'current_stock >= 0',\n" \
                "            name='chk_product_current_stock_non_negative'\n" \
                "        ),\n" \
                "    )\n" \
                "    id = Column(Integer, primary_key=True)\n" \
                "    current_stock = Column(Integer, nullable=False)"
    p_db.font.name = "Consolas"
    p_db.font.size = Pt(9)
    p_db.font.color.rgb = RGBColor(30, 41, 59)
    
    p_rdesc = tf_r.add_paragraph()
    p_rdesc.text = "• Vai trò 'Lưới bảo vệ cuối cùng': Kể cả khi có lỗi lập trình (Bug) hoặc tranh chấp đa luồng (Race Condition), CSDL từ chối ghi và tự động Rollback phiên làm việc ngay lập tức!"
    p_rdesc.font.name = FONT_BODY
    p_rdesc.font.size = Pt(9.5)
    p_rdesc.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Để giải quyết triệt để lỗi tồn kho âm, chúng em triển khai chốt chặn kép Two-Tier Defense:\n"
        "- Ở tầng Service, thuật toán Atomic Check kiểm tra số lượng và ném lỗi 400 thân thiện nếu thiếu hàng.\n"
        "- Ở tầng Database, chúng em khai báo CheckConstraint 'current_stock >= 0' trực tiếp trong DDL của bảng products. "
        "Ngay cả khi hacker cố tình gọi API vượt mặt hoặc code xảy ra race condition, SQLite hay PostgreSQL đều sẽ ném IntegrityError và từ chối ghi đĩa.\n"
        "Nhờ đó, hệ thống cam kết 100% không bao giờ xảy ra lỗi tồn kho âm."
    )

# ==============================================================================
# SLIDE 8: SỔ CÁI THẺ KHO & KIỂM KÊ BÙ TRỪ
# ==============================================================================
def build_slide_8(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 3 & 4: Kiểm Toán & Đối Soát",
               "Sổ Cái Thẻ Kho Bất Biến & Tính Năng Kiểm Kê Bù Trừ",
               "Lưu vết kiểm toán từng giây (Audit Trail) và quy trình cân đối số liệu kho thực tế")
    add_footer(slide, 8)
    
    col_w = Inches(5.7)
    col_h = Inches(4.8)
    top_pos = Inches(1.9)
    
    # Left: Sổ cái thẻ kho
    c1 = add_card(slide, Inches(0.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf1 = c1.text_frame
    tf1.margin_left = tf1.margin_right = Inches(0.25)
    tf1.margin_top = Inches(0.22)
    
    p = tf1.paragraphs[0]
    p.text = "1. SỔ CÁI THẺ KHO (STOCK LEDGER)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p = tf1.add_paragraph()
    p.text = "Nhật ký biến động bất biến (Append-Only Audit Trail)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items1 = [
        ("Bất biến tuyệt đối: ", "Chỉ cho phép INSERT thêm bản ghi mới. Tuyệt đối cấm UPDATE và DELETE trên bảng thẻ kho."),
        ("Dữ liệu lưu vết từng giây: ", "Mã chứng từ (PN, XK, KK), Mã mặt hàng, Loại nghiệp vụ (IMPORT, EXPORT, ADJUST), Biến động (+/-), Số tồn sau giao dịch, User ID và Timestamp."),
        ("Giá trị pháp lý & kiểm toán: ", "Cung cấp bằng chứng toàn vẹn cho Kế toán và Ban Giám đốc khi đối soát số liệu hoặc truy vết thất thoát hàng hóa.")
    ]
    for lbl, desc in items1:
        p_t = tf1.add_paragraph()
        p_t.text = "• " + lbl
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_d = tf1.add_paragraph()
        p_d.text = "  " + desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_MUTED

    # Right: Kiểm kê bù trừ
    c2 = add_card(slide, Inches(6.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf2 = c2.text_frame
    tf2.margin_left = tf2.margin_right = Inches(0.25)
    tf2.margin_top = Inches(0.22)
    
    p = tf2.paragraphs[0]
    p.text = "2. TÍNH NĂNG KIỂM KÊ KHO (STOCK ADJUSTMENT)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = TEAL_PRIMARY
    
    p = tf2.add_paragraph()
    p.text = "Cơ chế tự động cân đối sai lệch thực tế và sổ sách"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items2 = [
        ("Bối cảnh nghiệp vụ: ", "Trong thực tế, hàng hóa có thể bị hư hại, rơi vỡ, thất thoát hoặc nhầm lẫn số lượng khi nhập xuất."),
        ("Quy trình cân đối 3 bước: ", "Thủ kho kiểm đếm thực tế -> Nhập số lượng thực tế -> Hệ thống tự động tính độ lệch: Delta = Thực tế - Sổ sách."),
        ("Tự động sinh chứng từ: ", "Sinh mã phiếu kiểm kê chuẩn: KK-YYYYMMDD-XXXX."),
        ("Đồng bộ số tồn: ", "Tạo giao dịch nghiệp vụ ADJUST trên Thẻ kho để đưa số tồn về chuẩn xác, lưu kèm lý do điều chỉnh.")
    ]
    for lbl, desc in items2:
        p_t = tf2.add_paragraph()
        p_t.text = "• " + lbl
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_d = tf2.add_paragraph()
        p_d.text = "  " + desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Ở phân hệ kiểm toán kho:\n"
        "1. Bảng stock_ledger được thiết kế theo nguyên lý Append-Only. Mỗi lần xuất nhập đều ghi rõ tồn trước và tồn sau giao dịch.\n"
        "2. Tính năng kiểm kê bù trừ là một tính năng cực kỳ thực tế. Khi kho thực tế bị lệch so với phần mềm, thủ kho chỉ cần nhập số đếm được, "
        "hệ thống tự tính phần chênh lệch và tạo phiếu KK để cân bằng số liệu mà không làm gián đoạn sổ sách."
    )

# ==============================================================================
# SLIDE 9: PHÂN HỆ TRÍ TUỆ NHÂN TẠO (AI COPILOT)
# ==============================================================================
def build_slide_9(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 3 & 9: Ứng Dụng AI Trong Kỹ Nghệ Phần Mềm",
               "Phân Hệ AI Copilot Tích Hợp Google Gemini",
               "3 Năng lực AI chuyên sâu hỗ trợ ra quyết định kho thông minh (Theo yêu cầu Đề tài 07)")
    add_footer(slide, 9)
    
    col_w = Inches(3.7)
    col_h = Inches(3.6)
    top_pos = Inches(1.9)
    
    features = [
        ("NĂNG LỰC 1", "Báo Cáo Nhập - Xuất - Tồn", BLUE_PRIMARY, [
            "Tự động tổng hợp số liệu biến động kho theo chu kỳ tháng.",
            "Phân tích cơ cấu sản phẩm bán chạy nhất (Best-sellers) và sản phẩm tồn ứ.",
            "Sinh báo cáo định dạng Markdown trực quan kèm nhận định quản trị kinh doanh sắc bén."
        ]),
        ("NĂNG LỰC 2", "Dự Báo & Đề Xuất Nhập Hàng", WOOD_PRIMARY, [
            "Ứng dụng công thức ROP (Reorder Point): ROP = (ADC * Lead_Time) + Safety_Stock.",
            "Tính tốc độ tiêu thụ trung bình ngày (ADC) trong 30 ngày gần nhất.",
            "Tự động đề xuất danh sách mặt hàng cần đặt và số lượng kinh tế tối ưu (EOQ)."
        ]),
        ("NĂNG LỰC 3", "Cảnh Báo Biến Động Bất Thường", DANGER_RED, [
            "Phát hiện đơn hàng xuất tăng đột biến (> 200% so với mức trung bình).",
            "Cảnh báo hàng hóa ứ đọng kéo dài (> 30 ngày không phát sinh xuất).",
            "Giúp chủ kho phát hiện sớm rủi ro gian lận hoặc biến động nhu cầu thị trường."
        ])
    ]
    
    for i, (tag, title, color_p, bullets) in enumerate(features):
        left_pos = Inches(0.8) + i * Inches(4.0)
        c = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.2)
        tf.margin_top = Inches(0.2)
        
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = color_p
        
        p = tf.add_paragraph()
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        p_div = tf.add_paragraph()
        p_div.text = "——————————————"
        p_div.font.size = Pt(8)
        p_div.font.color.rgb = BORDER_LIGHT
        
        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = "• " + b
            p_b.font.name = FONT_BODY
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = TEXT_MUTED

    # Bottom Prompt Engineering Card
    c_bot = add_card(slide, Inches(0.8), Inches(5.65), Inches(11.733), Inches(1.15), TEAL_LIGHT, TEAL_PRIMARY)
    tf_b = c_bot.text_frame
    tf_b.margin_left = tf_b.margin_right = Inches(0.25)
    tf_b.margin_top = Inches(0.12)
    
    p = tf_b.paragraphs[0]
    p.text = "🎯 KỸ THUẬT PROMPT ENGINEERING & BẢO VỆ DỮ LIỆU NHẠY CẢM"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = TEAL_PRIMARY
    
    p2 = tf_b.add_paragraph()
    p2.text = "• Thiết lập vai trò nghiêm ngặt: System Prompt định danh 'Expert Warehouse AI Assistant', quy định cấm bịa đặt số liệu (Anti-hallucination).\n" \
              "• Làm sạch dữ liệu (Data Sanitization): Ẩn toàn bộ thông tin giá vốn, giá nhập thực tế khỏi prompt gửi lên Google Gemini, bảo mật tuyệt đối bí mật kinh doanh."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Về phân hệ Trí tuệ Nhân tạo, đây là trọng tâm yêu cầu của Đề tài 07:\n"
        "- Hệ thống tích hợp Google Gemini để thực hiện 3 năng lực: Báo cáo Nhập-Xuất-Tồn tự động, Đề xuất nhập hàng theo công thức ROP/EOQ, và Cảnh báo biến động bất thường.\n"
        "- Chúng em áp dụng kỹ thuật Prompt Engineering chặt chẽ: Định danh vai trò chuyên gia, ép buộc cấu trúc JSON hoặc Markdown chuẩn, và đặc biệt là cơ chế Data Sanitization bóc tách giá nhập nhạy cảm trước khi gửi dữ liệu sang bên thứ ba."
    )

# ==============================================================================
# SLIDE 10: DỰ PHÒNG HEURISTIC 24/7
# ==============================================================================
def build_slide_10(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 6 & 8: Độ Tin Cậy & Sẵn Sàng Cao",
               "Cơ Chế Dự Phòng Heuristic Fallback Engine",
               "Bảo đảm hoạt động quản trị kho bãi 24/7 không gián đoạn ngay cả khi mất mạng hoặc hết quota API")
    add_footer(slide, 10)
    
    col_w = Inches(5.7)
    col_h = Inches(3.6)
    top_pos = Inches(1.9)
    
    # Left: Cloud Mode
    c1 = add_card(slide, Inches(0.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf1 = c1.text_frame
    tf1.margin_left = tf1.margin_right = Inches(0.25)
    tf1.margin_top = Inches(0.22)
    
    p = tf1.paragraphs[0]
    p.text = "KÊNH CHÍNH: GOOGLE GEMINI CLOUD (ONLINE)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = BLUE_PRIMARY
    
    p = tf1.add_paragraph()
    p.text = "Phân tích ngôn ngữ tự nhiên thông minh & toàn diện"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items1 = [
        "Hoạt động khi có kết nối Internet ổn định và API Quota khả dụng.",
        "Sinh phân tích chuyên sâu, tổng kết xu hướng thị trường đa chiều.",
        "Bộ nhớ đệm (AI Cache): Lưu kết quả phân tích theo ngày để tiết kiệm chi phí gọi API và tăng tốc độ phản hồi < 50ms cho người dùng."
    ]
    for it in items1:
        p_b = tf1.add_paragraph()
        p_b.text = "• " + it
        p_b.font.name = FONT_BODY
        p_b.font.size = Pt(9.5)
        p_b.font.color.rgb = TEXT_MUTED

    # Right: Fallback Mode
    c2 = add_card(slide, Inches(6.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf2 = c2.text_frame
    tf2.margin_left = tf2.margin_right = Inches(0.25)
    tf2.margin_top = Inches(0.22)
    
    p = tf2.paragraphs[0]
    p.text = "KÊNH DỰ PHÒNG: HEURISTIC ENGINE (LOCAL OFFLINE)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p = tf2.add_paragraph()
    p.text = "Động cơ thuật toán cục bộ chạy độc lập 100%"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items2 = [
        "Tự động kích hoạt khi: Mất mạng Internet, Timeout (>10s), hoặc lỗi HTTP 429 Quota Exceeded.",
        "Thuật toán toán học cục bộ: Tự tính toán số liệu Nhập-Xuất-Tồn, tự quét ngưỡng min_stock và tự phát hiện bất thường trực tiếp trên Database.",
        "Minh bạch người dùng: Trả về kết quả ngay lập tức kèm nhãn cảnh báo [Chế độ Heuristic Offline]."
    ]
    for it in items2:
        p_b = tf2.add_paragraph()
        p_b.text = "• " + it
        p_b.font.name = FONT_BODY
        p_b.font.size = Pt(9.5)
        p_b.font.color.rgb = TEXT_MUTED

    # Bottom Callout
    c_bot = add_card(slide, Inches(0.8), Inches(5.65), Inches(11.733), Inches(1.15), WOOD_LIGHT, WOOD_PRIMARY)
    tf_b = c_bot.text_frame
    tf_b.margin_left = tf_b.margin_right = Inches(0.25)
    tf_b.margin_top = Inches(0.12)
    
    p = tf_b.paragraphs[0]
    p.text = "🛡️ GIÁ TRỊ CỐT LÕI: TÍNH LIÊN TỤC TRONG KINH DOANH (BUSINESS CONTINUITY)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p2 = tf_b.add_paragraph()
    p2.text = "• Trong kho vận thực tế, việc đình trệ dù chỉ 5 phút cũng gây thiệt hại lớn cho chuỗi cung ứng.\n" \
              "• Cơ chế Heuristic Fallback Engine bảo đảm hệ thống WMS AI đạt độ sẵn sàng cao (High Availability 24/7), hoàn toàn không bị động trước các sự cố mạng bên ngoài."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Một trong những ưu điểm kỹ thuật vượt trội của hệ thống là cơ chế Heuristic Fallback:\n"
        "- Nếu hệ thống phụ thuộc hoàn toàn vào Cloud AI, khi mất mạng cáp quang hoặc hết hạn mức API, ứng dụng sẽ bị treo hoặc báo lỗi.\n"
        "- Để giải quyết triệt để vấn đề này, chúng em đã tự viết một động cơ Heuristic Fallback Engine chạy cục bộ bằng Python.\n"
        "- Khi API Gemini lỗi, hệ thống tự động bắt ngoại lệ và chuyển sang chế độ Heuristic trong vòng vài phần trăm giây. Thủ kho vẫn nhận được đầy đủ số liệu báo cáo và danh sách cần nhập hàng."
    )

# ==============================================================================
# SLIDE 11: THIẾT KẾ CSDL & ERD 3NF
# ==============================================================================
def build_slide_11(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 4: Yêu Cầu Thông Tin Dữ Liệu",
               "Mô Hình Cơ Sở Dữ Liệu Chuẩn Hóa Dạng 3 (3NF ERD)",
               "9 Bảng thực thể phân cấp chặt chẽ, tối ưu hóa truy vấn và toàn vẹn tham chiếu")
    add_footer(slide, 11)
    
    # 3x3 Grid of Entities
    entities = [
        ("users", "Tài khoản & Phân quyền", "id, username, password_hash, role, full_name"),
        ("categories", "Nhóm phân loại hàng hóa", "id, name, description, created_at"),
        ("products", "Danh mục hàng hóa cốt lõi", "id, name, category_id, current_stock, min_stock, unit"),
        ("suppliers", "Nhà cung cấp vật tư", "id, name, contact_person, phone, email, address"),
        ("import_notes", "Phiếu nhập kho tổng quan", "id, note_code (PN-...), supplier_id, user_id, date"),
        ("import_note_details", "Chi tiết dòng hàng nhập", "id, note_id, product_id, quantity, unit_price"),
        ("export_notes", "Phiếu xuất kho 3 bước", "id, note_code (XK-...), status, user_id, created_at"),
        ("export_note_details", "Chi tiết dòng hàng xuất", "id, note_id, product_id, quantity"),
        ("stock_ledger", "Sổ cái thẻ kho kiểm toán", "id, document_code, type, product_id, change, balance")
    ]
    
    col_w = Inches(3.7)
    col_h = Inches(1.5)
    
    for idx, (t_name, t_desc, t_fields) in enumerate(entities):
        r = idx // 3
        c = idx % 3
        left_pos = Inches(0.8) + c * Inches(4.0)
        top_pos = Inches(1.9) + r * Inches(1.6)
        
        card = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = card.text_frame
        tf.margin_left = tf.margin_right = Inches(0.2)
        tf.margin_top = Inches(0.15)
        
        p = tf.paragraphs[0]
        p.text = f"TABLE: {t_name}"
        p.font.name = "Consolas"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = WOOD_PRIMARY if "stock" in t_name or "product" in t_name else BLUE_PRIMARY
        
        p = tf.add_paragraph()
        p.text = t_desc
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        p = tf.add_paragraph()
        p.text = f"Trường: {t_fields}"
        p.font.name = FONT_BODY
        p.font.size = Pt(8.5)
        p.font.color.rgb = TEXT_MUTED

    # Bottom note
    foot_note = slide.shapes.add_textbox(Inches(0.8), Inches(6.5), Inches(11.733), Inches(0.4))
    tf_fn = foot_note.text_frame
    p_fn = tf_fn.paragraphs[0]
    p_fn.text = "🔑 RÀNG BUỘC TOÀN VẸN: PRAGMA foreign_keys = ON; Quan hệ 1-N rõ ràng; Ràng buộc CheckConstraint('current_stock >= 0'); Index trên khóa ngoại và ngày giao dịch."
    p_fn.font.name = FONT_BODY
    p_fn.font.size = Pt(9.5)
    p_fn.font.bold = True
    p_fn.font.color.rgb = TEAL_PRIMARY

    add_speaker_notes(slide,
        "Về thiết kế cơ sở dữ liệu:\n"
        "- Hệ thống gồm 9 bảng được chuẩn hóa đạt chuẩn 3NF, loại bỏ hoàn toàn dư thừa dữ liệu.\n"
        "- Bảng products liên kết chặt chẽ với categories; import_notes và export_notes đều có bảng chi tiết details đi kèm.\n"
        "- Bảng stock_ledger là trung tâm lưu vết mọi biến động số lượng hàng hóa.\n"
        "- Tất cả các khóa ngoại đều được cấu hình kiểm tra toàn vẹn tham chiếu nghiêm ngặt."
    )

# ==============================================================================
# SLIDE 12: ĐỘT PHÁ GIAO DIỆN COMPONENT PRODUCTSELECT
# ==============================================================================
def build_slide_12(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 7: Thiết Kế Giao Diện & Công Thái Học",
               "Đột Phá Component ProductSelect & Trải Nghiệm Công Thái Học",
               "Tối ưu hóa thao tác người vận hành, giảm 70% thời gian nhập liệu và loại bỏ mỏi mắt")
    add_footer(slide, 12)
    
    col_w = Inches(5.7)
    col_h = Inches(4.8)
    top_pos = Inches(1.9)
    
    # Left Card: Ergonomic UX & Wood Theme
    c1 = add_card(slide, Inches(0.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf1 = c1.text_frame
    tf1.margin_left = tf1.margin_right = Inches(0.25)
    tf1.margin_top = Inches(0.22)
    
    p = tf1.paragraphs[0]
    p.text = "1. TRIẾT LÝ CÔNG THÁI HỌC (WARM WOOD & SLATE)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WOOD_PRIMARY
    
    p = tf1.add_paragraph()
    p.text = "Thiết kế giao diện hướng đến người vận hành thực tế"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items1 = [
        ("Bảng màu Warm Wood & Slate: ", "Lấy cảm hứng từ chất liệu gỗ tự nhiên và kho vận, tạo cảm giác dễ chịu, đạt tiêu chuẩn tương phản WCAG 2.1 AA giúp thủ kho làm việc liên tục 8 tiếng không bị mỏi mắt."),
        ("Ẩn hoàn toàn mã SKU kỹ thuật: ", "Khảo sát thực tế cho thấy thủ kho nhận biết hàng qua tên gọi. Giao diện chỉ hiển thị: [Tên sản phẩm] (Tồn: [SL]), loại bỏ mã SKU rườm rà gây rối mắt."),
        ("Bộ lọc phân cấp song song: ", "Bố trí ô chọn 'Nhóm hàng' ngay cạnh ô tìm kiếm. Cho phép lọc nhanh theo từng nhóm hoặc tra cứu toàn bộ kho hàng linh hoạt.")
    ]
    for lbl, desc in items1:
        p_t = tf1.add_paragraph()
        p_t.text = "• " + lbl
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_d = tf1.add_paragraph()
        p_d.text = "  " + desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_MUTED

    # Right Card: Component ProductSelect.jsx
    c2 = add_card(slide, Inches(6.8), top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
    tf2 = c2.text_frame
    tf2.margin_left = tf2.margin_right = Inches(0.25)
    tf2.margin_top = Inches(0.22)
    
    p = tf2.paragraphs[0]
    p.text = "2. ĐỘT PHÁ COMPONENT PRODUCTSELECT.JSX"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = TEAL_PRIMARY
    
    p = tf2.add_paragraph()
    p.text = "Thuật toán tìm kiếm thông minh & Điều hướng bàn phím"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    
    items2 = [
        ("Gõ tắt chữ cái đầu (Initials Match): ", "Thủ kho chỉ cần gõ 'blv' là tìm thấy ngay 'Bàn Làm Việc'; gõ 'gt' ra 'Gỗ Thông'; gõ 'tqa' ra 'Tủ Quần Áo'."),
        ("Khử dấu tiếng Việt (Unicode NFD): ", "Gõ không dấu hay có dấu đều cho kết quả chuẩn xác 100% nhờ thuật toán chuẩn hóa ký tự tổ hợp."),
        ("Bôi đen tự động khi click (Auto-select): ", "Click vào ô là text cũ tự động bôi đen, người dùng có thể gõ đè ngay lập tức mà không cần bấm phím xóa (Backspace)."),
        ("Điều hướng bàn phím 100%: ", "Hỗ trợ phím Mũi tên lên/xuống để duyệt danh sách, Enter để chọn, Esc để đóng menu — không cần rời tay khỏi bàn phím.")
    ]
    for lbl, desc in items2:
        p_t = tf2.add_paragraph()
        p_t.text = "• " + lbl
        p_t.font.name = FONT_BODY
        p_t.font.size = Pt(10)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_d = tf2.add_paragraph()
        p_d.text = "  " + desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Về trải nghiệm người dùng, nhóm đã nghiên cứu rất kỹ thói quen của thủ kho:\n"
        "- Thay vì dùng thẻ select mặc định của HTML bắt người dùng cuộn chuột tìm kiếm hàng trăm sản phẩm rất mỏi mắt, "
        "chúng em xây dựng component ProductSelect.jsx.\n"
        "- Component này tích hợp thuật toán trích xuất chữ cái đầu Initials kết hợp khử dấu tiếng Việt. Thủ kho chỉ cần gõ 'blv' là hệ thống tự khớp 'Bàn Làm Việc'.\n"
        "- Tính năng tự động bôi đen khi focus và hỗ trợ phím mũi tên giúp người vận hành có thể lập phiếu nhập xuất liên tục chỉ bằng bàn phím, tiết kiệm đến 70% thời gian thao tác."
    )

# ==============================================================================
# SLIDE 13: YÊU CẦU PHI CHỨC NĂNG & BẢO MẬT
# ==============================================================================
def build_slide_13(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 6: Yêu Cầu Phi Chức Năng",
               "Tiêu Chuẩn Hiệu Năng, Độ Tin Cậy & An Toàn Bảo Mật",
               "Hệ thống đạt các chỉ số kỹ thuật khắt khe về tốc độ, toàn vẹn dữ liệu và an toàn thông tin")
    add_footer(slide, 13)
    
    col_w = Inches(5.7)
    col_h = Inches(2.3)
    
    metrics = [
        ("HIỆU NĂNG VẬN HÀNH (PERFORMANCE)", BLUE_PRIMARY, [
            "Thời gian phản hồi API (Latency): < 100ms cho các truy vấn kho bãi.",
            "Tối ưu Bundle Frontend: Kích thước tải nén Gzip chỉ ~95KB nhờ code-splitting của Vite.",
            "Giao diện SPA phản hồi tức thì không tải lại trang (Zero reload)."
        ]),
        ("ĐỘ TIN CẬY & TOÀN VẸN (RELIABILITY)", SUCCESS_GREEN, [
            "Đạt chuẩn giao dịch ACID 100% trong mọi thao tác xuất nhập kho.",
            "Ràng buộc CheckConstraint chặn 100% nguy cơ tồn âm ở cấp độ đĩa cứng.",
            "Cơ chế Session Rollback tự động phục hồi trạng thái khi có ngoại lệ phát sinh."
        ]),
        ("AN TOÀN BẢO MẬT (SECURITY)", WOOD_PRIMARY, [
            "Mật khẩu người dùng được băm an toàn bằng thuật toán Bcrypt một chiều.",
            "Xác thực chuẩn JWT Bearer Token có thời hạn và chữ ký số bí mật.",
            "Kiểm soát truy cập phân tầng (RBAC) trên từng Endpoint tại tầng FastAPI dependencies."
        ]),
        ("BẢO VỆ DỮ LIỆU KINH DOANH (PRIVACY)", TEAL_PRIMARY, [
            "Bóc tách dữ liệu nhạy cảm (Data Sanitization) trước khi gửi prompt tới AI.",
            "Tuyệt đối không gửi giá vốn, giá nhập thực tế lên Cloud LLM của bên thứ ba.",
            "Ngăn chặn hoàn toàn rủi ro rò rỉ bí mật giá nhập và lợi nhuận kinh doanh."
        ])
    ]
    
    positions = [
        (Inches(0.8), Inches(1.9)),
        (Inches(6.8), Inches(1.9)),
        (Inches(0.8), Inches(4.5)),
        (Inches(6.8), Inches(4.5))
    ]
    
    for i, (title, color_p, bullets) in enumerate(metrics):
        left_pos, top_pos = positions[i]
        c = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.18)
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = color_p
        
        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = "• " + b
            p_b.font.name = FONT_BODY
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Về các chỉ số phi chức năng:\n"
        "- Về hiệu năng: Gói mã nguồn frontend chỉ 95KB sau khi nén Gzip, tải tức thì trong vòng nửa giây; thời gian phản hồi API dưới 100ms.\n"
        "- Về độ tin cậy: Tuân thủ tuyệt đối chuẩn ACID với chốt chặn CheckConstraint.\n"
        "- Về bảo mật: Sử dụng Bcrypt và JWT Token.\n"
        "- Đặc biệt về bảo mật AI: Hệ thống làm sạch dữ liệu trước khi gọi Gemini, đảm bảo thông tin giá vốn nhập hàng của doanh nghiệp không bao giờ bị truyền ra Internet."
    )

# ==============================================================================
# SLIDE 14: KIẾN TRÚC TRIỂN KHAI & CONTAINER HÓA
# ==============================================================================
def build_slide_14(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Chương 5: Chi Tiết Thiết Kế Hệ Thống",
               "Kiến Trúc Triển Khai & Container Hóa (Deployment)",
               "Mô hình Docker gọn nhẹ, hỗ trợ triển khai linh hoạt trên Cloud hoặc On-Premises nội bộ")
    add_footer(slide, 14)
    
    col_w = Inches(3.7)
    col_h = Inches(4.8)
    top_pos = Inches(1.9)
    
    nodes = [
        ("FRONTEND CONTAINER", "Nginx / Static Web Server", BLUE_PRIMARY, [
            ("Công nghệ đóng gói: ", "Multi-stage Dockerfile: Node.js build ra Static Assets, Nginx Alpine phân phối."),
            ("Tối ưu hóa: ", "Bật Nginx Gzip compression, cấu hình HTTP Caching cho tài nguyên tĩnh (JS/CSS/Fonts)."),
            ("Reverse Proxy: ", "Chuyển tiếp các request /api/ sang Backend container trong cùng mạng nội bộ Docker Network.")
        ]),
        ("BACKEND CONTAINER", "FastAPI on Uvicorn ASGI", WOOD_PRIMARY, [
            ("Môi trường thực thi: ", "Python 3.14 slim container hóa gọn nhẹ, bảo mật cao."),
            ("Máy chủ ứng dụng: ", "Uvicorn ASGI Server hỗ trợ xử lý hàng nghìn kết nối bất đồng bộ (Async I/O) đồng thời."),
            ("Quản trị cấu hình: ", "Tách biệt cấu hình qua biến môi trường .env (JWT Secret, Database URL, Gemini API Key).")
        ]),
        ("PERSISTENCE VOLUME", "SQLite / PostgreSQL Storage", TEAL_PRIMARY, [
            ("Lưu trữ bền vững: ", "Dữ liệu được lưu trữ trên Docker Named Volume, bảo đảm an toàn dữ liệu khi cập nhật container."),
            ("Khả năng mở rộng: ", "Hỗ trợ chuyển đổi nhanh chóng sang PostgreSQL Connection Pooling khi doanh nghiệp mở rộng quy mô lớn."),
            ("Cơ chế sao lưu: ", "Hỗ trợ backup dữ liệu tự động định kỳ, khôi phục thảm họa (Disaster Recovery) nhanh chóng.")
        ])
    ]
    
    for i, (tag, title, color_p, items) in enumerate(nodes):
        left_pos = Inches(0.8) + i * Inches(4.0)
        c = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.22)
        
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = color_p
        
        p = tf.add_paragraph()
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        p_div = tf.add_paragraph()
        p_div.text = "——————————————"
        p_div.font.size = Pt(8)
        p_div.font.color.rgb = BORDER_LIGHT
        
        for lbl, desc in items:
            p_l = tf.add_paragraph()
            p_l.text = "• " + lbl
            p_l.font.name = FONT_BODY
            p_l.font.size = Pt(10)
            p_l.font.bold = True
            p_l.font.color.rgb = TEXT_DARK
            
            p_t = tf.add_paragraph()
            p_t.text = "  " + desc
            p_t.font.name = FONT_BODY
            p_t.font.size = Pt(9.5)
            p_t.font.color.rgb = TEXT_MUTED

    add_speaker_notes(slide,
        "Về kiến trúc triển khai:\n"
        "- Toàn bộ hệ thống được container hóa bằng Docker với mô hình Multi-stage build gọn nhẹ.\n"
        "- Frontend được phân phối qua Nginx Alpine siêu nhẹ và làm Reverse Proxy.\n"
        "- Backend chạy FastAPI với ASGI Server Uvicorn trên nền Python 3.14.\n"
        "- Dữ liệu được bảo toàn trên Docker Persistent Volume. Mô hình này cho phép doanh nghiệp triển khai On-premises tại kho hoặc đưa lên các nền tảng điện toán đám mây như AWS, GCP hay máy chủ riêng một cách dễ dàng chỉ bằng lệnh docker-compose up."
    )

# ==============================================================================
# SLIDE 15: TỔNG KẾT & KẾT QUẢ NGHIỆM THU
# ==============================================================================
def build_slide_15(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_LIGHT)
    add_header(slide, "Tổng Kết & Đánh Giá Đề Tài 07",
               "Kết Quả Đạt Được & Giá Trị Thực Tiễn",
               "Đề tài đã hoàn thành xuất sắc 100% mục tiêu đặc tả và đáp ứng trọn vẹn tiêu chuẩn nghiệm thu")
    add_footer(slide, 15)
    
    col_w = Inches(5.7)
    col_h = Inches(2.3)
    
    outcomes = [
        ("TRIỆT TIÊU 100% LỖI TỒN KHO ÂM", SUCCESS_GREEN, [
            "Chốt chặn kép (Atomic Check + CheckConstraint) đã được kiểm chứng qua bộ test tự động.",
            "Cam kết tính toàn vẹn dữ liệu trong mọi trường hợp tải cao hoặc tranh chấp đồng thời.",
            "Số liệu tồn kho luôn khớp tuyệt đối giữa Sổ sách và Thực tế vật lý."
        ]),
        ("CỖ MÁY XUẤT KHO 3 BƯỚC CHUẨN MỰC", BLUE_PRIMARY, [
            "Xóa bỏ hoàn toàn tình trạng giam giữ hàng ảo trong kho bãi.",
            "Hỗ trợ quy trình 'Hủy đơn & Hoàn kho 100%' tự động và minh bạch.",
            "Phiếu xuất khóa bất biến khi hoàn thành (COMPLETED), bảo vệ lịch sử kế toán."
        ]),
        ("AI COPILOT 24/7 VỚI DỰ PHÒNG HEURISTIC", WOOD_PRIMARY, [
            "Tự động hóa báo cáo Nhập - Xuất - Tồn theo tháng và đề xuất nhập hàng ROP/EOQ.",
            "Bộ động cơ Heuristic Fallback nội tại bảo đảm hệ thống hoạt động ổn định cả khi mất mạng.",
            "Bảo vệ 100% bí mật giá vốn kinh doanh nhờ cơ chế Data Sanitization."
        ]),
        ("CÔNG THÁI HỌC & HIỆU QUẢ VẬN HÀNH VƯỢT TRỘI", TEAL_PRIMARY, [
            "Component ProductSelect tìm kiếm chữ cái đầu và khử dấu tiếng Việt tăng tốc độ nhập liệu gấp 3 lần.",
            "Giao diện Warm Wood & Slate chống mỏi mắt cho người vận hành.",
            "Hồ sơ kỹ thuật đầy đủ: SRS, Kiến trúc, ERD, API Specs và kịch bản Test Cases hoàn chỉnh."
        ])
    ]
    
    positions = [
        (Inches(0.8), Inches(1.9)),
        (Inches(6.8), Inches(1.9)),
        (Inches(0.8), Inches(4.5)),
        (Inches(6.8), Inches(4.5))
    ]
    
    for i, (title, color_p, bullets) in enumerate(outcomes):
        left_pos, top_pos = positions[i]
        c = add_card(slide, left_pos, top_pos, col_w, col_h, WHITE, BORDER_LIGHT)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.18)
        
        p = tf.paragraphs[0]
        p.text = "✅ " + title
        p.font.name = FONT_HEADING
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = color_p
        
        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = "• " + b
            p_b.font.name = FONT_BODY
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = TEXT_DARK

    add_speaker_notes(slide,
        "Tổng kết lại kết quả của Đề tài 07:\n"
        "- Nhóm chúng em đã hoàn thành 100% các yêu cầu kỹ thuật và nghiệp vụ được giao trong bản đặc tả kiến trúc.\n"
        "- Hệ thống đã triệt tiêu được lỗi tồn âm, giải quyết bài toán giam giữ hàng ảo qua cỗ máy 3 bước, "
        "tích hợp thành công AI Google Gemini với bộ dự phòng Heuristic 24/7 và mang lại trải nghiệm công thái học vượt trội cho thủ kho.\n"
        "- Toàn bộ các module đều đã vượt qua các kịch bản kiểm thử tích hợp và kiểm thử hộp đen với độ tin cậy tuyệt đối."
    )

# ==============================================================================
# SLIDE 16: Q&A & LỜI CẢM ƠN
# ==============================================================================
def build_slide_16(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, BG_DARK)
    
    # Decorative Accent Line
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(11.733), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = WOOD_ACCENT
    bar.line.fill.background()
    
    # Big Thank You Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.733), Inches(1.8))
    tf = t_box.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "XIN TRÂN TRỌNG CẢM ƠN!"
    p.font.name = FONT_HEADING
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    
    p2 = tf.add_paragraph()
    p2.text = "QUÝ THẦY CÔ VÀ HỘI ĐỒNG ĐÁNH GIÁ ĐÃ LẮNG NGHE"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(18)
    p2.font.bold = True
    p2.font.color.rgb = WOOD_LIGHT
    p2.alignment = PP_ALIGN.CENTER
    
    # QA Card Center
    card = add_card(slide, Inches(2.2), Inches(3.8), Inches(8.933), Inches(2.2), BG_DARK_CARD, BORDER_DARK)
    tf_c = card.text_frame
    tf_c.margin_left = tf_c.margin_right = Inches(0.4)
    tf_c.margin_top = Inches(0.3)
    
    p_c1 = tf_c.paragraphs[0]
    p_c1.text = "PHIÊN HỎI ĐÁP & PHẢN BIỆN (Q&A SESSION)"
    p_c1.font.name = FONT_HEADING
    p_c1.font.size = Pt(14)
    p_c1.font.bold = True
    p_c1.font.color.rgb = TEAL_PRIMARY
    p_c1.alignment = PP_ALIGN.CENTER
    
    p_c2 = tf_c.add_paragraph()
    p_c2.text = "Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI)\n" \
                "Mã đề tài: Đề tài 07 — Phiên bản chuẩn hóa 2026\n\n" \
                "Kính mời Quý Thầy/Cô và Hội đồng đặt câu hỏi và đóng góp ý kiến cho nhóm!"
    p_c2.font.name = FONT_BODY
    p_c2.font.size = Pt(11)
    p_c2.font.color.rgb = RGBColor(226, 232, 240)
    p_c2.alignment = PP_ALIGN.CENTER

    add_speaker_notes(slide,
        "Bài thuyết trình báo cáo kiến trúc hệ thống của nhóm chúng em đến đây là kết thúc.\n"
        "Chúng em xin chân thành cảm ơn Quý Thầy Cô trong Hội đồng đánh giá đã dành thời gian lắng nghe và theo dõi.\n"
        "Sau đây, chúng em xin kính mời Quý Thầy Cô và các bạn đặt câu hỏi phản biện để nhóm có cơ hội làm rõ hơn các giải pháp kỹ thuật của đề tài. "
        "Chúng em xin trân trọng cảm ơn!"
    )

def main():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    print("Building Slide 1: Title Slide...")
    build_slide_1(prs)
    
    print("Building Slide 2: 3 Core Problems...")
    build_slide_2(prs)
    
    print("Building Slide 3: 3-Tier Clean Architecture...")
    build_slide_3(prs)
    
    print("Building Slide 4: RBAC Matrix...")
    build_slide_4(prs)
    
    print("Building Slide 5: Import Flow & ACID Transaction...")
    build_slide_5(prs)
    
    print("Building Slide 6: 3-Stage Export State Machine...")
    build_slide_6(prs)
    
    print("Building Slide 7: Negative Stock Prevention (Two-tier Defense)...")
    build_slide_7(prs)
    
    print("Building Slide 8: Stock Ledger & Stock Adjustment...")
    build_slide_8(prs)
    
    print("Building Slide 9: AI Copilot & Google Gemini...")
    build_slide_9(prs)
    
    print("Building Slide 10: Heuristic Fallback Engine 24/7...")
    build_slide_10(prs)
    
    print("Building Slide 11: Database Design & 3NF ERD...")
    build_slide_11(prs)
    
    print("Building Slide 12: Ergonomic UX & ProductSelect...")
    build_slide_12(prs)
    
    print("Building Slide 13: Non-functional & Security...")
    build_slide_13(prs)
    
    print("Building Slide 14: Deployment & Docker Containerization...")
    build_slide_14(prs)
    
    print("Building Slide 15: Project Summary & Value...")
    build_slide_15(prs)
    
    print("Building Slide 16: Closing & Q&A...")
    build_slide_16(prs)
    
    output_path = os.path.join(os.getcwd(), "Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx")
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    main()
