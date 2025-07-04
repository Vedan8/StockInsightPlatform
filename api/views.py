from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, PredictionSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .models import Prediction, Membership, TelegramUser
from .predictor import fetch_stock_data, generate_prediction, create_charts
import stripe
import os

stripe.api_key = settings.STRIPE_SECRET_KEY

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

@api_view(['GET'])
def health_check(request):
    return Response({"status": "ok"})

# 🔐 API view with JWT auth
class PredictView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticker = request.data.get("ticker")
        if not ticker:
            return Response({"error": "Ticker is required"}, status=400)

        membership, _ = Membership.objects.get_or_create(user=request.user)

        if not membership.is_paid:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            count = Prediction.objects.filter(user=request.user, created_at__gte=today_start).count()
            if count >= 5:
                return Response({"error": "Free tier daily limit (5 predictions) reached. Upgrade for unlimited access."}, status=403)

        try:
            df = fetch_stock_data(ticker)
            next_price, scaler = generate_prediction(df)
            chart1, chart2 = create_charts(df, next_price, scaler, ticker=ticker)
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

# 🧑 Session-pro

@login_required
def dashboard(request):
    prediction = None
    chart1_url = chart2_url = None
    user = request.user

    if request.method == "POST":
        ticker = request.POST.get("ticker", "").strip()

        if ticker:
            membership, _ = Membership.objects.get_or_create(user=user)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_predictions = Prediction.objects.filter(user=user, created_at__gte=today_start).count()

            if not membership.is_paid and today_predictions >= 5:
                return render(request, "dashboard.html", {
                    "error": "Free tier daily limit (5 predictions) reached. Upgrade to continue.",
                    "past_predictions": Prediction.objects.filter(user=user).order_by("-created_at")
                })

            try:
                df = fetch_stock_data(ticker)
                next_price, scaler = generate_prediction(df)
                chart1, chart2 = create_charts(df, next_price, scaler, ticker=ticker)

                prediction = Prediction.objects.create(
                    user=user,
                    ticker=ticker.upper(),
                    predicted_price=round(next_price, 2),
                    metrics={},
                    chart1_path=chart1,
                    chart2_path=chart2,
                )
                chart1_url = chart1
                chart2_url = chart2
            except Exception as e:
                return render(request, "dashboard.html", {
                    "error": f"Error: {str(e)}",
                    "past_predictions": Prediction.objects.filter(user=user).order_by("-created_at")
                })

    return render(request, "dashboard.html", {
        "prediction": prediction,
        "chart1_url": chart1_url,
        "chart2_url": chart2_url,
        "past_predictions": Prediction.objects.filter(user=user).order_by("-created_at"),
        "is_paid": Membership.objects.filter(user=request.user, is_paid=True).exists(),
    })


def login_page(request):
    return render(request, "login.html")

def register_page(request):
    return render(request, "register.html")

@login_required
def web_payment_success(request):
    print("web payment success")
    user = request.user
    membership, created = Membership.objects.get_or_create(user=user)
    membership.is_paid = True
    membership.save()

    return render(request, "payment_success.html", {
        "message": "Web: Payment successful. You are now a premium member!"
    })


def telegram_payment_success(request, uidb64):
    print("telegram payment success")
    print("Received UIDB64:", uidb64)
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        TelegramUser.objects.filter(user=user).update(is_paid=True)
        return redirect(f"https://web.telegram.org/k/#{settings.BOT_USERNAME}")
    except Exception as e:
        print("Error in telegram_payment_success:", e)
        return redirect("/")

def payment_cancel(request):
    return render(request, "payment_cancel.html")

@login_required
def create_checkout_session(request):
    print("web checkout")
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Premium Membership'},
                'unit_amount': 49900,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/success/'),
        cancel_url=request.build_absolute_uri('/cancel/'),
        metadata={'user_id': str(request.user.id)}
    )
    return redirect(session.url, code=303)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not sig_header or not endpoint_secret:
        return JsonResponse({'error': 'Missing signature or secret'}, status=400)

    try:
        stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    

    return JsonResponse({'status': 'ok'})


def telegram_checkout(request, uidb64):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=int(uid))
    except Exception as e:
        return HttpResponse(f"Invalid link: {str(e)}", status=400)

    print("telegram checkout")
    success_url = request.build_absolute_uri(f'/tg/success/{uidb64}/')

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Premium Membership (Telegram)'},
                'unit_amount': 49900,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=request.build_absolute_uri('/cancel/'),
        metadata={'user_id': user.id}
    )
    return redirect(session.url)
