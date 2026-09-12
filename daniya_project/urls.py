from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from categories import views as category_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('payment/', include(('payment.urls', 'payment'), namespace='payment')),
    path('wishlist/', include('wishlist.urls')),
    path('categories/', include('categories.urls')),
    path('creams/', category_views.category_detail_view, {'slug': 'creams'}, name='creams'),
    path('soaps/', category_views.category_detail_view, {'slug': 'soaps'}, name='soaps'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

