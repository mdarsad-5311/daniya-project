import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daniya_project.settings')
django.setup()

from products.models import Product
from categories.models import Category

# Clear existing
Product.objects.all().delete()
Category.objects.all().delete()

# Create Categories
creams, _ = Category.objects.get_or_create(name='Creams', slug='creams', description='Hydrating face and body creams.')
soaps, _ = Category.objects.get_or_create(name='Soaps', slug='soaps', description='Hand-cut, cold-processed soaps.')

# Create Products
products = [
    {
        'category': creams,
        'name': 'Honey Glow Cream',
        'slug': 'honey-glow-cream',
        'description': 'A deeply nourishing facial moisturizer formulated with Manuka honey and jojoba oil to restore your natural glow.',
        'price': '34.00',
        'original_price': None,
        'image': 'products/honey_glow_cream.jpg',
        'best_seller': True,
    },
    {
        'category': creams,
        'name': 'Rose & Aloe Body Butter',
        'slug': 'rose-aloe-body-butter',
        'description': 'Whipped body butter infused with soothing aloe vera and wild rose absolute for 24-hour hydration.',
        'price': '28.00',
        'original_price': '35.00',
        'image': 'products/rose_aloe_butter.jpg',
        'best_seller': True,
    },
    {
        'category': soaps,
        'name': 'Charcoal Detox Bar',
        'slug': 'charcoal-detox-bar',
        'description': 'Purifying activated charcoal and tea tree oil draw out impurities without stripping the skin.',
        'price': '14.00',
        'original_price': None,
        'image': 'products/charcoal_detox_bar.jpg',
        'best_seller': True,
    },
    {
        'category': soaps,
        'name': 'Lavender Dream Soap',
        'slug': 'lavender-dream-soap',
        'description': 'Calming lavender essential oil and dried botanical sprigs make this bar perfect for winding down.',
        'price': '12.00',
        'original_price': '15.00',
        'image': 'products/lavender_dream_soap.jpg',
        'best_seller': True,
    }
]

for data in products:
    p = Product(**data)
    p.save()

print("Database populated successfully!")
