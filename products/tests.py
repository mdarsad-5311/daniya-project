from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category

from .models import Product, Review


class ReviewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='reviewer',
			password='test-password-123',
		)
		category = Category.objects.create(name='Care', slug='care')
		self.product = Product.objects.create(
			category=category,
			name='Daily Cream',
			slug='daily-cream',
			description='A simple cream.',
			price='24.00',
			image='',
		)
		self.url = reverse('review_create', args=[self.product.slug])

	def test_anonymous_user_is_redirected_to_login(self):
		response = self.client.post(self.url, {'rating': 5, 'comment': 'Lovely.'})

		self.assertRedirects(response, f'{reverse("login")}?next={self.url}')
		self.assertFalse(Review.objects.exists())

	def test_authenticated_user_can_create_review(self):
		self.client.login(username='reviewer', password='test-password-123')

		response = self.client.post(self.url, {'rating': 5, 'comment': 'Lovely.'})

		self.assertRedirects(response, reverse('product_detail', args=[self.product.slug]))
		review = Review.objects.get()
		self.assertEqual(review.product, self.product)
		self.assertEqual(review.user, self.user)
		self.assertEqual(review.rating, 5)

	def test_second_submission_updates_existing_review(self):
		self.client.login(username='reviewer', password='test-password-123')
		self.client.post(self.url, {'rating': 5, 'comment': 'Lovely.'})

		self.client.post(self.url, {'rating': 3, 'comment': 'It is good.'})

		self.assertEqual(Review.objects.filter(product=self.product, user=self.user).count(), 1)
		review = Review.objects.get()
		self.assertEqual(review.rating, 3)
		self.assertEqual(review.comment, 'It is good.')

	def test_product_detail_displays_review_summary(self):
		Review.objects.create(product=self.product, user=self.user, rating=4, comment='Good.')

		response = self.client.get(reverse('product_detail', args=[self.product.slug]))

		self.assertContains(response, '4.0')
		self.assertContains(response, '1 review')
		self.assertContains(response, 'Good.')

# Create your tests here.
from decimal import Decimal


class ProductModelAndDetailTests(TestCase):
	def setUp(self):
		self.category_skincare = Category.objects.create(name='Skincare', slug='skincare')
		self.category_serums = Category.objects.create(name='Serums', slug='serums')

	def test_product_creation_with_valid_data(self):
		product = Product.objects.create(
			category=self.category_skincare,
			name='Hydrating Moisturizer',
			description='A lightweight daily hydrating face moisturizer.',
			price=Decimal('29.95'),
			original_price=Decimal('39.99'),
			best_seller=True,
		)
		self.assertEqual(product.name, 'Hydrating Moisturizer')
		self.assertEqual(product.description, 'A lightweight daily hydrating face moisturizer.')
		self.assertEqual(product.price, Decimal('29.95'))
		self.assertEqual(product.original_price, Decimal('39.99'))
		self.assertEqual(product.category, self.category_skincare)
		self.assertTrue(product.best_seller)
		self.assertEqual(str(product), 'Hydrating Moisturizer')

	def test_slug_auto_generation_when_blank(self):
		product = Product.objects.create(
			category=self.category_skincare,
			name='Vitamin C Night Cream',
			description='Brightening night cream formula.',
			price=Decimal('34.50'),
		)
		self.assertEqual(product.slug, 'vitamin-c-night-cream')

	def test_product_detail_lookup_by_valid_slug(self):
		product = Product.objects.create(
			category=self.category_skincare,
			name='Rosewater Toner Mist',
			slug='rosewater-toner-mist',
			description='Hydrating and soothing rose water facial mist.',
			price=Decimal('18.00'),
		)
		response = self.client.get(reverse('product_detail', args=[product.slug]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['product'], product)
		self.assertContains(response, 'Rosewater Toner Mist')
		self.assertContains(response, '18.00')

	def test_product_detail_returns_404_for_nonexistent_slug(self):
		response = self.client.get(reverse('product_detail', args=['non-existent-product-slug']))
		self.assertEqual(response.status_code, 404)

	def test_product_price_stored_and_precision_preserved(self):
		product = Product.objects.create(
			category=self.category_serums,
			name='Retinol Repair Elixir',
			description='Night elixir treatment.',
			price=Decimal('49.99'),
		)
		product.refresh_from_db()
		self.assertIsInstance(product.price, Decimal)
		self.assertEqual(product.price, Decimal('49.99'))
		# Precision calculation check
		total_cost = product.price * 3
		self.assertEqual(total_cost, Decimal('149.97'))

	def test_product_category_relationship_and_filtering(self):
		prod1 = Product.objects.create(
			category=self.category_skincare,
			name='Skincare Balm',
			price=Decimal('15.00'),
		)
		prod2 = Product.objects.create(
			category=self.category_serums,
			name='Serum Dropper',
			price=Decimal('25.00'),
		)

		self.assertIn(prod1, self.category_skincare.products.all())
		self.assertNotIn(prod2, self.category_skincare.products.all())
		self.assertEqual(self.category_serums.products.count(), 1)

		# Filter shop page by category slug
		shop_response = self.client.get(reverse('shop'), {'category': ['skincare']})
		self.assertEqual(shop_response.status_code, 200)
		products_in_context = list(shop_response.context['products'])
		self.assertIn(prod1, products_in_context)
		self.assertNotIn(prod2, products_in_context)

	def test_inactive_product_hidden_from_shop(self):
		inactive_product = Product.objects.create(
			category=self.category_skincare,
			name='Archived Cream',
			price=Decimal('10.00'),
			is_active=False,
		)
		shop_response = self.client.get(reverse('shop'))
		self.assertNotIn(inactive_product, shop_response.context['products'])


from django.core.exceptions import ValidationError
from .models import ContactMessage
from .forms import ReviewForm, ContactForm


class ContactAndValidationTests(TestCase):
	def test_review_rating_validation(self):
		form = ReviewForm(data={'rating': 6, 'comment': 'Invalid'})
		self.assertFalse(form.is_valid())
		self.assertIn('rating', form.errors)

		valid_form = ReviewForm(data={'rating': 4, 'comment': 'Valid'})
		self.assertTrue(valid_form.is_valid())

	def test_contact_form_submission_persists_message(self):
		payload = {
			'name': 'Test Customer',
			'email': 'customer@example.com',
			'subject': 'Order Inquiry',
			'message': 'Hello, I have a question about my order.',
		}
		response = self.client.post(reverse('contact'), payload, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(ContactMessage.objects.filter(email='customer@example.com').exists())
		msg = ContactMessage.objects.get(email='customer@example.com')
		self.assertEqual(msg.name, 'Test Customer')
		self.assertEqual(msg.subject, 'Order Inquiry')
		self.assertContains(response, 'Thank you! Your message has been sent successfully.')


