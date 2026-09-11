from django.urls import path
from . import views

urlpatterns = [
    # Explicitly mapping React frontend routes to the dynamic category view
    path('creams/', views.category_detail_view, {'slug': 'creams'}, name='creams'),
    path('soaps/', views.category_detail_view, {'slug': 'soaps'}, name='soaps'),
    path('<slug:slug>/', views.category_detail_view, name='category_detail'),
]
