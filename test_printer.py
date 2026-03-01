"""
Test image-based Arabic receipt printing with table columns.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from core.printer import ReceiptBuilder, FONT_TITLE, FONT_HEADER, FONT_NORMAL, FONT_BOLD, FONT_SMALL, _send_raw

r = ReceiptBuilder()

# Header
r.add_space(8)
r.add_text('*  *  *', font=FONT_TITLE, align='center')
r.add_text('التكية', font=FONT_TITLE, align='center')
r.add_text('*  *  *', font=FONT_NORMAL, align='center')
r.add_double_separator()

# Session info
r.add_text('طاولة علوي 5', font=FONT_HEADER, align='center')
r.add_text('التاريخ: 2026-02-28 21:00', font=FONT_NORMAL, align='center')
r.add_text('الكاشير: فادي', font=FONT_NORMAL, align='center')
r.add_separator()

# Item Table
r.add_item_header()

r.add_item_row('طبق فول عادي طحينة', 2, 15.0, 30.0)
r.add_dotted_separator()

r.add_item_row('طبق شكشوكة', 1, 15.0, 15.0)
r.add_dotted_separator()

r.add_item_row('ساندوتش فول إسكندراني', 3, 8.0, 24.0)
r.add_dotted_separator()

r.add_item_row('كوباية زبادي', 1, 10.0, 10.0)
r.add_separator()

r.add_row('إجمالي الطلبات', '79.00 ج.م', font=FONT_BOLD)
r.add_double_separator()

# Total
r.add_text('الإجمالي: 79.00 ج.م', font=FONT_TITLE, align='center')
r.add_space(4)
r.add_text('طريقة الدفع: كاش', font=FONT_NORMAL, align='center')
r.add_double_separator()

# Footer
r.add_text('شكراً لزيارتكم!', font=FONT_BOLD, align='center')
r.add_text('التكية', font=FONT_HEADER, align='center')
r.add_space(8)

# Save preview image
img = r.build()
img.save('receipt_preview_v3.png')
print(f"Preview saved to receipt_preview_v3.png ({img.size[0]}x{img.size[1]})")

# Send to printer
data = r.to_escpos()
print(f"Sending {len(data)} bytes to printer...")
success = _send_raw(data, job_name='CMS_Test_Columns')
if success:
    print("SUCCESS! Check the printer.")
else:
    print("FAILED!")
