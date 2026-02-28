import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Category, Product

# Data to import
data = {
  "restaurant_name": "التكية",
  "greeting": "مُبَارَكٌ عَلَيْكُمُ الشَّهْرُ",
  "menu": {
    "sohour_dishes": [
      { "name": "طبق فول عادي طحينة", "price": 15 },
      { "name": "طبق فول إسكندراني", "price": 20 },
      { "name": "طبق فول زيت حار", "price": 15 },
      { "name": "طبق فول زيت زيتون", "price": 20 },
      { "name": "طبق أومليت", "price": 15 },
      { "name": "طبق بطاطس صوابع", "price": 10 },
      { "name": "طبق بطاطس مهروسة", "price": 10 },
      { "name": "طبق بطاطس بانيه", "price": 10 },
      { "name": "بيض مسلوق (1)", "price": 10 },
      { "name": "طبق مسقعة", "price": 12 },
      { "name": "طبق شكشوكة", "price": 15 },
      { "name": "طبق عجة فرنساوي", "price": 15 },
      { "name": "طبق بابا غنوج", "price": 15 },
      { "name": "طعمية قرص كبير (سادة)", "price": 3 },
      { "name": "طعمية محشية", "price": 5 },
      { "name": "عيش سياحي", "price": 1.5 },
      { "name": "سلطة خضراء", "price": 10 },
      { "name": "مخلل", "price": 10 },
      { "name": "جبنة مقلية", "price": 30 },
      { "name": "كوباية زبادي", "price": 10 }
    ],
    "extra_dishes": [
      { "name": "طبق جبنة طماطم", "price": 15 },
      { "name": "طبق باذنجان", "price": 10 },
      { "name": "طبق شيبسي", "price": 10 },
      { "name": "طبق بيض بسطرمة", "price": 30 }
    ],
    "sandwiches": [
      { "name": "ساندوتش طعمية مشكل", "price": 10 },
      { "name": "ساندوتش طعمية على بطاطس", "price": 8 },
      { "name": "ساندوتش بابا غنوج", "price": 8 },
      { "name": "ساندوتش فول عادي", "price": 7 },
      { "name": "ساندوتش فول إسكندراني", "price": 8 },
      { "name": "ساندوتش فول زيت حار", "price": 10 },
      { "name": "ساندوتش فول زيت زيتون", "price": 12 }
    ],
    "fries": [
      { "name": "باكيت بطاطس", "price": 15 },
      { "name": "بطاطس رومي", "price": 25 },
      { "name": "بطاطس كاتشب مايونيز", "price": 20 }
    ]
  }
}

category_names_ar = {
    "sohour_dishes": "أطباق السحور",
    "extra_dishes": "أطباق إضافية",
    "sandwiches": "سندوتشات",
    "fries": "بطاطس"
}

def import_sohour_menu():
    print(f"Starting import for restaurant: {data['restaurant_name']}")
    print(f"Greeting: {data['greeting']}")
    print("-" * 30)

    total_products_added = 0
    total_categories_added = 0

    for cat_key, items in data['menu'].items():
        cat_name_ar = category_names_ar.get(cat_key, cat_key)
        
        # Create or get category
        category, cat_created = Category.objects.get_or_create(
            name=cat_name_ar,
            defaults={
                'icon': '🌙',
                'is_active': True
            }
        )
        
        if cat_created:
            print(f"Created category: {category.name}")
            total_categories_added += 1
        else:
            print(f"Found category: {category.name}")
            
        # Create products in this category
        items_added = 0
        for item in items:
            product, prod_created = Product.objects.get_or_create(
                category=category,
                name=item['name'],
                defaults={
                    'price': item['price'],
                    'is_available': True,
                    'is_active': True,
                }
            )
            
            if prod_created:
                items_added += 1
                print(f"  + Added: {item['name']} - {item['price']} EGP")
            else:
                # Optional: update price if product already exists
                if product.price != item['price']:
                    product.price = item['price']
                    product.save()
                    print(f"  ~ Updated price for: {item['name']} to {item['price']} EGP")
                else:
                    print(f"  = Exists: {item['name']}")
                    
        total_products_added += items_added
        print(f"Completed category {category.name}: added {items_added} new items.")
        print("-" * 20)

    print(f"Import finished! Added {total_categories_added} new categories and {total_products_added} new products.")

if __name__ == '__main__':
    import_sohour_menu()
