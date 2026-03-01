import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Category, Product, ProductSize

MENU_DATA = {
  "hot_drinks": [
    {"name": "قهوة تركي", "price": "25 سنجل / 40 دبل"},
    {"name": "اسبريسو", "price": "35 سنجل / 45 دبل"},
    {"name": "اسبريسو ميكاتو", "price": "35 سنجل / 40 دبل"},
    {"name": "كورتادو", "price": 50},
    {"name": "كراميل ميكاتو", "description": "اسبريسو + حليب + فليفر فانيليا + صوص كراميل", "price": 65},
    {"name": "فلات وايت", "price": 50},
    {"name": "لاتيه", "price": 50},
    {"name": "اسبانيش لاتيه", "price": 55},
    {"name": "بستاشيو لاتيه", "price": 70},
    {"name": "كابتشينو", "price": 50},
    {"name": "امريكانو", "price": 50},
    {"name": "موكا", "description": "دارك - وايت", "price": 55},
    {"name": "ابل سيدر", "price": 40},
    {"name": "فيتامين سي", "description": "برتقال + عسل + ليمون + جوافة", "price": 50},
    {"name": "شاي", "price": 15},
    {"name": "شاي أخضر", "price": 20},
    {"name": "براد شاي", "price": 30},
    {"name": "سحلب مكسرات", "price": 40},
    {"name": "سحلب فواكه", "price": 50},
    {"name": "نسكافيه بلاك", "price": 30},
    {"name": "نسكافيه حليب", "price": 40},
    {"name": "كاكاو حليب", "price": 40}
  ],
  "hot_chocolate": [
    {"name": "هوت شوكلت", "description": "نوتيلا - وايت - كندر", "price": 50},
    {"name": "هوت شوكلت دارك", "price": 45},
    {"name": "هوت شوكلت مارشميلو", "price": 65}
  ],
  "iced_coffee": [
    {"name": "ايس لاتيه", "price": 50},
    {"name": "اسبانيش لاتيه", "price": 60},
    {"name": "ايس موكا", "description": "وايت - دارك", "price": 60},
    {"name": "ايس امريكانو", "price": 50},
    {"name": "ايس كراميل ميكاتو", "price": 55}
  ],
  "frappe": [
    {"name": "فرابتشينو كلاسيك", "price": 55},
    {"name": "فرابتشينو فليفر", "description": "فانيليا - دارك - كراميل", "price": 60},
    {"name": "فرابيه لوتس", "price": 60},
    {"name": "فرابيه كندر", "price": 60}
  ],
  "milk_shake": [
    {"name": "ميلك تشيك", "description": "شوكلت - فانيليا - فراولة - مانجا", "price": 55},
    {"name": "ميلك تشيك", "description": "بلوبيري - مكس بيري - بطيخ", "price": 60},
    {"name": "ميلك تشيك", "description": "نوتيلا - لوتس - كراميل - كندر", "price": 60},
    {"name": "ميلك تشيك بستاشيو", "price": 80},
    {"name": "ميلك تشيك أوريو", "price": 70}
  ],
  "mojito": [
    {"name": "موهيتو كلاسيك", "price": 45},
    {"name": "موهيتو فليفر", "description": "بلوبيري - فراولة - باشون فروت - مانجا - اناناس - كريز", "price": 55},
    {"name": "موهيتو ريدبول", "description": "بلوبيري - فراولة - باشون فروت - مانجا - اناناس - كريز", "price": 80},
    {"name": "جيلي كولا", "description": "اناناس - ليمون - كولا", "price": 55}
  ],
  "smoothie": [
    {"name": "سموزي نكهات", "description": "فراولة - ميكس بيري - برتقال - بطيخ - باشون فروت - أناناس - جوافة", "price": 55},
    {"name": "كولا كريز", "price": 45},
    {"name": "ليمون برتقال", "price": 50},
    {"name": "ليمون نعناع", "price": 50}
  ],
  "cocktails": [
    {"name": "مانجو فراولة", "price": 55},
    {"name": "مانجو كيوي", "price": 60},
    {"name": "خوخ مانجو", "price": 55},
    {"name": "جوافة موز", "price": 50},
    {"name": "جوافة نعناع", "price": 50},
    {"name": "بانش بلانش", "description": "اناناس + كيوي + برتقال + تفاح", "price": 55},
    {"name": "سويت & سور", "description": "بطيخ كيوي + فراولة + ليمون", "price": 55},
    {"name": "لافلي التكية", "description": "مكس توت + موز + فراولة + ايس كريم فانيليا", "price": 55},
    {"name": "جرين باور", "description": "أفوكادو + كيوي + مكسرات + عسل + حليب + ايس كريم فانيليا", "price": 75},
    {"name": "بانانا جرين", "description": "موز + أفوكادو + لوز", "price": 70},
    {"name": "باور التكية", "description": "موز + حليب + عسل + أفوكادو + مكسرات + قرفة + زبدة فول سوداني + بلح", "price": 80},
    {"name": "جولد كيوي", "description": "أناناس كيوي + موز", "price": 65}
  ],
  "fresh_juices": [
    {"name": "مانجو", "price": 50},
    {"name": "فراولة", "price": 45},
    {"name": "فراولة حليب", "price": 50},
    {"name": "برتقال", "price": 40},
    {"name": "جوافة", "price": 40},
    {"name": "جوافة حليب", "price": 45},
    {"name": "كانتلوب", "price": 40},
    {"name": "كانتلوب حليب", "price": 45},
    {"name": "أناناس", "price": 50},
    {"name": "كيوي", "price": 50},
    {"name": "بطيخ", "price": 50},
    {"name": "خوخ", "price": 50},
    {"name": "موز حليب", "price": 50},
    {"name": "بلح حليب", "price": 50},
    {"name": "أفوكادو حليب", "price": 70},
    {"name": "ليمون", "price": 30},
    {"name": "ليمون نعناع", "price": 40}
  ],
  "yoghurt": [
    {"name": "زبادي عسل", "price": 40},
    {"name": "زبادي فراولة", "price": 50},
    {"name": "زبادي مانجا", "price": 50},
    {"name": "زبادي موز", "price": 50},
    {"name": "زبادي كيوي", "price": 70},
    {"name": "زبادي أفوكادو", "price": 75}
  ],
  "soft_drinks": [
    {"name": "كولا", "price": 30},
    {"name": "فيروز", "price": 35},
    {"name": "بريل", "price": 35},
    {"name": "جولد", "price": 35},
    {"name": "ريدبول", "price": 80},
    {"name": "فيوري", "price": 35},
    {"name": "استنج", "price": 35},
    {"name": "مياه صغيرة", "price": 10},
    {"name": "مياه كبيرة", "price": 15}
  ],
  "goblet_cookies": [
    {"name": "جوبلت كوكيز صوص", "description": "نوتيلا - كندر - لوتس - كراميل - وايت شوكلت", "price": 60},
    {"name": "جوبلت كوكيز هاف و هاف", "description": "2 صوص من إختيارك", "price": 75},
    {"name": "جوبلت بستاشيو", "price": 90},
    {"name": "جوبلت ابل باي", "description": "تفاح مكرمل بالقرفة", "price": 60},
    {"name": "جوبلت بانانا باي", "description": "موز مكرمل بالقرفة", "price": 60}
  ],
  "desserts": [
    {"name": "أم علي مكسرات", "price": 50},
    {"name": "تشيز كيك صوص", "description": "نوتيلا - لوتس - كراميل - دارك - وايت", "price": 65},
    {"name": "تشيز كيك بستاشيو", "price": 90},
    {"name": "مولتن كيك", "price": 70},
    {"name": "سينابون صوص", "description": "نوتيلا - لوتس - كراميل - دارك - وايت", "price": 65},
    {"name": "سينابون بستاشيو", "price": 90},
    {"name": "فادج كيك", "price": 65},
    {"name": "فروت سلاد", "price": 70}
  ],
  "pan_cake": [
    {"name": "بان كيك 12 قطعة", "description": "نوتيلا - لوتس - كراميل - دارك - كندر", "price": 50},
    {"name": "بان كيك 12 قطعة هاف و هاف", "description": "ميكس صوص من إختيارك", "price": 60},
    {"name": "بان كيك 12 قطعة بستاشيو", "price": 70},
    {"name": "بان كيك 24 قطعة", "description": "نوتيلا - لوتس - كراميل - دارك - كندر", "price": 80},
    {"name": "بان كيك 24 قطعة هاف و هاف", "description": "ميكس صوص من إختيارك", "price": 90},
    {"name": "بان كيك 24 قطعة بستاشيو", "price": 100}
  ],
  "waffles": [
    {"name": "وافلز", "description": "نوتيلا - لوتس - وايت - كراميل - دارك - كندر", "price": 50},
    {"name": "وافلز هاف و هاف", "description": "ميكس نوعين صوص", "price": 65},
    {"name": "وافلز بستاشيو", "price": 80},
    {"name": "وافلز فواكه", "price": 60},
    {"name": "وافلز ابل باي", "description": "مع التفاح المكرمل والقرفة", "price": 65},
    {"name": "وافلز بانانا باي", "description": "مع الموز المكرمل والقرفة", "price": 55}
  ],
  "shesha": [
    {"name": "شيشة كلاسيك", "price": 20},
    {"name": "شيشة فواكه", "price": 45},
    {"name": "شيشة ميكس", "price": 50},
    {"name": "شيشة مخصوص التكية", "description": "تقدم في شيشة تركي مستورد مع إضافة ثلج مع مكس معسل التكية من إختيارك", "price": 60}
  ],
  "shesha_adds": [
    {"name": "ثلج", "price": 5},
    {"name": "فليفر", "price": 10},
    {"name": "حليب", "price": 10},
    {"name": "بولة ايس كريم", "price": 15},
    {"name": "مكسرات", "price": 15}
  ]
}

CATEGORY_NAMES = {
    "hot_drinks": "مشروبات ساخنة",
    "hot_chocolate": "هوت شوكلت",
    "iced_coffee": "ايس كوفي",
    "frappe": "فرابيه",
    "milk_shake": "ميلك تشيك",
    "mojito": "موهيتو",
    "smoothie": "سموزي",
    "cocktails": "كوكتيلات",
    "fresh_juices": "عصائر فريش",
    "yoghurt": "زبادي فواكه",
    "soft_drinks": "مشروبات غازية",
    "goblet_cookies": "جوبلت كوكيز",
    "desserts": "حلويات",
    "pan_cake": "بان كيك",
    "waffles": "وافلز",
    "shesha": "شيشة",
    "shesha_adds": "إضافات شيشة"
}

def import_menu():
    print("Starting menu import...")
    
    for cat_slug, items in MENU_DATA.items():
        cat_name = CATEGORY_NAMES.get(cat_slug, cat_slug.replace('_', ' ').title())
        category, created = Category.objects.get_or_create(name=cat_name)
        if created:
            print(f"Created category: {cat_name}")
        
        for item in items:
            name = item['name']
            desc = item.get('description', '')
            price_val = item['price']
            
            # Check if it has sizes (like coffee)
            has_sizes = False
            default_price = 0
            sizes_to_create = []
            
            if isinstance(price_val, str) and '/' in price_val:
                # Format: "25 سنجل / 40 دبل"
                has_sizes = True
                parts = price_val.split('/')
                for part in parts:
                    part = part.strip()
                    # Extract number and name
                    try:
                        p_val = "".join([c for c in part if c.isdigit() or c == '.'])
                        p_name = "".join([c for c in part if not c.isdigit() and c != '.']).strip()
                        sizes_to_create.append({
                            'name': p_name,
                            'price': float(p_val),
                            'size': 'small' if 'سنجل' in p_name else ('medium' if 'دبل' in p_name else 'large')
                        })
                        if not default_price:
                            default_price = float(p_val)
                    except:
                        print(f"Error parsing price part: {part}")
            else:
                default_price = float(price_val)
            
            product, created = Product.objects.update_or_create(
                name=name,
                category=category,
                defaults={
                    'description': desc,
                    'price': default_price,
                    'has_sizes': has_sizes
                }
            )
            
            if has_sizes:
                for s_data in sizes_to_create:
                    # Clear existing if any to avoid unique constraint if we changed logic
                    ProductSize.objects.update_or_create(
                        product=product,
                        size=s_data['size'],
                        defaults={
                            'name': s_data['name'],
                            'price': s_data['price']
                        }
                    )
            
            status = "Created" if created else "Updated"
            print(f"  {status} product: {name}")

    print("Menu import finished successfully!")

if __name__ == "__main__":
    import_menu()
