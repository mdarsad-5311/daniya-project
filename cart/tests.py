from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from products.models import Product
from cart.models import Cart, CartItem

User = get_user_model()


class CartWorkflowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Skincare', slug='skincare')
        self.product1 = Product.objects.create(
            category=self.category,
            name='Hydrating Cleanser',
            slug='hydrating-cleanser',
            description='Gentle cleanser.',
            price=Decimal('20.00'),
        )
        self.product2 = Product.objects.create(
            category=self.category,
            name='Moisture Cream',
            slug='moisture-cream',
            description='Rich cream.',
            price=Decimal('35.50'),
        )
        self.user = User.objects.create_user(
            username='cartuser',
            password='Password123!',
            email='cartuser@example.com',
        )

    # ---------------------------------------------------------
    # Guest cart tests (Session-based)
    # ---------------------------------------------------------

    def test_guest_add_item_to_cart(self):
        # Add item
        response = self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 1})
        self.assertEqual(response.status_code, 302)

        # Cart should exist with session_id
        session_key = self.client.session.session_key
        self.assertTrue(session_key)
        cart = Cart.objects.get(session_id=session_key, user=None)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.product, self.product1)
        self.assertEqual(item.quantity, 1)

    def test_guest_view_cart_renders_correct_details(self):
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 2})
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hydrating Cleanser')
        self.assertEqual(response.context['cart_count'], 2)
        self.assertEqual(response.context['subtotal'], Decimal('40.00'))
        self.assertEqual(response.context['total'], Decimal('40.00'))

    def test_guest_increase_quantity_via_add_or_update(self):
        # Adding same item increments quantity
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 1})
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 2})

        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_id=session_key)
        item = cart.items.get(product=self.product1)
        self.assertEqual(item.quantity, 3)

        # Update cart quantity directly
        response = self.client.post(reverse('update_cart', args=[item.id]), {'quantity': 5})
        self.assertRedirects(response, reverse('cart'))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

        # Verify cart total updated: 5 * 20.00 = 100.00
        view_response = self.client.get(reverse('cart'))
        self.assertEqual(view_response.context['total'], Decimal('100.00'))

    def test_guest_decrease_quantity(self):
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 3})
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_id=session_key)
        item = cart.items.get(product=self.product1)
        self.assertEqual(item.quantity, 3)

        # Decrease to 2
        self.client.post(reverse('update_cart', args=[item.id]), {'quantity': 2})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        # Verify item was not deleted
        self.assertEqual(cart.items.count(), 1)

    def test_guest_decrease_to_zero_removes_item(self):
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 2})
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_id=session_key)
        item = cart.items.get(product=self.product1)

        # Setting quantity <= 0 removes it
        self.client.post(reverse('update_cart', args=[item.id]), {'quantity': 0})
        self.assertEqual(cart.items.count(), 0)

    def test_guest_remove_item(self):
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 1})
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_id=session_key)
        item = cart.items.get(product=self.product1)

        response = self.client.post(reverse('remove_from_cart', args=[item.id]))
        self.assertRedirects(response, reverse('cart'))
        self.assertFalse(CartItem.objects.filter(id=item.id).exists())

    def test_cart_total_with_multiple_products_and_quantities(self):
        # Add 2 of product1 ($20.00) = $40.00
        self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 2})
        # Add 3 of product2 ($35.50) = $106.50
        self.client.post(reverse('add_to_cart', args=[self.product2.id]), {'qty': 3})

        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_id=session_key)
        self.assertEqual(cart.items.count(), 2)

        response = self.client.get(reverse('cart'))
        expected_total = (Decimal('20.00') * 2) + (Decimal('35.50') * 3)  # 40.00 + 106.50 = 146.50
        self.assertEqual(response.context['subtotal'], expected_total)
        self.assertEqual(response.context['total'], expected_total)
        self.assertEqual(response.context['cart_count'], 5)

    # ---------------------------------------------------------
    # Logged-in cart tests (User-based)
    # ---------------------------------------------------------

    def test_authenticated_user_cart_workflow(self):
        self.client.login(username='cartuser', password='Password123!')

        # Add item
        response = self.client.post(reverse('add_to_cart', args=[self.product1.id]), {'qty': 2})
        self.assertEqual(response.status_code, 302)

        # Cart should belong to user
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.product, self.product1)
        self.assertEqual(item.quantity, 2)

        # View cart
        view_res = self.client.get(reverse('cart'))
        self.assertEqual(view_res.status_code, 200)
        self.assertEqual(view_res.context['cart_count'], 2)
        self.assertEqual(view_res.context['total'], Decimal('40.00'))

        # Increase quantity
        self.client.post(reverse('update_cart', args=[item.id]), {'quantity': 4})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)
        self.assertEqual(item.total_price, Decimal('80.00'))

        # Decrease quantity
        self.client.post(reverse('update_cart', args=[item.id]), {'quantity': 1})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

        # Remove item
        self.client.post(reverse('remove_from_cart', args=[item.id]))
        self.assertEqual(cart.items.count(), 0)

    def test_cart_item_isolation_between_users(self):
        other_user = User.objects.create_user(
            username='otheruser',
            password='Password123!',
        )
        other_cart = Cart.objects.create(user=other_user)
        other_item = CartItem.objects.create(
            cart=other_cart,
            product=self.product1,
            quantity=2,
        )

        # Log in as self.user and attempt to update other_user's cart item
        self.client.login(username='cartuser', password='Password123!')
        response = self.client.post(reverse('update_cart', args=[other_item.id]), {'quantity': 10})
        # Scoped get_object_or_404 should return 404
        self.assertEqual(response.status_code, 404)
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 2)
