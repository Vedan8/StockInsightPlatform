from django.contrib import admin
from .models import Prediction,TelegramUser,Membership

admin.site.register(Prediction)
admin.site.register(TelegramUser)
admin.site.register(Membership)
# Register your models here.
