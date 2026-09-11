from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from orders.models import Order


User = get_user_model()


class AuthenticationFlowTests(TestCase):
	def setUp(self):
		self.password = 'Strong-password-123!'
		self.user = User.objects.create_user(
			username='account-user',
			email='account@example.com',
			password=self.password,
			first_name='Account',
		)

	def test_register_page_and_valid_registration(self):
		response = self.client.get(reverse('register'))
		self.assertEqual(response.status_code, 200)
		response = self.client.post(reverse('register'), {
			'username': 'new-user',
			'password1': self.password,
			'password2': self.password,
		})
		self.assertRedirects(response, reverse('home'))
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_invalid_registration_renders_errors(self):
		response = self.client.post(reverse('register'), {
			'username': 'new-user',
			'password1': self.password,
			'password2': 'Different-password-123!',
		})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'password fields')

	def test_login_supports_next_and_invalid_credentials(self):
		response = self.client.get(reverse('login'))
		self.assertEqual(response.status_code, 200)
		response = self.client.post(reverse('login'), {
			'username': self.user.username,
			'password': 'wrong-password',
		})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Please enter a correct username and password.')

		response = self.client.post(reverse('login') + '?next=/orders/my-orders/', {
			'username': self.user.username,
			'password': self.password,
			'next': '/orders/my-orders/',
		})
		self.assertRedirects(response, reverse('my_orders'))

	def test_external_next_url_is_not_trusted(self):
		response = self.client.post(reverse('login'), {
			'username': self.user.username,
			'password': self.password,
			'next': 'https://example.com/account',
		})
		self.assertRedirects(response, reverse('home'))

	def test_profile_requires_login_and_shows_navigation(self):
		response = self.client.get(reverse('profile'))
		self.assertRedirects(response, f'{reverse("login")}?next={reverse("profile")}')
		self.client.login(username=self.user.username, password=self.password)
		response = self.client.get(reverse('profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse('cart'))
		self.assertContains(response, reverse('wishlist'))
		self.assertContains(response, reverse('my_orders'))

	def test_logout_requires_post_and_redirects(self):
		self.client.login(username=self.user.username, password=self.password)
		response = self.client.get(reverse('logout'))
		self.assertRedirects(response, reverse('home'))
		self.assertTrue(response.wsgi_request.user.is_authenticated)

		response = self.client.post(reverse('logout'))
		self.assertRedirects(response, reverse('home'))
		self.assertFalse(response.wsgi_request.user.is_authenticated)

	def test_logout_requires_csrf_token(self):
		csrf_client = Client(enforce_csrf_checks=True)
		csrf_client.force_login(self.user)
		response = csrf_client.post(reverse('logout'))
		self.assertEqual(response.status_code, 403)

	def test_navbar_authentication_states(self):
		response = self.client.get(reverse('home'))
		self.assertContains(response, 'Register')
		self.assertContains(response, 'Login')
		self.assertNotContains(response, '>Logout<')

		self.client.login(username=self.user.username, password=self.password)
		response = self.client.get(reverse('home'))
		self.assertContains(response, 'Profile')
		self.assertContains(response, 'My Orders')
		self.assertContains(response, 'Logout')


class MyOrdersSecurityTests(TestCase):
	def setUp(self):
		self.password = 'Strong-password-123!'
		self.user = User.objects.create_user(username='owner', password=self.password)
		self.other_user = User.objects.create_user(username='other', password=self.password)
		order_data = {
			'first_name': 'Owner',
			'last_name': 'User',
			'email': 'owner@example.com',
			'address': '1 Main Street',
			'city': 'Lahore',
			'postal_code': '54000',
		}
		self.user_order = Order.objects.create(user=self.user, **order_data)
		Order.objects.create(user=self.other_user, **order_data)

	def test_my_orders_requires_login_and_is_user_scoped(self):
		response = self.client.get(reverse('my_orders'))
		self.assertEqual(response.status_code, 302)

		self.client.login(username=self.user.username, password=self.password)
		response = self.client.get(reverse('my_orders'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'Order #{self.user_order.id}')
		other_order = Order.objects.get(user=self.other_user)
		self.assertNotContains(response, f'Order #{other_order.id}')


class AdditionalAuthTests(TestCase):
	def setUp(self):
		self.password = 'Strong-password-123!'
		self.user = User.objects.create_user(
			username='existinguser',
			email='existing@example.com',
			password=self.password,
		)

	def test_duplicate_username_registration_rejected(self):
		response = self.client.post(reverse('register'), {
			'username': 'existinguser',
			'password1': self.password,
			'password2': self.password,
		})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A user with that username already exists.')
		self.assertEqual(User.objects.filter(username='existinguser').count(), 1)

	def test_authenticated_user_redirected_away_from_login_and_register(self):
		self.client.login(username='existinguser', password=self.password)
		login_res = self.client.get(reverse('login'))
		self.assertRedirects(login_res, reverse('home'))
		register_res = self.client.get(reverse('register'))
		self.assertRedirects(register_res, reverse('home'))

	def test_newsletter_subscription(self):
		from accounts.models import NewsletterSubscriber
		response = self.client.post(reverse('subscribe'), {'email': 'newsletter@example.com'})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(NewsletterSubscriber.objects.filter(email='newsletter@example.com').exists())
		self.assertContains(response, 'Thanks for subscribing!')

