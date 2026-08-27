"""
سكريبت لمسح بيانات التشغيل مع الإبقاء على:
- الترابيزات (tables)
- المنيو والأصناف (products & categories)
- المستخدمين (accounts)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("[*] جاري مسح البيانات...")

# -- 1. الأوردرات وعناصرها --
try:
    from orders.models import Order, OrderItem
    count = OrderItem.objects.count()
    OrderItem.objects.all().delete()
    print(f"[OK] تم مسح {count} عنصر اوردر (OrderItems)")

    count = Order.objects.count()
    Order.objects.all().delete()
    print(f"[OK] تم مسح {count} اوردر (Orders)")
except Exception as e:
    print(f"[SKIP] Orders: {e}")

# -- 2. المدفوعات --
try:
    from payments.models import Payment
    count = Payment.objects.count()
    Payment.objects.all().delete()
    print(f"[OK] تم مسح {count} دفعة (Payments)")
except Exception as e:
    print(f"[SKIP] Payments: {e}")

# -- 3. الجلسات (sessions الطاولات) --
try:
    from sessions.models import TableSession
    count = TableSession.objects.count()
    TableSession.objects.all().delete()
    print(f"[OK] تم مسح {count} جلسة طاولة (TableSessions)")
except Exception as e:
    print(f"[SKIP] TableSessions: {e}")

# -- 4. النشاطات --
try:
    from activities.models import Activity
    count = Activity.objects.count()
    Activity.objects.all().delete()
    print(f"[OK] تم مسح {count} نشاط (Activities)")
except Exception as e:
    print(f"[SKIP] Activities: {e}")

# -- 5. الاشعارات --
try:
    from notifications.models import Notification
    count = Notification.objects.count()
    Notification.objects.all().delete()
    print(f"[OK] تم مسح {count} اشعار (Notifications)")
except Exception as e:
    print(f"[SKIP] Notifications: {e}")

# -- 6. طابور الانتظار --
try:
    from queue_system.models import QueueEntry
    count = QueueEntry.objects.count()
    QueueEntry.objects.all().delete()
    print(f"[OK] تم مسح {count} سجل انتظار (Queue)")
except Exception as e:
    print(f"[SKIP] Queue: {e}")

# -- 7. التقارير --
try:
    from reports.models import Report
    count = Report.objects.count()
    Report.objects.all().delete()
    print(f"[OK] تم مسح {count} تقرير (Reports)")
except Exception as e:
    print(f"[SKIP] Reports: {e}")

# -- 8. المخزون (الحركات مش المنتجات) --
try:
    from inventory.models import InventoryTransaction
    count = InventoryTransaction.objects.count()
    InventoryTransaction.objects.all().delete()
    print(f"[OK] تم مسح {count} حركة مخزون (InventoryTransactions)")
except Exception as e:
    print(f"[SKIP] InventoryTransactions: {e}")

print("\n[DONE] تم مسح كل البيانات بنجاح!")
print("[INFO] الترابيزات والمنيو والاصناف لسه موجودين زي ما هم.")

