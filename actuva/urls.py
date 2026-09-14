from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('panel/', views.dashboard, name='dashboard'),
    path('anamnesis/', include('anamnesis.urls')),
    path('admin/', admin.site.urls),
    path('cuentas/', include('accounts.urls')),
    path('chat/', include('chat.urls')),
    path('casos/', include('cases.urls')),
    path('estadisticas/', include('stats.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
