from django.contrib import admin
from django.urls import path, include
from api.views import health_check,dashboard,login_page,register_page,create_checkout_session,stripe_webhook,payment_cancel,web_payment_success,telegram_payment_success,telegram_checkout
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("register/", register_page, name="register"),
    path("login/", login_page, name="login"),
    path('api/v1/', include('api.urls')),
    path('healthz/', health_check, name='healthz'),
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path("webhook/", stripe_webhook, name="stripe-webhook"), 
    path("success/", web_payment_success, name="payment_success"),
    path("tg/success/<str:uidb64>/", telegram_payment_success, name="telegram_success"),
    path("cancel/", payment_cancel, name="payment_cancel"),
    path("telegram-checkout/<uidb64>/", telegram_checkout, name="telegram_checkout"),
    path("", dashboard, name="dashboard"),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
]