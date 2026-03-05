"""
USB Thermal Printer Integration (ESC/POS) — Image-Based Arabic Printing
Renders receipt as an image using Pillow, then sends the bitmap to the printer.
This guarantees correct Arabic RTL rendering regardless of printer codepage.
"""
import logging
import os
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ─── Printer Config ──────────────────────────────────────────────────
PRINTER_WIDTH_PX = 576          # 80mm paper = 576 dots at 203 DPI
LINE_SPACING = 8                # extra px between lines
MARGIN = 30                     # left/right margin px (inside frame)

# ─── Fonts ────────────────────────────────────────────────────────────
FONTS_DIR = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')

def _font(size=20, bold=False):
    fname = 'arialbd.ttf' if bold else 'arial.ttf'
    path = os.path.join(FONTS_DIR, fname)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

FONT_TITLE   = _font(48, bold=True)
FONT_HEADER  = _font(38, bold=True)
FONT_NORMAL  = _font(32)
FONT_BOLD    = _font(32, bold=True)
FONT_SMALL   = _font(28)

# ─── Arabic Text Shaping ─────────────────────────────────────────────
def _shape_arabic(text: str) -> str:
    """Reshape Arabic text for proper rendering: connects letters and applies RTL."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

# ─── ESC/POS Constants ───────────────────────────────────────────────
ESC = b'\x1b'
GS  = b'\x1d'
INIT = ESC + b'\x40'
ALIGN_CENTER = ESC + b'\x61\x01'
FEED_AND_CUT = ESC + b'\x64\x06' + GS + b'\x56\x01'


# ─── Image to ESC/POS Raster ─────────────────────────────────────────
def _image_to_raster(img: Image.Image) -> bytes:
    """Convert a PIL Image to ESC/POS raster bit-image format."""
    # Convert to monochrome 1-bit
    img = img.convert('1')
    width, height = img.size
    pixels = img.load()

    # Width must be multiple of 8
    byte_width = (width + 7) // 8

    data = b''
    for y in range(height):
        # GS v 0 — print raster bit image (one row at a time)
        # Format: GS v 0 m xL xH yL yH [data]
        # m=0 (normal), xL xH = byte_width, yL yH = 1 row
        row_bytes = bytearray()
        for bx in range(byte_width):
            byte_val = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < width:
                    pixel = pixels[x, y]
                    # In mode '1': 0=black, 255=white
                    if pixel == 0:  # black pixel → print
                        byte_val |= (0x80 >> bit)
            row_bytes.append(byte_val)
        data += row_bytes

    # Send as one raster block
    # GS v 0 m xL xH yL yH d1...dk
    xL = byte_width & 0xFF
    xH = (byte_width >> 8) & 0xFF
    yL = height & 0xFF
    yH = (height >> 8) & 0xFF

    return GS + b'\x76\x30\x00' + bytes([xL, xH, yL, yH]) + data


# ─── Printer Discovery & Send ────────────────────────────────────────
def _find_printer():
    """Find the first Xprinter or Generic / Text Only printer."""
    try:
        import win32print
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        for p in all_printers:
            name = p[2]
            if 'xprinter' in name.lower() or 'generic' in name.lower():
                return name
        default = win32print.GetDefaultPrinter()
        if default:
            return default
    except Exception as e:
        logger.error(f"Printer discovery failed: {e}")
    return None


def _send_raw(data: bytes, job_name: str = 'CMS_Receipt'):
    """Send raw ESC/POS bytes to the printer."""
    try:
        import win32print
        printer_name = _find_printer()
        if not printer_name:
            logger.warning("No printer found – skipping print.")
            return False

        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hPrinter, 1, (job_name, None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
        return True
    except Exception as e:
        logger.error(f"Printing failed: {e}")
        return False


# ─── Settings Helpers ─────────────────────────────────────────────────
def _get_cafe_name():
    try:
        from core.models import SystemSettings
        s = SystemSettings.load()
        return s.cafe_name or 'التكية'
    except Exception:
        return 'التكية'

def _get_currency():
    try:
        from core.models import SystemSettings
        s = SystemSettings.load()
        return s.currency or 'ج.م'
    except Exception:
        return 'ج.م'


# ─── Receipt Image Builder ───────────────────────────────────────────
class ReceiptBuilder:
    """Builds a receipt image line-by-line, then outputs ESC/POS raster data."""

    def __init__(self, width=PRINTER_WIDTH_PX):
        self.width = width
        self.usable = width - (MARGIN * 2)
        self.lines = []  # list of (image_line) — each is a row image
        self.y = 0

    def _text_size(self, text, font):
        """Get text bounding box size."""
        dummy = Image.new('1', (1, 1), 1)
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def add_text(self, text, font=None, align='center', bold=False):
        """Add a line of text (Arabic is auto-shaped)."""
        if font is None:
            font = FONT_BOLD if bold else FONT_NORMAL
        shaped = _shape_arabic(text)
        tw, th = self._text_size(shaped, font)
        row_h = th + LINE_SPACING
        row = Image.new('1', (self.width, row_h), 1)  # white bg
        draw = ImageDraw.Draw(row)

        if align == 'center':
            x = (self.width - tw) // 2
        elif align == 'right':
            x = self.width - MARGIN - tw
        else:
            x = MARGIN

        draw.text((x, 0), shaped, font=font, fill=0)  # black text
        self.lines.append(row)

    def add_row(self, right_text, left_text, font=None):
        """Add a row with right-aligned Arabic label and left-aligned value.
        For Arabic receipts: item name on the right, price/qty on the left.
        """
        if font is None:
            font = FONT_NORMAL
        shaped_right = _shape_arabic(right_text) if right_text else ''
        shaped_left = _shape_arabic(left_text) if left_text else ''
        rw, rh = self._text_size(shaped_right, font) if shaped_right else (0, 18)
        lw, lh = self._text_size(shaped_left, font) if shaped_left else (0, 18)
        row_h = max(rh, lh) + LINE_SPACING
        row = Image.new('1', (self.width, row_h), 1)
        draw = ImageDraw.Draw(row)
        # Right text on the right side
        if shaped_right:
            draw.text((self.width - MARGIN - rw, 0), shaped_right, font=font, fill=0)
        # Left text on the left side
        if shaped_left:
            draw.text((MARGIN, 0), shaped_left, font=font, fill=0)
        self.lines.append(row)

    def add_table_row(self, col_data, col_widths, font=None, aligns=None):
        """Add a row with multiple columns. col_widths are in pixels.
        col_data: list of strings.
        col_widths: list of widths (must sum up to usable width).
        aligns: list of 'left', 'center', 'right'.
        """
        if font is None:
            font = FONT_NORMAL
        if aligns is None:
            aligns = ['right'] * len(col_data)

        row_h = 40 # Standard height for table rows
        row = Image.new('1', (self.width, row_h), 1)
        draw = ImageDraw.Draw(row)
        
        current_x = self.width - MARGIN
        for i, text in enumerate(col_data):
            width = col_widths[i]
            align = aligns[i]
            shaped = _shape_arabic(text or "")
            tw, th = self._text_size(shaped, font)
            
            # Start X for this column (moving right to left)
            x_start = current_x - width
            
            # Sub-alignment within column
            if align == 'center':
                draw_x = x_start + (width - tw) // 2
            elif align == 'left':
                draw_x = x_start
            else: # right
                draw_x = current_x - tw
                
            draw.text((draw_x, (row_h - th) // 2), shaped, font=font, fill=0)
            current_x -= width
            
        self.lines.append(row)

    def add_item_header(self):
        """Specific header for item table."""
        cols = ['الصنف', 'ك', 'سعر', 'اجمالي']
        # Total usable: 516px (576 - 60)
        # Name: 250, Qty: 50, Price: 100, Total: 116
        widths = [250, 50, 100, 116]
        aligns = ['right', 'center', 'center', 'left']
        self.add_table_row(cols, widths, font=FONT_BOLD, aligns=aligns)
        self.add_separator()

    def add_item_row(self, name, qty, price, total):
        """Specific row for items."""
        cols = [name, str(qty), f"{price:.1f}", f"{total:.1f}"]
        widths = [250, 50, 100, 116]
        aligns = ['right', 'center', 'center', 'left']
        self.add_table_row(cols, widths, font=FONT_NORMAL, aligns=aligns)

    def add_separator(self, style='dashed'):
        """Add a separator line within margins."""
        row_h = 12
        row = Image.new('1', (self.width, row_h), 1)
        draw = ImageDraw.Draw(row)
        y = row_h // 2
        x_start = MARGIN + 2
        x_end = self.width - MARGIN - 2
        
        if style == 'dotted':
            for x in range(x_start, x_end, 4):
                draw.point((x, y), fill=0)
        else: # dashed
            for x in range(x_start, x_end, 8):
                draw.line((x, y, min(x+4, x_end), y), fill=0, width=1)
                
        self.lines.append(row)

    def add_dotted_separator(self):
        self.add_separator('dotted')

    def add_double_separator(self):
        """Add a double line separator."""
        row_h = 14
        row = Image.new('1', (self.width, row_h), 1)
        draw = ImageDraw.Draw(row)
        x_start = MARGIN + 2
        x_end = self.width - MARGIN - 2
        draw.line((x_start, 4, x_end, 4), fill=0, width=2)
        draw.line((x_start, 9, x_end, 9), fill=0, width=2)
        self.lines.append(row)

    def add_space(self, px=8):
        """Add empty space."""
        row = Image.new('1', (self.width, px), 1)
        self.lines.append(row)

    def build(self) -> Image.Image:
        """Combine all lines into a single image and draw an outer frame."""
        total_h = sum(l.size[1] for l in self.lines)
        pad_y = 12
        img = Image.new('1', (self.width, total_h + pad_y * 2), 1)
        y = pad_y
        for line_img in self.lines:
            img.paste(line_img, (0, y))
            y += line_img.size[1]
            
        # Draw aesthetic frame
        draw = ImageDraw.Draw(img)
        # Outer bold frame
        draw.rectangle([2, 2, self.width - 3, img.size[1] - 3], outline=0, width=3)
        # Inner fine frame
        draw.rectangle([8, 8, self.width - 9, img.size[1] - 9], outline=0, width=1)
        
        return img

    def to_escpos(self) -> bytes:
        """Build image and convert to ESC/POS raster commands."""
        img = self.build()
        data = INIT
        data += ALIGN_CENTER  # Center the image to avoid left-shift
        data += _image_to_raster(img)
        data += FEED_AND_CUT
        return data


# ─── Kitchen Receipt ─────────────────────────────────────────────────
def print_kitchen_receipt(order):
    """
    Print segmented kitchen tickets based on product categories.
    Stages:
    1. Sohour: أطباق السحور، أطباق إضافية، سندوتشات، بطاطس
    2. Shisha: شيشة، إضافات شيشة
    3. Bar: All other categories (Drinks, Desserts, etc.)
    """
    from orders.models import Order
    if isinstance(order, int):
        order = Order.objects.select_related('table').prefetch_related('items__product__category').get(pk=order)
    
    # Define category groups
    SOHOUR_CATS = ['أطباق السحور', 'أطباق إضافية', 'سندوتشات', 'بطاطس']
    SHISHA_CATS = ['شيشة', 'إضافات شيشة']
    
    all_items = list(order.items.all())
    if not all_items:
        return False

    # Group items (skip virtual items like percentage adjustments with no product)
    valid_items = [i for i in all_items if i.product is not None]
    groups = {
        '🥘 سحور': [i for i in valid_items if i.product.category.name in SOHOUR_CATS],
        '💨 شيشة': [i for i in valid_items if i.product.category.name in SHISHA_CATS],
        '☕ بار': [i for i in valid_items if i.product.category.name not in SOHOUR_CATS and i.product.category.name not in SHISHA_CATS]
    }

    success = True
    for group_name, items in groups.items():
        if not items:
            continue
            
        r = ReceiptBuilder()
        # Header
        r.add_space(4)
        r.add_text(f'تكت {group_name}', font=FONT_TITLE, align='center')
        r.add_separator()

        # Table & order
        table_name = f"{order.table.floor.name} - {order.table.display_name}" if order.table else 'تيك أواي'
        r.add_text(table_name, font=FONT_HEADER, align='center')
        if order.shift_order_number:
            r.add_text(f'تكت رقم: {order.shift_order_number}', font=FONT_TITLE, align='center')
        else:
            r.add_text(f'طلب #{order.pk}', font=FONT_NORMAL, align='center')
        from django.utils import timezone
        # 12-hour format for kitchen
        time_local = timezone.localtime(order.created_at) if timezone.is_aware(order.created_at) else order.created_at
        time_str = time_local.strftime('%I:%M %p').replace('AM', 'ص').replace('PM', 'م')
        r.add_text(time_str, font=FONT_NORMAL, align='center')
        r.add_separator()

        # Items
        for item in items:
            name = item.product.name
            if item.size_name:
                name += f' ({item.size_name})'
            r.add_row(name, f'x{item.quantity}', font=FONT_BOLD)
            if item.notes:
                r.add_text(f'** {item.notes}', font=FONT_SMALL, align='right')

        r.add_separator()

        # Order-level Notes (printed on all tickets if exist)
        if order.notes:
            r.add_text(f'ملاحظات عامة: {order.notes}', font=FONT_NORMAL, align='right')
            r.add_separator()

        # Footer
        r.add_text(f'--- {group_name} التكية ---', font=FONT_SMALL, align='center')
        r.add_space(4)

        data = r.to_escpos()
        if not _send_raw(data, job_name=f'CMS_Kitchen_{group_name}'):
            success = False
            
    return success


# ─── Client Receipt ──────────────────────────────────────────────────
def print_client_receipt(payment):
    """Print a full client receipt after payment."""
    from payments.models import Payment
    from django.db import models
    import datetime

    # Ensure we have a fresh object with all fields (especially auto_now_add ones)
    try:
        payment_id = payment.pk if hasattr(payment, 'pk') else payment
        payment = Payment.objects.select_related(
            'session__primary_table', 'paid_by'
        ).get(pk=payment_id)
    except Exception as e:
        logger.error(f"Failed to fetch payment {payment}: {e}")
        return False

    session = payment.session
    
    if session:
        orders = session.orders.prefetch_related('items__product').exclude(status='cancelled')
        activities = session.activity_sessions.select_related('device__activity_type').filter(ended_at__isnull=False)
    else:
        # Takeaway payment - find orders by other means
        from orders.models import Order
        orders = Order.objects.filter(
            is_takeaway=True, shift=payment.shift, confirmed_by=payment.paid_by
        ).prefetch_related('items__product').exclude(status='cancelled').order_by('-created_at')[:1]
        activities = []

    cafe_name = _get_cafe_name()
    currency = _get_currency()

    r = ReceiptBuilder()

    # ═══ Header ═══
    r.add_space(8)
    r.add_text('*  *  *', font=FONT_TITLE, align='center')
    r.add_text(cafe_name, font=FONT_TITLE, align='center')
    r.add_text('*  *  *', font=FONT_NORMAL, align='center')
    r.add_double_separator()

    # ═══ Session info ═══
    if payment.shift_invoice_number:
        r.add_text(f'فاتورة رقم: {payment.shift_invoice_number}', font=FONT_HEADER, align='center')
    
    if session:
        table_name = f"{session.primary_table.floor.name} - {session.primary_table.display_name}"
        # Check for merged tables
        all_tables = list(session.tables.all())
        if len(all_tables) > 1:
            table_name = ' & '.join(f"{t.floor.name} - {t.display_name}" for t in all_tables)
    else:
        table_name = 'تيك أواي 🛍️'
    r.add_text(table_name, font=FONT_HEADER, align='center')
    
    # Handle potentially missing paid_at
    from django.utils import timezone
    paid_at = payment.paid_at or timezone.now()
    paid_at_local = timezone.localtime(paid_at) if timezone.is_aware(paid_at) else paid_at
    # 12-hour format with AM/PM
    time_str = paid_at_local.strftime('%Y-%m-%d  %I:%M %p')
    # Simple replacement for Arabic context if needed, or just standard AM/PM
    time_str = time_str.replace('AM', 'ص').replace('PM', 'م')
    r.add_text('التاريخ: ' + time_str, font=FONT_NORMAL, align='center')
    if payment.paid_by:
        cashier = payment.paid_by.get_full_name() or payment.paid_by.username
        r.add_text(f'الكاشير: {cashier}', font=FONT_NORMAL, align='center')
    r.add_separator()

    # ═══ Order Items ═══
    has_orders = False
    for order in orders:
        items = order.items.all()
        if items.exists():
            if not has_orders:
                r.add_item_header()
                has_orders = True
            for item in items:
                r.add_item_row(
                    item.display_name, 
                    item.quantity, 
                    item.price, 
                    item.subtotal
                )
                r.add_dotted_separator()

    if has_orders:
        r.add_separator()
        total_orders = session.total_orders if session else sum(
            sum(i.subtotal for i in o.items.all()) for o in orders
        )
        r.add_row(f'إجمالي الطلبات', f'{total_orders:.2f} {currency}', font=FONT_BOLD)

    # ═══ Activities ═══
    has_activities = False
    for act in activities:
        if not has_activities:
            r.add_space(8)
            r.add_text('الأنشطة', font=FONT_BOLD)
            r.add_separator()
            has_activities = True
        
        # Check if this activity was paid separately
        act_is_paid = act.payments.exclude(pk=payment.pk).exists()
        tag = ' (مدفوع)' if act_is_paid else ''
        r.add_row(act.device.name + f' ({act.duration_display}){tag}', f'{act.total_price:.2f}', font=FONT_NORMAL)
        r.add_dotted_separator()

    if has_activities and session:
        r.add_separator()
        r.add_row('إجمالي الأنشطة', f'{session.total_activities:.2f} {currency}', font=FONT_BOLD)

    # ═══ Totals ═══
    r.add_double_separator()

    # Pre-payment info for full session receipts
    if session:
        # Calculate total previous payments excluding the current one
        prev_payments = session.payments.exclude(pk=payment.pk).aggregate(total=models.Sum('amount'))['total'] or 0
        if prev_payments > 0:
            r.add_row('إجمالي الجلسة', f'{session.total_amount:.2f} {currency}', font=FONT_NORMAL)
            r.add_row('تم دفعه مسبقاً', f'-{prev_payments:.2f} {currency}', font=FONT_NORMAL)
            r.add_separator()

    if payment.discount and payment.discount > 0:
        r.add_row('الخصم', f'{payment.discount:.2f} {currency}', font=FONT_NORMAL)

    r.add_text(f'المبلغ المدفوع: {payment.final_amount:.2f} {currency}', font=FONT_TITLE, align='center')
    r.add_space(4)
    r.add_text(f'طريقة الدفع: {payment.get_method_display()}', font=FONT_NORMAL, align='center')
    r.add_double_separator()

    # ═══ Footer ═══
    r.add_text('شكراً لزيارتكم!', font=FONT_BOLD, align='center')
    r.add_text('*  *  *', font=FONT_NORMAL, align='center')
    r.add_text(cafe_name, font=FONT_HEADER, align='center')
    r.add_space(4)
    r.add_text('Powered by: NEXUS CODE', font=FONT_BOLD, align='center')
    r.add_text('FADY ASHRAF', font=FONT_BOLD, align='center')
    r.add_text('01069476417', font=FONT_NORMAL, align='center')
    r.add_space(10)

    data = r.to_escpos()
    success = _send_raw(data, job_name='CMS_Client_Receipt')
    if success:
        logger.info(f"Client receipt printed for payment #{payment.pk}")
    return success


def print_activity_receipt(activity_session):
    """Print a compact receipt for a single activity session."""
    from activities.models import ActivitySession
    
    cafe_name = _get_cafe_name()
    currency = _get_currency()
    
    r = ReceiptBuilder()
    
    # Header
    r.add_space(8)
    r.add_text(cafe_name, font=FONT_TITLE, align='center')
    r.add_double_separator()
    
    # Info
    table_name = f"{activity_session.session.primary_table.floor.name} - {activity_session.session.primary_table.display_name}" if activity_session.session and activity_session.session.primary_table else "نشاط"
    r.add_text(table_name, font=FONT_HEADER, align='center')
    
    from django.utils import timezone
    now = timezone.localtime(timezone.now())
    r.add_text(now.strftime('%Y-%m-%d  %I:%M %p').replace('AM', 'ص').replace('PM', 'م'), font=FONT_NORMAL, align='center')
    r.add_separator()
    
    # Activity Details
    r.add_text('تفاصيل النشاط', font=FONT_BOLD, align='center')
    r.add_space(4)
    r.add_row('الجهاز:', activity_session.device.name, font=FONT_NORMAL)
    r.add_row('النوع:', activity_session.device.activity_type.name, font=FONT_NORMAL)
    r.add_row('الوقت المنقضي:', activity_session.duration_display, font=FONT_NORMAL)
    r.add_separator()
    
    # Check if paid
    is_paid = activity_session.payments.exists()
    
    # Total
    if is_paid:
        r.add_text(f'الإجمالي: {activity_session.total_price:.2f} {currency}', font=FONT_BOLD, align='center')
        r.add_text('*** مـدفـوع ***', font=FONT_TITLE, align='center')
    else:
        r.add_text(f'المطلوب: {activity_session.total_price:.2f} {currency}', font=FONT_TITLE, align='center')
    
    r.add_double_separator()
    
    # Footer
    r.add_text('شكراً لزيارتكم!', font=FONT_BOLD, align='center')
    r.add_space(10)
    
    data = r.to_escpos()
    return _send_raw(data, job_name='CMS_Activity_Receipt')

# ─── Shift Report ──────────────────────────────────────────────────
def print_shift_report(shift_id, printed_by=None):
    """Print 4 separate receipts for a fully comprehensive shift report."""
    from reports.models import CashierShift
    from orders.models import Order
    from payments.models import Payment
    from activities.models import ActivitySession
    from django.utils import timezone
    from django.db.models import Q, Sum

    try:
        shift = CashierShift.objects.get(pk=shift_id)
    except CashierShift.DoesNotExist:
        logger.error(f"Shift {shift_id} not found for printing.")
        return False

    end_time = shift.ended_at or timezone.now()
    prev_shift = CashierShift.objects.filter(started_at__lt=shift.started_at).order_by('-started_at').first()
    start_time = prev_shift.ended_at if prev_shift and prev_shift.ended_at else shift.started_at

    ord_filter = Q(shift=shift) | (Q(shift__isnull=True) & Q(created_at__gte=start_time, created_at__lte=end_time))
    orders = Order.objects.filter(ord_filter).exclude(status=Order.Status.CANCELLED).prefetch_related('items__product__category')

    pay_filter = Q(shift=shift) | (Q(shift__isnull=True) & Q(paid_at__gte=start_time, paid_at__lte=end_time))
    payments = Payment.objects.filter(pay_filter)

    activities = ActivitySession.objects.filter(
        started_at__gte=start_time,
        started_at__lte=end_time,
        ended_at__isnull=False
    )

    SOHOUR_CATS = ['أطباق السحور', 'أطباق إضافية', 'سندوتشات', 'بطاطس']
    SHISHA_CATS = ['شيشة', 'إضافات شيشة']

    shisha_items = {}
    suhoor_items = {}
    bar_items = {}
    activity_items = {}

    for order in orders:
        for item in order.items.all():
            if not item.product:
                continue
            cat = item.product.category.name if item.product.category else ''

            key = (item.product.id, item.size_name)
            name = item.display_name

            if cat in SHISHA_CATS:
                target_dict = shisha_items
            elif cat in SOHOUR_CATS:
                target_dict = suhoor_items
            else:
                target_dict = bar_items

            if key not in target_dict:
                target_dict[key] = {'name': name, 'qty': 0, 'total': 0.0}

            target_dict[key]['qty'] += item.quantity
            target_dict[key]['total'] += float(item.subtotal)

    for act in activities:
        key = act.device.id
        name = act.device.name
        if key not in activity_items:
            activity_items[key] = {'name': name, 'qty': 0, 'total': 0.0}
        
        # We define qty here as the number of sessions for this device, and total as the total price.
        activity_items[key]['qty'] += 1
        activity_items[key]['total'] += float(act.total_price)

    cafe_name = _get_cafe_name()
    currency = _get_currency()
    time_str = timezone.localtime(timezone.now()).strftime('%Y-%m-%d  %I:%M %p').replace('AM', 'ص').replace('PM', 'م')

    def print_category_receipt(title, items_dict):
        r = ReceiptBuilder()
        r.add_space(8)
        r.add_text(cafe_name, font=FONT_TITLE, align='center')
        r.add_double_separator()
        r.add_text(title, font=FONT_HEADER, align='center')
        r.add_text(f'شيفت رقم: {shift.pk}', font=FONT_NORMAL, align='center')
        r.add_text('التاريخ: ' + time_str, font=FONT_NORMAL, align='center')
        r.add_separator()

        if not items_dict:
            r.add_text('لا توجد مبيعات', font=FONT_NORMAL, align='center')
            r.add_separator()
        else:
            r.add_item_header()
            total_qty = 0
            total_price = 0.0
            for k, v in items_dict.items():
                unit_price = v['total'] / v['qty'] if v['qty'] else 0
                r.add_item_row(v['name'], v['qty'], unit_price, v['total'])
                r.add_dotted_separator()
                total_qty += v['qty']
                total_price += v['total']

            r.add_separator()
            r.add_row('إجمالي الكمية', str(total_qty), font=FONT_BOLD)
            r.add_row('إجمالي المبلغ', f"{total_price:.2f} {currency}", font=FONT_BOLD)

        r.add_space(10)
        data = r.to_escpos()
        _send_raw(data, job_name=f'CMS_Shift_{title}')

    # Print Category Receipts
    print_category_receipt('تقرير الشيشة', shisha_items)
    print_category_receipt('تقرير السحور', suhoor_items)
    print_category_receipt('تقرير البار', bar_items)
    print_category_receipt('تقرير البلايستيشن والأنشطة', activity_items)

    # Print Final Summary Receipt
    r = ReceiptBuilder()
    r.add_space(8)
    r.add_text(cafe_name, font=FONT_TITLE, align='center')
    r.add_double_separator()
    r.add_text('التقرير الختامي للشيفت', font=FONT_HEADER, align='center')
    r.add_text(f'شيفت رقم: {shift.pk}', font=FONT_NORMAL, align='center')
    if shift.ended_at:
        r.add_text('الحالة: مغلق', font=FONT_NORMAL, align='center')
    else:
        r.add_text('الحالة: نشط', font=FONT_NORMAL, align='center')
    r.add_text('وقت الطباعة: ' + time_str, font=FONT_NORMAL, align='center')
    r.add_separator()

    total_rev = round(float(payments.aggregate(total=Sum('amount'))['total'] or 0), 2)
    total_disc = round(float(payments.aggregate(total=Sum('discount'))['total'] or 0), 2)
    cash_rev = round(float(payments.filter(method='cash').aggregate(total=Sum('amount'))['total'] or 0), 2)
    visa_rev = round(float(payments.filter(method='visa').aggregate(total=Sum('amount'))['total'] or 0), 2)
    acts_rev = round(float(activities.aggregate(total=Sum('total_price'))['total'] or 0), 2)
    
    refunded_payments = payments.filter(refunded_amount__gt=0)
    refund_count = refunded_payments.count()
    total_refund = round(float(refunded_payments.aggregate(total=Sum('refunded_amount'))['total'] or 0), 2)

    r.add_text('ملخص الإيرادات', font=FONT_BOLD, align='center')
    r.add_space(4)
    r.add_row('إجمالي الطلبات (العدد)', str(orders.count()))
    r.add_row('إجمالي الأنشطة (العدد)', str(activities.count()))
    r.add_separator()
    r.add_row('إيراد الكاش', f"{cash_rev:.2f} {currency}")
    r.add_row('إيراد الفيزا', f"{visa_rev:.2f} {currency}")
    r.add_row('إيراد الأنشطة', f"{acts_rev:.2f} {currency}")
    r.add_separator()
    r.add_row('إجمالي الخصومات', f"{total_disc:.2f} {currency}")
    r.add_row('الصافي الكلي', f"{total_rev:.2f} {currency}", font=FONT_BOLD)
    r.add_separator()
    r.add_text('المرتجعات', font=FONT_BOLD, align='center')
    r.add_row('الفواتير المرتجعة (العدد)', str(refund_count))
    r.add_row('قيمة المرتجعات', f"{total_refund:.2f} {currency}")
    r.add_double_separator()

    r.add_text('تمت الطباعة بواسطة', font=FONT_NORMAL, align='center')
    if printed_by:
        r.add_text(printed_by.get_full_name() or printed_by.username, font=FONT_BOLD, align='center')
    r.add_space(10)

    data = r.to_escpos()
    _send_raw(data, job_name='CMS_Shift_Total')

    return True
