from django.contrib import admin
from django.utils.html import format_html
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'slug', 'product_count')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    def get_queryset(self, request):
        from django.db.models import Count
        return super().get_queryset(request).annotate(_product_count=Count('products'))

    def product_count(self, obj):
        return getattr(obj, '_product_count', obj.products.count())
    product_count.short_description = "Products"
    product_count.admin_order_field = '_product_count'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px;" alt="{}" />',
                obj.image.url,
                obj.name
            )
        return "-"
    image_preview.short_description = "Image"

