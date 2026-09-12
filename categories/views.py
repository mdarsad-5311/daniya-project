from django.shortcuts import render, get_object_or_404
from .models import Category
from products.models import Product

def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True)

    context = {
        'category': category,
        'slug': slug,
        'products': products,
    }
    return render(request, 'categories/category_detail.html', context)

