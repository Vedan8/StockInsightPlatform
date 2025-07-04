from django.db import models
from django.contrib.auth.models import User

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=10)
    predicted_price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField(default=dict)  # optional: mse, rmse, r2
    chart1_path = models.CharField(max_length=255)
    chart2_path = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.ticker} - {self.predicted_price:.2f} on {self.created_at.date()}"


class TelegramUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return self.username or f"Chat {self.chat_id}"


class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({'Paid' if self.is_paid else 'Free'})"

