import os
import io
import textwrap
import qrcode
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# Ensure font registration once
_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    regular_candidates = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'tahoma.ttf'),
        'C:/Windows/Fonts/tahoma.ttf',
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    bold_candidates = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'tahomabd.ttf'),
        'C:/Windows/Fonts/tahomabd.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]

    reg_path = next((p for p in regular_candidates if os.path.exists(p)), None)
    bold_path = next((p for p in bold_candidates if os.path.exists(p)), None)

    if reg_path:
        pdfmetrics.registerFont(TTFont('Digitell-Font', reg_path))
    if bold_path:
        pdfmetrics.registerFont(TTFont('Digitell-Font-Bold', bold_path))
    elif reg_path:
        pdfmetrics.registerFont(TTFont('Digitell-Font-Bold', reg_path))

    _FONTS_REGISTERED = True


def to_persian_digits(val):
    if val is None:
        return ""
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(val).translate(trans)


def fa(text):
    """Reshape and reorder single-line Persian text."""
    if text is None:
        return ""
    text_str = str(text).strip()
    if not text_str:
        return ""
    text_str = to_persian_digits(text_str)
    return get_display(arabic_reshaper.reshape(text_str))


def fa_para(text, style, width_chars=32):
    """
    Wrap multi-line Persian text properly by wrapping into lines first,
    then reshaping each line so words stay top-to-bottom and right-to-left.
    """
    if text is None:
        return Paragraph("", style)
    text_str = str(text).strip()
    if not text_str:
        return Paragraph("", style)
    text_str = to_persian_digits(text_str)

    lines = textwrap.wrap(text_str, width=width_chars)
    if not lines:
        lines = [text_str]
    reshaped_lines = [get_display(arabic_reshaper.reshape(line)) for line in lines]
    html_content = "<br/>".join(reshaped_lines)
    return Paragraph(html_content, style)


def num_to_persian_words(num):
    """Convert integer number into Persian verbal words."""
    try:
        n = int(num)
    except (ValueError, TypeError):
        return ""

    if n == 0:
        return "صفر"

    ones = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    teens = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    hundreds = ["", "یکصد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]
    scales = ["", "هزار", "میلیون", "میلیارد", "تریلیون"]

    def parse_chunk(val):
        parts = []
        c = val // 100
        val %= 100
        if c:
            parts.append(hundreds[c])
        if 10 <= val < 20:
            parts.append(teens[val - 10])
        else:
            t = val // 10
            o = val % 10
            if t:
                parts.append(tens[t])
            if o:
                parts.append(ones[o])
        return " و ".join(parts)

    chunks = []
    scale_idx = 0
    val = abs(n)
    while val > 0:
        chunk = val % 1000
        if chunk > 0:
            words = parse_chunk(chunk)
            if scale_idx > 0:
                words += " " + scales[scale_idx]
            chunks.append(words)
        scale_idx += 1
        val //= 1000

    res = " و ".join(reversed(chunks))
    return ("منفی " + res) if n < 0 else res


def _make_qr_image(content, size=55):
    """Generate in-memory QR code Image for ReportLab."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=1,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=size, height=size)
    except Exception:
        return None


def generate_official_invoice_pdf(order):
    """
    Generate an official Iranian commercial invoice (صورتحساب رسمی فروش کالا و خدمات)
    in PDF format for the given Order object.
    """
    _register_fonts()

    # Jalali dates
    jalali_date_str = ""
    try:
        import jdatetime
        oj = jdatetime.datetime.fromgregorian(datetime=order.created_at)
        jalali_date_str = to_persian_digits(oj.strftime("%Y/%m/%d - %H:%M"))
    except Exception:
        jalali_date_str = to_persian_digits(order.created_at.strftime("%Y/%m/%d %H:%M"))

    buffer = io.BytesIO()

    # Printable width: 595.27 - 40 = 555.27 points
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    style_normal = ParagraphStyle(
        'DigitellNormal',
        fontName='Digitell-Font',
        fontSize=7.5,
        leading=10.5,
        alignment=2,  # Right-aligned
        textColor=colors.HexColor('#1E293B'),
    )
    style_normal_center = ParagraphStyle(
        'DigitellNormalCenter',
        fontName='Digitell-Font',
        fontSize=7.5,
        leading=10.5,
        alignment=1,  # Centered
        textColor=colors.HexColor('#1E293B'),
    )
    style_bold = ParagraphStyle(
        'DigitellBold',
        fontName='Digitell-Font-Bold',
        fontSize=8,
        leading=11,
        alignment=2,
        textColor=colors.HexColor('#0F172A'),
    )

    story = []

    # -------------------------------------------------------------
    # 1. HEADER SECTION
    # -------------------------------------------------------------
    qr_data = (
        f"فروشگاه اینترنتی دیجی‌تل\n"
        f"شماره سفارش: {order.order_number}\n"
        f"مبلغ کل: {order.formatted_final_amount} تومان\n"
        f"تاریخ: {jalali_date_str}\n"
        f"وضعیت: {order.get_status_display()}"
    )
    qr_img = _make_qr_image(qr_data, size=52)

    left_meta = [
        fa(f"شماره فاکتور: {order.order_number}"),
        fa(f"تاریخ صدور: {jalali_date_str}"),
        fa(f"وضعیت پرداخت: {order.get_payment_status_display()}"),
        fa(f"کد تراکنش: {order.transaction_id or '—'}"),
    ]
    left_meta_text = "\n".join(left_meta)

    header_data = [
        [
            # Left: Invoice metadata & QR code
            Table(
                [[
                    Table([[fa(m)] for m in left_meta], colWidths=[120], style=[
                        ('FONT', (0, 0), (-1, -1), 'Digitell-Font-Bold', 7),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0F172A')),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('PADDING', (0, 0), (-1, -1), 1),
                    ]),
                    qr_img or "",
                ]],
                colWidths=[125, 55],
                style=[
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 0),
                ]
            ),
            # Center: Title
            Table(
                [
                    [fa("صورتحساب فروش کالا و خدمات")],
                    [fa("(فاکتور رسمی مطابق با استانداردهای مالیاتی)")],
                    [fa("فروشگاه اینترنتی و حضوری دیجی‌تل")],
                ],
                colWidths=[190],
                style=[
                    ('FONT', (0, 0), (0, 0), 'Digitell-Font-Bold', 12),
                    ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#1E3A8A')),
                    ('FONT', (0, 1), (0, 1), 'Digitell-Font', 7.5),
                    ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#64748B')),
                    ('FONT', (0, 2), (0, 2), 'Digitell-Font-Bold', 9),
                    ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#0F172A')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('PADDING', (0, 0), (-1, -1), 1),
                ]
            ),
            # Right: Store brand info
            Table(
                [
                    [fa("دیجی‌تل | DIGITELL")],
                    [fa("تجارت الکترونیک هوشمند")],
                    [fa("تلفن: ۰۲۱-۶۶۴۰۲۱۲۰")],
                    [fa("www.digitell.ir")],
                ],
                colWidths=[175],
                style=[
                    ('FONT', (0, 0), (0, 0), 'Digitell-Font-Bold', 10),
                    ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#1E3A8A')),
                    ('FONT', (0, 1), (-1, -1), 'Digitell-Font', 7.5),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#475569')),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('PADDING', (0, 0), (-1, -1), 1),
                ]
            ),
        ]
    ]

    header_table = Table(header_data, colWidths=[185, 195, 175])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor('#1E3A8A')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------
    # 2. SELLER & BUYER INFO TABLES
    # -------------------------------------------------------------
    # Seller Section Title
    seller_title = Table([[fa("مشخصات فروشنده (عرضه‌کننده)")]], colWidths=[555])
    seller_title.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E2E8F0')),
        ('FONT', (0, 0), (-1, -1), 'Digitell-Font-Bold', 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
    ]))
    story.append(seller_title)

    seller_rows = [
        [
            fa("کد پستی: ۱۴۱۷۶۳۵۴۱۱"),
            fa("شماره ثبت: ۵۶۳۲۱۰"),
            fa("شناسه ملی: ۱۰۳۸۰۴۵۹۱۲۲"),
            fa("نام: شرکت تجارت هوشمند دیجی‌تل (فروشگاه دیجی‌تل)"),
        ],
        [
            fa("وب‌سایت: www.digitell.ir"),
            fa("تلفن: ۰۲۱-۶۶۴۰۲۱۲۰"),
            fa("استان/شهر: تهران - تهران"),
            fa("نشانی: تهران، خیابان ولیعصر، تقاطع انقلاب، پلاک ۱۴۵، ساختمان دیجی‌تل"),
        ],
    ]
    seller_table = Table(seller_rows, colWidths=[100, 110, 110, 235])
    seller_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Digitell-Font', 7),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
    ]))
    story.append(seller_table)
    story.append(Spacer(1, 4))

    # Buyer Section Title
    buyer_title = Table([[fa("مشخصات خریدار (مشتری)")]], colWidths=[555])
    buyer_title.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E2E8F0')),
        ('FONT', (0, 0), (-1, -1), 'Digitell-Font-Bold', 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
    ]))
    story.append(buyer_title)

    buyer_rows = [
        [
            fa(f"کد پستی: {order.postal_code or '—'}"),
            fa(f"شماره تماس: {order.recipient_phone}"),
            fa("نوع مشتری: مصرف‌کننده نهایی"),
            fa(f"نام و نام خانوادگی: {order.recipient_name}"),
        ],
        [
            fa(f"کد رهگیری مرسوله: {order.tracking_code or 'در حال تخصیص'}"),
            fa(f"روش ارسال: {order.get_shipping_method_display()}"),
            fa(f"استان / شهر: {order.province} - {order.city}"),
            fa(f"نشانی ارسال: {order.shipping_address}"),
        ],
    ]
    buyer_table = Table(buyer_rows, colWidths=[120, 100, 115, 220])
    buyer_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Digitell-Font', 7),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
    ]))
    story.append(buyer_table)
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------
    # 3. ITEMS TABLE
    # -------------------------------------------------------------
    # In PDF from left to right (so Persian reader sees from right to left):
    # Col 0 (left): مبلغ کل (تومان)
    # Col 1: تخفیف (تومان)
    # Col 2: مبلغ واحد (تومان)
    # Col 3: تعداد
    # Col 4: کد کالا (SKU)
    # Col 5: شرح کالا یا خدمات
    # Col 6 (right): ردیف
    # Widths: 90 + 60 + 80 + 35 + 65 + 195 + 30 = 555
    col_widths = [90, 60, 80, 35, 65, 195, 30]

    items_data = [
        [
            fa("مبلغ کل (تومان)"),
            fa("تخفیف"),
            fa("مبلغ واحد (تومان)"),
            fa("تعداد"),
            fa("کد کالا"),
            fa("شرح کالا یا خدمات"),
            fa("ردیف"),
        ]
    ]

    items = list(order.items.select_related('product').all())
    for idx, item in enumerate(items, start=1):
        # Calculate item discount if product had an original price > unit price
        item_discount_val = 0
        if item.product and getattr(item.product, 'original_price', None):
            if item.product.original_price > item.unit_price:
                item_discount_val = (item.product.original_price - item.unit_price) * item.quantity

        item_title_p = fa_para(item.product_title, style_normal, width_chars=36)
        sku = item.product_sku or (item.product.sku if item.product else f"PRD-{idx}")

        items_data.append([
            fa(f"{item.total_price:,}"),
            fa(f"{item_discount_val:,}" if item_discount_val > 0 else "۰"),
            fa(f"{item.unit_price:,}"),
            fa(str(item.quantity)),
            fa(sku),
            item_title_p,
            fa(str(idx)),
        ])

    items_table = Table(items_data, colWidths=col_widths, repeatRows=1)
    items_table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 0), (-1, 0), 'Digitell-Font-Bold', 7.5),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONT', (0, 1), (-1, -1), 'Digitell-Font', 7.5),
        ('ALIGN', (0, 1), (4, -1), 'CENTER'),
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
        ('ALIGN', (6, 1), (6, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1E3A8A')),
    ]

    # Alternate row background
    for row_idx in range(1, len(items_data)):
        if row_idx % 2 == 0:
            items_table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#F8FAFC')))

    items_table.setStyle(TableStyle(items_table_style))
    story.append(items_table)
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------
    # 4. FINANCIAL SUMMARY TABLE
    # -------------------------------------------------------------
    total_discount = (order.discount_amount or 0) + (order.coupon_discount or 0)
    amount_in_words = num_to_persian_words(order.final_amount)

    summary_rows = [
        [
            fa(f"{order.products_total:,} تومان"),
            fa("جمع مبالغ اقلام:"),
            fa(f"مبلغ قابل پرداخت به حروف: {amount_in_words} تومان"),
        ],
        [
            fa(f"{total_discount:,} تومان" if total_discount > 0 else "۰ تومان"),
            fa("مجموع تخفیف‌ها و کمپین:"),
            fa(f"روش پرداخت: {order.get_payment_method_display()} (تراکنش: {order.transaction_id or '—'})"),
        ],
        [
            fa(f"{order.shipping_cost:,} تومان"),
            fa("هزینه ارسال و بسته‌بندی:"),
            fa(f"کد تخفیف اعمال‌شده: {order.coupon_code or 'ندارد'}"),
        ],
        [
            fa(f"{order.final_amount:,} تومان"),
            fa("مبلغ نهایی قابل پرداخت:"),
            fa(f"وضعیت سفارش: {order.get_status_display()} | پرداخت: {order.get_payment_status_display()}"),
        ],
    ]

    summary_table = Table(summary_rows, colWidths=[100, 130, 325])
    summary_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Digitell-Font-Bold', 7.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('BACKGROUND', (0, 3), (1, 3), colors.HexColor('#EFF6FF')),
        ('TEXTCOLOR', (0, 3), (1, 3), colors.HexColor('#1E3A8A')),
        ('FONT', (0, 3), (1, 3), 'Digitell-Font-Bold', 8.5),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # 5. SIGNATURE & OFFICIAL SEALS
    # -------------------------------------------------------------
    signatures_data = [
        [
            # Left: Customer Signature & Acceptance
            Table(
                [
                    [fa("نام و امضای تحویل‌گیرنده کالا:")],
                    [Spacer(1, 30)],
                    [fa("کالاها صحیح و سالم تحویل گرفته شد.")],
                ],
                colWidths=[270],
                style=[
                    ('FONT', (0, 0), (0, 0), 'Digitell-Font-Bold', 7.5),
                    ('FONT', (0, 2), (0, 2), 'Digitell-Font', 6.5),
                    ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#64748B')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('PADDING', (0, 0), (-1, -1), 1),
                ]
            ),
            # Right: Seller Stamp & Signature
            Table(
                [
                    [fa("مهر و امضای مجاز فروشگاه دیجی‌تل:")],
                    [Spacer(1, 30)],
                    [fa("شرکت تجارت هوشمند دیجی‌تل (امور مالی)")],
                ],
                colWidths=[270],
                style=[
                    ('FONT', (0, 0), (0, 0), 'Digitell-Font-Bold', 7.5),
                    ('FONT', (0, 2), (0, 2), 'Digitell-Font', 6.5),
                    ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#64748B')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('PADDING', (0, 0), (-1, -1), 1),
                ]
            ),
        ]
    ]

    signatures_table = Table(signatures_data, colWidths=[277, 278])
    signatures_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
        ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAFA')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether(signatures_table))
    story.append(Spacer(1, 6))

    # Bottom notice
    notice_text = fa(
        "توجه: این فاکتور رسمی به صورت خودکار توسط سامانه فروشگاه دیجی‌تل صادر شده و سند معتبر تسویه حساب و گارانتی کالا می‌باشد."
    )
    notice_p = Paragraph(notice_text, style_normal_center)
    story.append(notice_p)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
