import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from django.core.management.base import BaseCommand
from api.models import Prediction, TelegramUser
from api.predictor import fetch_stock_data, generate_prediction, create_charts
from asgiref.sync import sync_to_async
from django.db.models import Max
import httpx
from django.contrib.auth import get_user_model
User = get_user_model()


BOT_TOKEN = os.environ.get("BOT_TOKEN")


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **kwargs):
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        application.bot.request._client.timeout = httpx.Timeout(30.0)

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            username = update.effective_user.username 
            print("-----------",username,"->",chat_id,"-----------")
            user=await sync_to_async(User.objects.get_or_create)(username=username)
            user=await sync_to_async(User.objects.get)(username=username)
            await sync_to_async(TelegramUser.objects.get_or_create)(user=user.id,username=username,chat_id=chat_id)
        
            msg = f"Hi @{username}! You've been registered."
            await update.message.reply_text(msg)        

        async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if len(context.args) != 1:
                await update.message.reply_text("Usage: /predict <TICKER>")
                return

            ticker = context.args[0].upper()
            chat_id = update.effective_chat.id
            print("-----------",ticker,"->",chat_id,"-----------")
            try:
                tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
                user = tg_user.user
            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
                return

            try:
                df = fetch_stock_data(ticker)
                next_price, scaler = generate_prediction(df)
                chart1, chart2 = create_charts(df, next_price, scaler)

                await sync_to_async(Prediction.objects.create)(
                    user=user,
                    ticker=ticker,
                    predicted_price=round(next_price, 2),
                    metrics={},
                    chart1_path=chart1,
                    chart2_path=chart2
                )

                await update.message.reply_text(f"Prediction for {ticker}: ₹{round(next_price, 2)}")
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{chart1}", "rb"))
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{chart2}", "rb"))

            except Exception as e:
                await update.message.reply_text(f"Error: {str(e)}")

        async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id

            try:
                tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
                user = tg_user.user

                # Get latest prediction safely
                max_time = await sync_to_async(Prediction.objects.filter(user=user).aggregate)(Max("created_at"))
                latest_pred = await sync_to_async(Prediction.objects.get)(
                    user=user, created_at=max_time["created_at__max"]
                )

                await update.message.reply_text(
                    f"Latest: {latest_pred.ticker} → ₹{latest_pred.predicted_price} at {latest_pred.created_at}"
                )
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{latest_pred.chart1_path}", "rb"))
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{latest_pred.chart2_path}", "rb"))

            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
            except Prediction.DoesNotExist:
                await update.message.reply_text("No predictions yet.")

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("predict", predict))
        application.add_handler(CommandHandler("latest", latest))

        self.stdout.write("Telegram bot started")
        application.run_polling()
