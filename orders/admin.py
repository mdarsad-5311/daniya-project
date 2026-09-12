from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product', 'product_name', 'price', 'quantity', 'item_total')
    readonly_fields = ('product', 'product_name', 'price', 'quantity', 'item_total')

    def item_total(self, obj):
        if obj.pk:
            return f"₹{obj.get_cost():.2f}"
        return "-"
    item_total.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_name',
        'email',
        'phone',
        'user',
        'total_amount_display',
        'status',
        'paid',
        'created_at',
    )
    list_editable = ('status', 'paid')
    list_filter = ('status', 'paid', 'payment_status', 'created_at')
    search_fields = (
        'id',
        'first_name',
        'last_name',
        'email',
        'phone',
        'address',
        'city',
        'postal_code',
        'user__username',
        'user__email',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'total_amount_display',
        'shipping_cost', 'payment_status', 'razorpay_order_id', 'razorpay_payment_id',
    )
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Summary', {
            'fields': (
                'id', 'status', 'paid', 'payment_status', 'razorpay_order_id',
                'razorpay_payment_id', 'shipping_cost', 'total_amount_display',
            )
        }),
        ('Customer Information', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items__product')

    def customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "-"
    customer_name.short_description = "Customer"

    def total_amount_display(self, obj):
        return f"₹{obj.get_total_cost():.2f}"
    total_amount_display.short_description = "Total Amount"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'product_name', 'price', 'quantity', 'item_total')
    readonly_fields = ('order', 'product', 'product_name', 'price', 'quantity', 'item_total')
    search_fields = ('order__id', 'product__name', 'product_name')
    ordering = ('-id',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'order__user', 'product')

    def item_total(self, obj):
        return f"₹{obj.get_cost():.2f}"
    item_total.short_description = "Subtotal"
