from django.shortcuts import render, get_object_or_404
from .models import Category
from products.models import Product

def category_detail_view(request, slug):
    # Try to fetch the category from DB if it exists
    category = None
    products = []
    try:
        category = Category.objects.get(slug=slug)
        products = category.products.all()
    except Category.DoesNotExist:
        # For the demo if the DB is empty, just pass the slug
        pass

    context = {
        'category': category,
        'slug': slug,
        'products': products,
    }
    return render(request, 'categories/category_detail.html', context)
