from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Product, Category
from .forms import ReviewForm, ContactForm

def home_view(request):
    best_sellers = Product.objects.filter(best_seller=True, is_active=True)[:4]
    categories = Category.objects.all()[:3]
    
    context = {
        'best_sellers': best_sellers,
        'categories': categories,
    }
    return render(request, 'home.html', context)

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! Your message has been sent successfully.')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})

from .models import Product

def product_detail_view(request, slug):
    # Retrieve product or 404
    product = get_object_or_404(Product, slug=slug)
    # Get up to 4 related products in the same category
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    # Check if authenticated user has this product in their wishlist
    is_wishlisted = False
    wishlist_item_id = None
    if request.user.is_authenticated:
        from wishlist.models import Wishlist, WishlistItem
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()
            if wishlist_item:
                is_wishlisted = True
                wishlist_item_id = wishlist_item.id
        except Wishlist.DoesNotExist:
            pass

    reviews = product.reviews.select_related('user')
    review_summary = reviews.aggregate(average=Avg('rating'), count=Count('id'))
    existing_review = reviews.filter(user=request.user).first() if request.user.is_authenticated else None
    context = {
        'product': product,
        'related_products': related_products,
        'is_wishlisted': is_wishlisted,
        'wishlist_item_id': wishlist_item_id,
        'reviews': reviews,
        'review_average': review_summary['average'] or 0,
        'review_count': review_summary['count'],
        'review_form': ReviewForm(instance=existing_review),
        'existing_review': existing_review,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
@require_POST
def review_create_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    existing_review = product.reviews.filter(user=request.user).first()
    form = ReviewForm(request.POST, instance=existing_review)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
    return redirect('product_detail', slug=product.slug)


from categories.models import Category
from django.db.models import Q

def shop_view(request):
    products = Product.objects.filter(is_active=True)
    all_categories = Category.objects.all()
    
    # Filtering Logic
    q = request.GET.get('q')
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
        
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        products = products.filter(category__slug__in=selected_categories)
        
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
            
    # Sorting Logic
    sort = request.GET.get('sort', 'featured')
    if sort == 'price-asc':
        products = products.order_by('price')
    elif sort == 'price-desc':
        products = products.order_by('-price')
        
    dummy_fallback = not Product.objects.exists()

    context = {
        'products': products,
        'all_categories': all_categories,
        'selected_categories': selected_categories,
        'dummy_fallback': dummy_fallback,
    }
    return render(request, 'products/shop.html', context)
