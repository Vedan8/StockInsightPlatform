from django.contrib import admin
from django.urls import path, include
from api.views import health_check,dashboard,login_page,register_page
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path("register/", register_page, name="register"),
    path("login/", login_page, name="login"),
    path('api/v1/', include('api.urls')),
    path('healthz/', health_check, name='healthz'),
    path("", dashboard, name="dashboard"),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
