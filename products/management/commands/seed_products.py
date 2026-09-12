from decimal import Decimal
from django.core.management.base import BaseCommand
from products.models import Product
from categories.models import Category


class Command(BaseCommand):
    help = 'Seeds the database with initial categories and organic skincare products safely.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing products and categories before seeding (use with caution in production)',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write(self.style.WARNING('Clearing existing products and categories...'))
            Product.objects.all().delete()
            Category.objects.all().delete()

        creams, _ = Category.objects.get_or_create(
            slug='creams',
            defaults={
                'name': 'Creams',
                'description': 'Hydrating face and body creams formulated with natural botanical extracts.',
            }
        )
        soaps, _ = Category.objects.get_or_create(
            slug='soaps',
            defaults={
                'name': 'Soaps',
                'description': 'Hand-cut, cold-processed soaps made from pure essential oils.',
            }
        )

        products_data = [
            {
                'category': creams,
                'name': 'Honey Glow Cream',
                'slug': 'honey-glow-cream',
                'description': 'A deeply nourishing facial moisturizer formulated with Manuka honey and jojoba oil to restore your natural glow.',
                'price': Decimal('799.00'),
                'original_price': Decimal('999.00'),
                'image': 'products/honey_glow_cream.jpg',
                'stock': 50,
                'is_active': True,
                'best_seller': True,
            },
            {
                'category': creams,
                'name': 'Rose & Aloe Body Butter',
                'slug': 'rose-aloe-body-butter',
                'description': 'Whipped body butter infused with soothing aloe vera and wild rose absolute for 24-hour hydration.',
                'price': Decimal('649.00'),
                'original_price': Decimal('799.00'),
                'image': 'products/rose_aloe_butter.jpg',
                'stock': 45,
                'is_active': True,
                'best_seller': True,
            },
            {
                'category': soaps,
                'name': 'Charcoal Detox Bar',
                'slug': 'charcoal-detox-bar',
                'description': 'Purifying activated charcoal and tea tree oil draw out impurities without stripping the skin.',
                'price': Decimal('349.00'),
                'original_price': Decimal('399.00'),
                'image': 'products/charcoal_detox_bar.jpg',
                'stock': 60,
                'is_active': True,
                'best_seller': True,
            },
            {
                'category': soaps,
                'name': 'Lavender Dream Soap',
                'slug': 'lavender-dream-soap',
                'description': 'Calming lavender essential oil and dried botanical sprigs make this bar perfect for winding down.',
                'price': Decimal('299.00'),
                'original_price': Decimal('349.00'),
                'image': 'products/lavender_dream_soap.jpg',
                'stock': 70,
                'is_active': True,
                'best_seller': True,
            },
        ]

        for item in products_data:
            slug = item.pop('slug')
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults=item
            )
            status_text = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status_text} product: {product.name} (INR {product.price})'))

        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
