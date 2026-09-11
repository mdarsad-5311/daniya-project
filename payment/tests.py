from decimal import Decimal
import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cart.models import Cart, CartItem
from categories.models import Category
from orders.models import Order
from products.models import Product


@override_settings(
    RAZORPAY_KEY_ID='rzp_test_key',
    RAZORPAY_KEY_SECRET='test_secret',
    RAZORPAY_WEBHOOK_SECRET='',
)
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='buyer', password='password123', email='buyer@example.com'
        )
        self.other_user = User.objects.create_user(
            username='other', password='password123', email='other@example.com'
        )
        category = Category.objects.create(name='Face Care', slug='face-care')
        self.product = Product.objects.create(
            category=category,
            name='Test Serum',
            slug='test-serum',
            description='Test product',
            price=Decimal('12.50'),
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart, product=self.product, quantity=2
        )
        self.client.force_login(self.user)
        self.razorpay_client = Mock()
        self.razorpay_client.order.create.return_value = {'id': 'order_test_123'}
        self.razorpay_client.utility.verify_payment_signature.return_value = None
        self.client_patcher = patch(
            'payment.views.razorpay.Client', return_value=self.razorpay_client
        )
        self.client_patcher.start()
        self.addCleanup(self.client_patcher.stop)

    def checkout_data(self):
        return {
            'first_name': 'Test',
            'last_name': 'Buyer',
            'email': 'buyer@example.com',
            'address': '1 Test Street',
            'city': 'Mumbai',
            'postal_code': '400001',
        }

    def create_pending_order(self):
        response = self.client.post(reverse('checkout'), self.checkout_data())
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.client.get(reverse('payment:create', args=[order.id]))
        order.refresh_from_db()
        return order

    def test_checkout_creates_pending_order_and_preserves_cart(self):
        response = self.client.post(reverse('checkout'), self.checkout_data())
        order = Order.objects.get(user=self.user)

        self.assertRedirects(response, reverse('payment:create', args=[order.id]))
        self.assertEqual(order.payment_status, 'pending')
        self.assertFalse(order.paid)
        self.assertEqual(self.cart.items.count(), 1)
        self.assertEqual(order.get_total_cost(), Decimal('25.00'))

    def test_razorpay_order_uses_server_total_in_paise(self):
        order = self.create_pending_order()

        self.razorpay_client.order.create.assert_called_once_with(data={
            'amount': 2500,
            'currency': 'INR',
            'receipt': f'order_{order.id}',
            'notes': {'django_order_id': str(order.id)},
        })
        response = self.client.get(reverse('payment:create', args=[order.id]))
        self.assertContains(response, 'rzp_test_key')
        self.assertNotContains(response, 'test_secret')

    def test_valid_signature_marks_paid_and_clears_cart(self):
        order = self.create_pending_order()

        response = self.client.post(reverse('payment:verify', args=[order.id]), {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'signature_test',
        })

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'pay_test_123')
        self.assertEqual(self.cart.items.count(), 0)

    def test_invalid_signature_does_not_mark_paid_or_clear_cart(self):
        order = self.create_pending_order()
        self.razorpay_client.utility.verify_payment_signature.side_effect = ValueError('bad signature')

        response = self.client.post(reverse('payment:verify', args=[order.id]), {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'invalid',
        })

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertFalse(order.paid)
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(self.cart.items.count(), 1)

    def test_missing_payment_parameters_are_rejected(self):
        order = self.create_pending_order()

        response = self.client.post(reverse('payment:verify', args=[order.id]), {})

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertFalse(order.paid)
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(self.cart.items.count(), 1)

    def test_user_cannot_verify_another_users_order(self):
        order = self.create_pending_order()
        self.client.force_login(self.other_user)

        response = self.client.post(reverse('payment:verify', args=[order.id]), {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'signature_test',
        })

        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertFalse(order.paid)

    def test_duplicate_verification_is_idempotent(self):
        order = self.create_pending_order()
        payload = {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'signature_test',
        }

        first = self.client.post(reverse('payment:verify', args=[order.id]), payload)
        second = self.client.post(reverse('payment:verify', args=[order.id]), payload)

        self.assertEqual(first.json()['status'], 'paid')
        self.assertEqual(second.json()['status'], 'already_paid')
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.cart.items.count(), 0)

    def test_razorpay_api_failure_keeps_order_unpaid_and_cart(self):
        self.razorpay_client.order.create.side_effect = RuntimeError('service down')
        response = self.client.post(reverse('checkout'), self.checkout_data(), follow=True)

        self.assertEqual(response.status_code, 503)
        order = Order.objects.get(user=self.user)
        self.assertFalse(order.paid)
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(self.cart.items.count(), 1)

    def test_verification_requires_csrf(self):
        order = self.create_pending_order()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(reverse('payment:verify', args=[order.id]), {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'signature_test',
        })

        self.assertEqual(response.status_code, 403)

    @override_settings(RAZORPAY_WEBHOOK_SECRET='webhook_secret')
    def test_valid_payment_webhook_marks_order_paid(self):
        order = self.create_pending_order()
        event = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_123',
                        'order_id': order.razorpay_order_id,
                    }
                }
            },
        }

        response = self.client.post(
            reverse('payment:webhook'),
            data=json.dumps(event),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='valid-webhook-signature',
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.payment_status, 'paid')

    @override_settings(RAZORPAY_WEBHOOK_SECRET='webhook_secret')
    def test_invalid_webhook_signature_does_not_mark_order_paid(self):
        order = self.create_pending_order()
        self.razorpay_client.utility.verify_webhook_signature.side_effect = ValueError('bad webhook')

        response = self.client.post(
            reverse('payment:webhook'),
            data=json.dumps({'event': 'payment.captured'}),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid-webhook-signature',
        )

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertFalse(order.paid)

    @override_settings(RAZORPAY_WEBHOOK_SECRET='webhook_secret')
    def test_order_paid_webhook_uses_order_entity(self):
        order = self.create_pending_order()
        event = {
            'event': 'order.paid',
            'payload': {
                'order': {
                    'entity': {'id': order.razorpay_order_id}
                }
            },
        }

        response = self.client.post(
            reverse('payment:webhook'),
            data=json.dumps(event),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='valid-webhook-signature',
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertTrue(order.paid)


@override_settings(
    RAZORPAY_KEY_ID='rzp_test_key',
    RAZORPAY_KEY_SECRET='test_secret',
    RAZORPAY_WEBHOOK_SECRET='',
)
class EndToEndIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Serum Collection', slug='serums')
        self.product = Product.objects.create(
            category=self.category,
            name='Miracle Glow Serum',
            slug='miracle-glow-serum',
            description='Pure hydration and glow.',
            price=Decimal('45.00'),
        )
        self.razorpay_client = Mock()
        self.razorpay_client.order.create.return_value = {'id': 'order_e2e_999'}
        self.razorpay_client.utility.verify_payment_signature.return_value = None
        self.patcher = patch('payment.views.razorpay.Client', return_value=self.razorpay_client)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_complete_customer_journey_and_cart_clearing(self):
        # 1. Register a new user
        password = 'SecurePassword123!'
        reg_res = self.client.post(reverse('register'), {
            'username': 'e2e_customer',
            'password1': password,
            'password2': password,
        })
        self.assertEqual(reg_res.status_code, 302)
        user = User.objects.get(username='e2e_customer')

        # 2. Add product to cart
        add_res = self.client.post(reverse('add_to_cart', args=[self.product.id]), {'qty': 2})
        self.assertEqual(add_res.status_code, 302)
        cart = Cart.objects.get(user=user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)

        # 3. Checkout with customer information
        checkout_payload = {
            'first_name': 'E2E',
            'last_name': 'Tester',
            'email': 'e2e@example.com',
            'address': '42 Discovery Way',
            'city': 'Islamabad',
            'postal_code': '44000',
        }
        checkout_res = self.client.post(reverse('checkout'), checkout_payload)
        self.assertEqual(checkout_res.status_code, 302)

        order = Order.objects.get(user=user)
        self.assertEqual(checkout_res.url, reverse('payment:create', args=[order.id]))
        self.assertFalse(order.paid)
        self.assertEqual(order.payment_status, 'pending')

        # Verify order items created before payment
        self.assertEqual(order.items.count(), 1)
        order_item = order.items.first()
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.price, Decimal('45.00'))
        self.assertEqual(order.get_total_cost(), Decimal('90.00'))

        # Cart still holds items pending successful payment
        self.assertEqual(cart.items.count(), 1)

        # 4. Simulate payment create view
        pay_create_res = self.client.get(reverse('payment:create', args=[order.id]))
        self.assertEqual(pay_create_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.razorpay_order_id, 'order_e2e_999')

        # 5. Verify payment completes order and empties cart
        verify_payload = {
            'razorpay_order_id': 'order_e2e_999',
            'razorpay_payment_id': 'pay_e2e_999',
            'razorpay_signature': 'sig_e2e_999',
        }
        verify_res = self.client.post(reverse('payment:verify', args=[order.id]), verify_payload)
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.json()['status'], 'paid')

        # Order should now be marked paid and cart completely cleared
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.status, 'Processing')
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

        # 6. View confirmation page
        conf_res = self.client.get(reverse('order_confirmation', args=[order.id]))
        self.assertEqual(conf_res.status_code, 200)
        self.assertContains(conf_res, f'Order #{order.id}')
        self.assertContains(conf_res, 'Miracle Glow Serum')

        # 7. View user profile and my orders
        profile_res = self.client.get(reverse('profile'))
        self.assertEqual(profile_res.status_code, 200)
        my_orders_res = self.client.get(reverse('my_orders'))
        self.assertEqual(my_orders_res.status_code, 200)
        self.assertContains(my_orders_res, f'Order #{order.id}')

        # 8. Log out
        logout_res = self.client.post(reverse('logout'))
        self.assertRedirects(logout_res, reverse('home'))
        self.assertFalse(logout_res.wsgi_request.user.is_authenticated)

