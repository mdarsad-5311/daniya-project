from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'item_total')
    fields = ('product', 'quantity', 'item_total')

    def item_total(self, obj):
        if obj.pk:
            return f"${obj.total_price:.2f}"
        return "-"
    item_total.short_description = "Subtotal"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_id', 'items_count', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'session_id')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'total_price')
    inlines = [CartItemInline]

    def items_count(self, obj):
        return sum(item.quantity for item in obj.items.all())
    items_count.short_description = "Total Items"

    def total_price(self, obj):
        total = sum(item.total_price for item in obj.items.all())
        return f"${total:.2f}"
    total_price.short_description = "Cart Total"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'item_total')
    search_fields = ('product__name', 'cart__id')
    readonly_fields = ('cart', 'product', 'quantity', 'item_total')

    def item_total(self, obj):
        return f"${obj.total_price:.2f}"
    item_total.short_description = "Subtotal"

