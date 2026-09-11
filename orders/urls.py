from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('confirmation/<int:order_id>/', views.order_confirmation_view, name='order_confirmation'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),
]
