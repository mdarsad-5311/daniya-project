from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>/', views.category_detail_view, name='category_detail'),
]
