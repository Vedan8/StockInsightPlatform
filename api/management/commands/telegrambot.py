import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from django.core.management.base import BaseCommand
from api.models import Prediction, TelegramUser
from api.utils import fetch_stock_data, generate_prediction, create_charts
from django.contrib.auth.models import User

BOT_TOKEN = os.environ.get("BOT_TOKEN")


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **kwargs):
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            username = update.effective_user.username

            tg_user, created = TelegramUser.objects.get_or_create(chat_id=chat_id)
            tg_user.username = username
            tg_user.save()

            if created:
                msg = f"Hi @{username}! You’ve been registered."
            else:
                msg = f"Welcome back, @{username}!"

            await update.message.reply_text(msg)

        async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if len(context.args) != 1:
                await update.message.reply_text("Usage: /predict <TICKER>")
                return

            ticker = context.args[0].upper()
            chat_id = update.effective_chat.id

            try:
                tg_user = TelegramUser.objects.get(chat_id=chat_id)
                user = tg_user.user
            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
                return

            try:
                df = fetch_stock_data(ticker)
                next_price, scaler = generate_prediction(df)
                chart1, chart2 = create_charts(df, next_price, scaler)

                prediction = Prediction.objects.create(
                    user=user,
                    ticker=ticker,
                    predicted_price=round(next_price, 2),
                    metrics={},
                    chart1_path=chart1,
                    chart2_path=chart2
                )

                await update.message.reply_text(
                    f"Prediction for {ticker}: ₹{round(next_price, 2)}"
                )
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{chart1}", "rb"))
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{chart2}", "rb"))

            except Exception as e:
                await update.message.reply_text(f"Error: {str(e)}")

        async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id

            try:
                tg_user = TelegramUser.objects.get(chat_id=chat_id)
                user = tg_user.user
                pred = Prediction.objects.filter(user=user).latest("created_at")

                await update.message.reply_text(
                    f"Latest: {pred.ticker} → ₹{pred.predicted_price} at {pred.created_at}"
                )
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{pred.chart1_path}", "rb"))
                await context.bot.send_photo(chat_id=chat_id, photo=open(f"static/{pred.chart2_path}", "rb"))

            except TelegramUser.DoesNotExist:
                await update.message.reply_text("Use /start to link your account.")
            except Prediction.DoesNotExist:
                await update.message.reply_text("No predictions yet.")

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("predict", predict))
        application.add_handler(CommandHandler("latest", latest))

        self.stdout.write("Telegram bot started")
        application.run_polling()
