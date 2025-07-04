import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from django.core.management.base import BaseCommand
from api.models import Prediction, TelegramUser
from api.predictor import fetch_stock_data, generate_prediction, create_charts
from asgiref.sync import sync_to_async
from django.db.models import Max
import httpx
from django.contrib.auth.models import User
from django.conf import settings
from datetime import datetime
from django.utils.timezone import make_aware
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

BOT_TOKEN = os.environ.get("BOT_TOKEN")


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **kwargs):
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        application.bot.request._client.timeout = httpx.Timeout(30.0)

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            username = update.effective_user.username 
            user, _ = await sync_to_async(User.objects.get_or_create)(username=username)
            print("----",user.id,"----",user.username)
            telegram_user, created = await sync_to_async(TelegramUser.objects.get_or_create)(
                user=user,
                username=username,
                chat_id=chat_id
            )
            print("----",telegram_user.username,"----",telegram_user.chat_id)
            if not created and telegram_user.username != username:
                telegram_user.username = username
                await sync_to_async(telegram_user.save)()
            msg = f"Hi @{username}! You've been registered."
            await update.message.reply_text(msg)        

        async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if len(context.args) != 1:
                await update.message.reply_text("Usage: /predict <TICKER>")
                return

            ticker = context.args[0].upper()
            chat_id = update.effective_chat.id
            print("-----------", ticker, "->", chat_id, "-----------")

            try:
                tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
                user = await sync_to_async(lambda: tg_user.user)()
            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
                return

            print("----", tg_user.username, "---", ticker)

            try:
                # Get start of today in aware datetime
                today_start = make_aware(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

                # Count predictions made today by this user
                prediction_count_today = await sync_to_async(Prediction.objects.filter(
                    user=user, created_at__gte=today_start
                ).count)()

                if not tg_user.is_paid and prediction_count_today >= 5:
                    await update.message.reply_text("Daily limit reached (5 predictions/day). Upgrade to premium for unlimited predictions.")
                    return

                df = fetch_stock_data(ticker)
                next_price, scaler = generate_prediction(df)
                chart1, chart2 = create_charts(df, next_price, scaler,ticker=ticker)

                await sync_to_async(Prediction.objects.create)(
                    user=user,
                    ticker=ticker,
                    predicted_price=round(next_price, 2),
                    metrics={},
                    chart1_path=chart1,
                    chart2_path=chart2
                )

                await update.message.reply_text(f"Prediction for {ticker}: ₹{round(next_price, 2)}")

                chart1_path = os.path.join(settings.BASE_DIR, chart1)
                chart2_path = os.path.join(settings.BASE_DIR, chart2)

                with open(chart1_path, "rb") as f1:
                    await context.bot.send_photo(chat_id=chat_id, photo=f1)
                with open(chart2_path, "rb") as f2:
                    await context.bot.send_photo(chat_id=chat_id, photo=f2)

            except Exception as e:
                await update.message.reply_text(f"Error: {str(e)}")

        async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id

            try:
                tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
                user = await sync_to_async(lambda: tg_user.user)()

                # Get latest prediction safely
                max_time = await sync_to_async(Prediction.objects.filter(user=user).aggregate)(Max("created_at"))
                latest_pred = await sync_to_async(Prediction.objects.get)(
                    user=user, created_at=max_time["created_at__max"]
                )

                await update.message.reply_text(
                    f"Latest: {latest_pred.ticker} → ${latest_pred.predicted_price} at {latest_pred.created_at}"
                )

            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
            except Prediction.DoesNotExist:
                await update.message.reply_text("No predictions yet.")
        
        async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            try:
                tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
                user = await sync_to_async(lambda: tg_user.user)()
                uid = urlsafe_base64_encode(force_bytes(user.id))
                url = f"{settings.SITE_URL}/telegram-checkout/{uid}/"
                await update.message.reply_text(f"🚀 Upgrade to premium: {url}")
            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to register first.")

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("predict", predict))
        application.add_handler(CommandHandler("latest", latest))
        application.add_handler(CommandHandler("upgrade", upgrade))


        self.stdout.write("Telegram bot started")
        application.run_polling()
