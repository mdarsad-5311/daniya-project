from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('shop/', views.shop_view, name='shop'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<slug:slug>/review/', views.review_create_view, name='review_create'),
]
