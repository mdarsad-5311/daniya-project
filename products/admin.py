from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Review, ContactMessage


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'image_preview',
        'name',
        'category',
        'price',
        'original_price',
        'stock',
        'is_active',
        'best_seller',
        'slug',
        'created_at',
    )
    list_editable = ('price', 'original_price', 'stock', 'is_active', 'best_seller')
    list_filter = ('category', 'is_active', 'best_seller', 'created_at')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'image_preview_large')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'original_price', 'stock', 'is_active')
        }),
        ('Media', {
            'fields': ('image', 'image_preview_large')
        }),
        ('Status & Timestamps', {
            'fields': ('best_seller', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px;" alt="{}" />',
                obj.image.url,
                obj.name
            )
        return "-"
    image_preview.short_description = "Image"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; object-fit: contain; border-radius: 8px; border: 1px solid #ddd;" alt="{}" />',
                obj.image.url,
                obj.name
            )
        return "No image uploaded"
    image_preview_large.short_description = "Current Image Preview"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    ordering = ('-created_at',)
