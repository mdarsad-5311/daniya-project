from django.urls import path

from . import views


app_name = 'payment'

urlpatterns = [
    path('', views.payment_start_view, name='start'),
    path('create/<int:order_id>/', views.create_razorpay_order_view, name='create'),
    path('verify/<int:order_id>/', views.verify_payment_view, name='verify'),
    path('webhook/', views.webhook_view, name='webhook'),
]