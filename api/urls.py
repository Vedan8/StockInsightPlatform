from django.urls import path
from .views import RegisterView, PredictView, PredictionListView
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token"),
    path("predict/", PredictView.as_view(), name="predict"),           # ✅ make sure this is here
    path("predictions/", PredictionListView.as_view(), name="predictions"),  # ✅ and this too
]
