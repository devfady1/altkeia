from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('accounts.urls')),
    path('dashboard/', include('tables.urls')),
    path('orders/', include('orders.urls')),
    path('products/', include('products.urls')),
    path('activities/', include('activities.urls')),
    path('queue/', include('queue_system.urls')),
    path('payments/', include('payments.urls')),
    path('reports/', include('reports.urls')),
    path('qr/', include('qr_menu.urls')),
    path('sessions/', include('sessions.urls')),
    # API
    path('api/', include('orders.api_urls')),
    path('api/', include('tables.api_urls')),
    path('api/', include('activities.api_urls')),
    path('api/', include('queue_system.api_urls')),
    path('api/', include('sessions.api_urls')),
    path('api/', include('products.api_urls')),
    path('api/', include('payments.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
