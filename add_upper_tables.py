import os
import django

# إعداد بيئة جانغو للسكربت
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Floor
from tables.models import Table

def add_upper_tables():
    # البحث عن الطابق العلوي أو إنشاؤه إذا لم يكن موجوداً
    floor, created = Floor.objects.get_or_create(
        name='علوي',
        defaults={
            'order': 2,
            'is_active': True
        }
    )
    
    if created:
        print("تم إنشاء طابق 'علوي' بنجاح.")
    else:
        print("تم العثور على طابق 'علوي'.")
        
    print("-" * 30)

    # حصر الطاولات الموجودة في هذا الطابق لمعرفة أين انتهت الأرقام
    last_table = Table.objects.filter(floor=floor).order_by('-number').first()
    start_num = last_table.number + 1 if last_table else 1
    
    # نريد إضافة 15 طاولة جديدة
    tables_to_add = 15
    end_num = start_num + tables_to_add
    
    tables_created = 0
    
    for num in range(start_num, end_num):
        table_name = f'ترابيزة علوي {num}'
        
        # إنشاء الطاولة
        table, t_created = Table.objects.get_or_create(
            floor=floor,
            number=num,
            defaults={
                'name': table_name,
                'capacity': 4,
                'is_active': True,
                'status': Table.Status.EMPTY
            }
        )
        
        if t_created:
            print(f"تمت إضافة: {table.name} (رقم الطاولة: {num})")
            tables_created += 1
        else:
            print(f"الطاولة رقم {num} موجودة مسبقاً.")

    print("-" * 30)
    print(f"تم الانتهاء! تمت إضافة {tables_created} ترابيزة جديدة للطابق العلوي بنجاح.")

if __name__ == '__main__':
    add_upper_tables()
