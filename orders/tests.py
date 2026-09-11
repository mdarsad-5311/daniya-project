import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from products.models import Product
from categories.models import Category
from orders.models import Order, OrderItem
from accounts.models import NewsletterSubscriber
from cart.models import Cart, CartItem


def get_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='green')
    image.save(file, 'JPEG')
    file.seek(0)
    return SimpleUploadedFile('test_img.jpg', file.read(), content_type='image/jpeg')


class AdminSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='password123',
            email='regular@example.com'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='password123',
            email='staff@example.com',
            is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='adminuser',
            password='password123',
            email='admin@example.com'
        )

    def test_anonymous_user_redirected(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_regular_user_cannot_access_admin(self):
        self.client.login(username='regularuser', password='password123')
        response = self.client.get('/admin/')
        # Django admin redirects non-staff users back to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_staff_user_can_access_admin(self):
        self.client.login(username='staffuser', password='password123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_admin(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)


class ProductsAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='adminuser',
            password='password123',
            email='admin@example.com'
        )
        self.client.login(username='adminuser', password='password123')
        self.category = Category.objects.create(name='Skincare', slug='skincare')
        self.product = Product.objects.create(
            category=self.category,
            name='Hydrating Serum',
            slug='hydrating-serum',
            description='A rich hydrating serum.',
            price=29.99,
            original_price=39.99,
            best_seller=True,
            image=get_test_image()
        )

    def test_product_changelist(self):
        response = self.client.get(reverse('admin:products_product_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hydrating Serum')
        self.assertContains(response, 'Skincare')
        self.assertContains(response, '29.99')
        # Check image preview rendered
        self.assertContains(response, '<img src=')

    def test_product_change_form(self):
        response = self.client.get(reverse('admin:products_product_change', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current Image Preview')
        self.assertContains(response, 'Basic Information')
        self.assertContains(response, 'Pricing')

    def test_product_add_via_admin(self):
        test_img = get_test_image()
        data = {
            'name': 'Glow Cleanser',
            'slug': 'glow-cleanser',
            'category': self.category.id,
            'description': 'Gentle glowing face cleanser',
            'price': '18.50',
            'original_price': '22.00',
            'best_seller': True,
            'image': test_img,
        }
        response = self.client.post(reverse('admin:products_product_add'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.filter(slug='glow-cleanser').exists())
        new_prod = Product.objects.get(slug='glow-cleanser')
        self.assertEqual(float(new_prod.price), 18.50)
        self.assertTrue(new_prod.best_seller)

    def test_product_delete_via_admin(self):
        response = self.client.post(
            reverse('admin:products_product_delete', args=[self.product.id]),
            {'post': 'yes'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())


class CategoriesAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='adminuser',
            password='password123',
            email='admin@example.com'
        )
        self.client.login(username='adminuser', password='password123')
        self.category = Category.objects.create(name='Body Care', slug='body-care')
        Product.objects.create(
            category=self.category,
            name='Body Lotion',
            slug='body-lotion',
            description='Nourishing lotion',
            price=15.00,
            image=get_test_image()
        )

    def test_category_changelist_and_product_count(self):
        response = self.client.get(reverse('admin:categories_category_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Body Care')
        # product_count is 1
        self.assertContains(response, '1')

    def test_category_add_via_admin(self):
        data = {
            'name': 'Hair Care',
            'slug': 'hair-care',
            'description': 'Shampoos and conditioners',
        }
        response = self.client.post(reverse('admin:categories_category_add'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(slug='hair-care').exists())


class OrdersAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='adminuser',
            password='password123',
            email='admin@example.com'
        )
        self.client.login(username='adminuser', password='password123')
        self.customer = User.objects.create_user(
            username='customer1',
            password='password123',
            email='customer@example.com'
        )
        self.category = Category.objects.create(name='Face Care', slug='face-care')
        self.product = Product.objects.create(
            category=self.category,
            name='Moisturizer',
            slug='moisturizer',
            description='Moisturizer description',
            price=25.00,
            image=get_test_image()
        )
        self.order = Order.objects.create(
            user=self.customer,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            address='123 Main St',
            city='Springfield',
            postal_code='12345',
            paid=False,
            status='Pending'
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=25.00,
            quantity=2
        )

    def test_order_changelist(self):
        response = self.client.get(reverse('admin:orders_order_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'john@example.com')
        self.assertContains(response, '$50.00')
        self.assertContains(response, 'Pending')

    def test_order_change_view(self):
        response = self.client.get(reverse('admin:orders_order_change', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order Summary')
        self.assertContains(response, 'Customer Information')
        self.assertContains(response, 'Shipping Address')
        self.assertContains(response, 'Moisturizer')
        self.assertContains(response, '$50.00')

    def test_order_status_update(self):
        data = {
            'user': self.customer.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'address': '123 Main St',
            'city': 'Springfield',
            'postal_code': '12345',
            'status': 'Shipped',
            'paid': True,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': str(self.order_item.id),
            'items-0-order': str(self.order.id),
        }
        response = self.client.post(reverse('admin:orders_order_change', args=[self.order.id]), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'Shipped')
        self.assertTrue(self.order.paid)

    def test_order_item_changelist(self):
        response = self.client.get(reverse('admin:orders_orderitem_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Moisturizer')
        self.assertContains(response, '$50.00')


class AccountsAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='adminuser',
            password='password123',
            email='admin@example.com'
        )
        self.client.login(username='adminuser', password='password123')
        self.subscriber = NewsletterSubscriber.objects.create(email='sub@example.com')

    def test_users_admin(self):
        response = self.client.get(reverse('admin:auth_user_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'adminuser')
        # Confirm password hash is not exposed directly in change list
        self.assertNotContains(response, 'pbkdf2_')

    def test_newsletter_admin(self):
        response = self.client.get(reverse('admin:accounts_newslettersubscriber_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sub@example.com')

    def test_newsletter_delete(self):
        response = self.client.post(
            reverse('admin:accounts_newslettersubscriber_delete', args=[self.subscriber.id]),
            {'post': 'yes'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NewsletterSubscriber.objects.filter(id=self.subscriber.id).exists())


class Phase3RegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Face', slug='face')
        self.product = Product.objects.create(
            category=self.category,
            name='Daily Cream',
            slug='daily-cream',
            description='Daily moisturizer',
            price=20.00,
            best_seller=True,
            image=get_test_image()
        )

    def test_storefront_pages(self):
        # Homepage
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        # Products list / shop
        res = self.client.get(reverse('shop'))
        self.assertEqual(res.status_code, 200)
        # Product detail
        res = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(res.status_code, 200)
        # Category detail
        res = self.client.get(reverse('category_detail', args=[self.category.slug]))
        self.assertEqual(res.status_code, 200)
        # Cart
        res = self.client.get(reverse('cart'))
        self.assertEqual(res.status_code, 200)
        # Checkout (redirects to login if not logged in)
        res = self.client.get(reverse('checkout'))
        self.assertEqual(res.status_code, 302)
        # Log in customer
        user = User.objects.create_user(username='reguser', password='password123')
        self.client.login(username='reguser', password='password123')
        res = self.client.get(reverse('profile'))
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse('my_orders'))
        self.assertEqual(res.status_code, 200)


from decimal import Decimal


class CheckoutWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='shopper',
            password='TestPassword123!',
            email='shopper@example.com',
            first_name='Jane',
            last_name='Doe',
        )
        self.category = Category.objects.create(name='Skincare', slug='skincare')
        self.product1 = Product.objects.create(
            category=self.category,
            name='Hydrating Cream',
            slug='hydrating-cream',
            description='Daily hydration.',
            price=Decimal('25.00'),
        )
        self.product2 = Product.objects.create(
            category=self.category,
            name='Facial Mist',
            slug='facial-mist',
            description='Refreshing mist.',
            price=Decimal('15.50'),
        )
        self.checkout_payload = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'shopper@example.com',
            'address': '123 Garden Avenue',
            'city': 'Lahore',
            'postal_code': '54000',
        }

    def test_unauthenticated_checkout_redirects_to_login(self):
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_empty_cart_cannot_checkout_get_or_post(self):
        self.client.login(username='shopper', password='TestPassword123!')
        
        # GET empty cart
        get_res = self.client.get(reverse('checkout'))
        self.assertRedirects(get_res, reverse('cart'))

        # POST empty cart
        post_res = self.client.post(reverse('checkout'), self.checkout_payload)
        self.assertRedirects(post_res, reverse('cart'))
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_valid_checkout_creates_order_and_snapshots_order_items(self):
        self.client.login(username='shopper', password='TestPassword123!')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=cart, product=self.product2, quantity=1)

        response = self.client.post(reverse('checkout'), self.checkout_payload)
        
        # Verify order created
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        order = Order.objects.get(user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('payment:create', args=[order.id]))

        self.assertEqual(order.first_name, 'Jane')
        self.assertEqual(order.last_name, 'Doe')
        self.assertEqual(order.email, 'shopper@example.com')
        self.assertEqual(order.address, '123 Garden Avenue')
        self.assertEqual(order.city, 'Lahore')
        self.assertEqual(order.postal_code, '54000')
        self.assertEqual(order.payment_status, 'pending')
        self.assertFalse(order.paid)
        self.assertEqual(order.status, 'Pending')

        # Verify OrderItems snapshot product price and quantity
        order_items = order.items.order_by('id')
        self.assertEqual(order_items.count(), 2)
        item1 = order_items[0]
        self.assertEqual(item1.product, self.product1)
        self.assertEqual(item1.price, Decimal('25.00'))
        self.assertEqual(item1.quantity, 2)
        self.assertEqual(item1.get_cost(), Decimal('50.00'))

        item2 = order_items[1]
        self.assertEqual(item2.product, self.product2)
        self.assertEqual(item2.price, Decimal('15.50'))
        self.assertEqual(item2.quantity, 1)
        self.assertEqual(item2.get_cost(), Decimal('15.50'))

        expected_total = Decimal('65.50')
        self.assertEqual(order.get_total_cost(), expected_total)

    def test_checkout_prefills_authenticated_user_information(self):
        self.client.login(username='shopper', password='TestPassword123!')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Jane"')
        self.assertContains(response, 'value="Doe"')
        self.assertContains(response, 'value="shopper@example.com"')

    def test_confirmation_page_access_control(self):
        self.client.login(username='shopper', password='TestPassword123!')
        order = Order.objects.create(
            user=self.user,
            first_name='Jane',
            last_name='Doe',
            email='shopper@example.com',
            address='123 Road',
            city='City',
            postal_code='10000',
            paid=False,
            payment_status='pending',
        )

        # Pending unpaid order redirects to payment:create
        response = self.client.get(reverse('order_confirmation', args=[order.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('payment:create', args=[order.id]))

        # Paid order displays confirmation successfully
        order.paid = True
        order.payment_status = 'paid'
        order.save()

        paid_response = self.client.get(reverse('order_confirmation', args=[order.id]))
        self.assertEqual(paid_response.status_code, 200)
        self.assertContains(paid_response, f'Order #{order.id}')

    def test_order_detail_view_idor_protection(self):
        other_user = User.objects.create_user(username='other_shopper', password='Password123!')
        order = Order.objects.create(
            user=other_user,
            first_name='Other',
            last_name='Person',
            email='other@example.com',
            address='456 Street',
            city='Town',
            postal_code='20000',
            paid=True,
            payment_status='paid',
        )

        # Logged in as self.user trying to view other_user's order
        self.client.login(username='shopper', password='TestPassword123!')
        response = self.client.get(reverse('order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 404)



