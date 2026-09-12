import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from products.models import Product
from categories.models import Category
from wishlist.models import Wishlist, WishlistItem
from cart.models import Cart, CartItem


def get_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='pink')
    image.save(file, 'JPEG')
    file.seek(0)
    return SimpleUploadedFile('test.jpg', file.read(), content_type='image/jpeg')


import shutil
import tempfile
from django.test import override_settings


class WishlistSetupMixin:
    """Shared setUp for wishlist tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._temp_media)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(
            username='user_a', password='password123', email='a@example.com'
        )
        self.user_b = User.objects.create_user(
            username='user_b', password='password123', email='b@example.com'
        )
        self.category = Category.objects.create(name='Skincare', slug='skincare')
        self.product = Product.objects.create(
            category=self.category,
            name='Hydrating Cream',
            slug='hydrating-cream',
            description='A hydrating cream.',
            price=29.99,
            best_seller=True,
            image=get_test_image(),
        )
        self.product2 = Product.objects.create(
            category=self.category,
            name='Rose Toner',
            slug='rose-toner',
            description='A rose toner.',
            price=15.00,
            image=get_test_image(),
        )


# ---------------------------------------------------------------------------
# 1. Wishlist Access Tests
# ---------------------------------------------------------------------------

class WishlistAccessTests(WishlistSetupMixin, TestCase):

    def test_anonymous_redirected_to_login(self):
        """Anonymous users cannot access the wishlist page."""
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_user_can_view_wishlist(self):
        """Authenticated user can access their wishlist page."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Wishlist')


# ---------------------------------------------------------------------------
# 2. Add to Wishlist Tests
# ---------------------------------------------------------------------------

class AddToWishlistTests(WishlistSetupMixin, TestCase):

    def test_anonymous_add_redirects_to_login(self):
        """Anonymous users cannot POST to add_to_wishlist."""
        response = self.client.post(reverse('add_to_wishlist', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_user_can_add_product(self):
        """Authenticated user can add a product to their wishlist."""
        self.client.login(username='user_a', password='password123')
        response = self.client.post(
            reverse('add_to_wishlist', args=[self.product.id]),
            {'next': reverse('wishlist')},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        # Confirm database record created
        self.assertTrue(WishlistItem.objects.filter(
            wishlist__user=self.user_a,
            product=self.product,
        ).exists())

    def test_wishlist_item_created_in_database(self):
        """WishlistItem is actually persisted in the database."""
        self.client.login(username='user_a', password='password123')
        self.assertEqual(WishlistItem.objects.count(), 0)
        self.client.post(reverse('add_to_wishlist', args=[self.product.id]))
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_adding_same_product_twice_no_duplicate(self):
        """Adding the same product twice results in exactly 1 WishlistItem."""
        self.client.login(username='user_a', password='password123')
        self.client.post(reverse('add_to_wishlist', args=[self.product.id]))
        self.client.post(reverse('add_to_wishlist', args=[self.product.id]))
        count = WishlistItem.objects.filter(
            wishlist__user=self.user_a,
            product=self.product,
        ).count()
        self.assertEqual(count, 1)

    def test_add_to_wishlist_get_not_allowed(self):
        """GET requests to add_to_wishlist are rejected (POST only)."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('add_to_wishlist', args=[self.product.id]))
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# 3. Remove from Wishlist Tests
# ---------------------------------------------------------------------------

class RemoveFromWishlistTests(WishlistSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        # Create wishlists and items for both users
        self.wishlist_a, _ = Wishlist.objects.get_or_create(user=self.user_a)
        self.item_a = WishlistItem.objects.create(wishlist=self.wishlist_a, product=self.product)

        self.wishlist_b, _ = Wishlist.objects.get_or_create(user=self.user_b)
        self.item_b = WishlistItem.objects.create(wishlist=self.wishlist_b, product=self.product2)

    def test_user_can_remove_own_item(self):
        """User can remove their own WishlistItem."""
        self.client.login(username='user_a', password='password123')
        response = self.client.post(
            reverse('remove_from_wishlist', args=[self.item_a.id]),
            {'next': reverse('wishlist')},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(WishlistItem.objects.filter(id=self.item_a.id).exists())

    def test_user_b_cannot_remove_user_a_item(self):
        """IDOR protection: User B cannot remove User A's WishlistItem."""
        self.client.login(username='user_b', password='password123')
        response = self.client.post(
            reverse('remove_from_wishlist', args=[self.item_a.id])
        )
        # Must return 404, not 200 or redirect to success
        self.assertEqual(response.status_code, 404)
        # User A's item must still exist
        self.assertTrue(WishlistItem.objects.filter(id=self.item_a.id).exists())

    def test_user_a_cannot_see_user_b_items(self):
        """User A's wishlist view only shows User A's items."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        # User A sees their product
        self.assertContains(response, self.product.name)
        # User A does NOT see User B's product
        self.assertNotContains(response, self.product2.name)

    def test_remove_from_wishlist_get_not_allowed(self):
        """GET requests to remove_from_wishlist are rejected (POST only)."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('remove_from_wishlist', args=[self.item_a.id]))
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# 4. Add to Cart from Wishlist Tests
# ---------------------------------------------------------------------------

class WishlistAddToCartTests(WishlistSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        self.item = WishlistItem.objects.create(wishlist=wishlist, product=self.product)

    def test_add_to_cart_from_wishlist_page(self):
        """Add to Cart from wishlist page uses existing cart logic."""
        response = self.client.post(
            reverse('add_to_cart', args=[self.product.id]),
            {'quantity': '1'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.get(user=self.user_a)
        self.assertTrue(CartItem.objects.filter(cart=cart, product=self.product).exists())

    def test_wishlist_page_has_add_to_cart_form(self):
        """Wishlist page HTML contains add_to_cart forms for each item."""
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/cart/add/{self.product.id}/')


# ---------------------------------------------------------------------------
# 5. Integration / URL Resolution Tests
# ---------------------------------------------------------------------------

class WishlistIntegrationTests(WishlistSetupMixin, TestCase):

    def test_product_detail_wishlist_button_for_anonymous(self):
        """Product detail page shows login link for anonymous users."""
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        # Anonymous: should see login link, not wishlist form
        self.assertContains(response, reverse('login'))

    def test_product_detail_wishlist_button_for_authenticated(self):
        """Product detail page shows add-to-wishlist form for authenticated users."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/wishlist/add/{self.product.id}/')

    def test_product_detail_shows_saved_state_when_wishlisted(self):
        """Product detail shows remove/Saved button when product is already wishlisted."""
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        item = WishlistItem.objects.create(wishlist=wishlist, product=self.product)
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        # Should show remove_from_wishlist form with item id
        self.assertContains(response, f'/wishlist/remove/{item.id}/')
        self.assertContains(response, 'Saved')

    def test_navbar_wishlist_url_resolves(self):
        """Wishlist URL resolves correctly."""
        url = reverse('wishlist')
        self.assertEqual(url, '/wishlist/')

    def test_profile_wishlist_link_present(self):
        """Profile page contains a link to the wishlist."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('wishlist'))

    def test_product_card_wishlist_form_for_authenticated(self):
        """Shop page (which uses product cards) has wishlist forms for authenticated users."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/wishlist/add/')


# ---------------------------------------------------------------------------
# 6. Wishlist Empty State Test
# ---------------------------------------------------------------------------

class WishlistEmptyStateTests(WishlistSetupMixin, TestCase):

    def test_empty_wishlist_shows_empty_state(self):
        """Empty wishlist shows empty state message."""
        self.client.login(username='user_a', password='password123')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your wishlist is empty')

    def test_wishlist_with_items_shows_products(self):
        """Wishlist with items shows product names."""
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, 'Your wishlist is empty')


# ---------------------------------------------------------------------------
# 7. Regression Tests
# ---------------------------------------------------------------------------

class Phase5RegressionTests(WishlistSetupMixin, TestCase):

    def test_cart_still_works(self):
        """Cart page loads."""
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_checkout_requires_login(self):
        """Checkout still requires login."""
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)

    def test_orders_page_requires_login(self):
        """My orders page still requires login."""
        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 302)

    def test_home_page_loads(self):
        """Home page still loads correctly."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_shop_page_loads(self):
        """Shop page still loads correctly."""
        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_loads(self):
        """Product detail still loads."""
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)

    def test_category_detail_loads(self):
        """Category detail still loads."""
        response = self.client.get(reverse('category_detail', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        """Profile still requires login."""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_add_to_cart_still_works(self):
        """Add to cart still works end to end."""
        self.client.login(username='user_a', password='password123')
        response = self.client.post(
            reverse('add_to_cart', args=[self.product.id]),
            {'quantity': '1'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            CartItem.objects.filter(
                cart__user=self.user_a,
                product=self.product
            ).exists()
        )


# ---------------------------------------------------------------------------
# 8. Context Processor & Navbar Count Tests
# ---------------------------------------------------------------------------

class WishlistContextProcessorTests(WishlistSetupMixin, TestCase):

    def test_anonymous_context_processor(self):
        """Anonymous user gets wishlist_count=0 and empty wishlist_product_ids."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wishlist_count'], 0)
        self.assertEqual(response.context['wishlist_product_ids'], set())

    def test_authenticated_context_processor_with_items(self):
        """Authenticated user gets accurate wishlist_count and product IDs."""
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wishlist_count'], 1)
        self.assertIn(self.product.id, response.context['wishlist_product_ids'])

    def test_navbar_displays_wishlist_count_badge(self):
        """Navbar displays the wishlist count badge when items are wishlisted."""
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Check badge is rendered in navbar
        self.assertContains(response, 'title="Wishlist"')
        self.assertContains(response, '1\n        </span>')

    def test_product_card_reflects_wishlisted_state(self):
        """Product card displays active heart icon when product is in wishlist."""
        self.client.login(username='user_a', password='password123')
        wishlist, _ = Wishlist.objects.get_or_create(user=self.user_a)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)

        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'title="In your wishlist"')

