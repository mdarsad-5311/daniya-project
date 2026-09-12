from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

from products.models import Product
from .models import Category


class CategoryTests(TestCase):
    def setUp(self):
        self.creams = Category.objects.create(name='Creams', slug='creams', description='Soothing creams')
        self.soaps = Category.objects.create(name='Soaps', slug='soaps', description='Natural soaps')

        self.active_prod = Product.objects.create(
            category=self.creams,
            name='Face Butter',
            price=Decimal('500.00'),
            is_active=True,
        )
        self.inactive_prod = Product.objects.create(
            category=self.creams,
            name='Expired Cream',
            price=Decimal('200.00'),
            is_active=False,
        )

    def test_category_slug_collision_safe(self):
        duplicate = Category.objects.create(name='Creams')
        self.assertTrue(duplicate.slug.startswith('creams-'))
        self.assertNotEqual(duplicate.slug, 'creams')

    def test_category_detail_view_returns_200_and_filters_inactive(self):
        response = self.client.get(reverse('category_detail', args=['creams']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Face Butter')
        self.assertNotContains(response, 'Expired Cream')

    def test_category_detail_view_returns_404_for_nonexistent_slug(self):
        response = self.client.get(reverse('category_detail', args=['non-existent-category']))
        self.assertEqual(response.status_code, 404)

    def test_direct_creams_and_soaps_urls(self):
        res_creams = self.client.get(reverse('creams'))
        self.assertEqual(res_creams.status_code, 200)
        self.assertContains(res_creams, 'Face Butter')

        res_soaps = self.client.get(reverse('soaps'))
        self.assertEqual(res_soaps.status_code, 200)
