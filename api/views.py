from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import RegisterSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .predictor import fetch_stock_data, generate_prediction, create_charts
from .serializers import PredictionSerializer
from .models import Prediction,Membership
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@api_view(['GET'])
def health_check(request):
    return Response({"status": "ok"})


class PredictView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticker = request.data.get("ticker")
        if not ticker:
            return Response({"error": "Ticker is required"}, status=400)

        # Get or create membership
        membership, _ = Membership.objects.get_or_create(user=request.user)

        # Enforce free daily limit
        if not membership.is_paid:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_predictions = Prediction.objects.filter(
                user=request.user,
                created_at__gte=today_start
            ).count()

            if today_predictions >= 5:
                return Response({
                    "error": "Free tier daily limit (5 predictions) reached. Upgrade for unlimited access."
                }, status=403)

        try:
            df = fetch_stock_data(ticker)
            next_price, scaler = generate_prediction(df)
            chart1, chart2 = create_charts(df, next_price, scaler,ticker=ticker)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        Prediction.objects.create(
            user=request.user,
            ticker=ticker.upper(),
            predicted_price=round(next_price, 2),
            metrics={},
            chart1_path=chart1,
            chart2_path=chart2,
        )

        return Response({
            "ticker": ticker.upper(),
            "next_day_price": round(next_price, 2),
            "plot_urls": [chart1, chart2]
        })


class PredictionListView(generics.ListAPIView):
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Prediction.objects.filter(user=self.request.user)
        ticker = self.request.query_params.get("ticker")
        if ticker:
            qs = qs.filter(ticker__iexact=ticker)
        return qs.order_by("-created_at")



@login_required
def dashboard(request):
    return render(request, "dashboard.html")

def login_page(request):
    return render(request, "login.html")

def register_page(request):
    return render(request, "register.html")
