# 📈 Stock Insight Platform

A full-stack micro-SaaS application for stock price predictions powered by Django, Django REST Framework, Stripe for payments, TailwindCSS for UI, and a Telegram bot for predictions on the go.

---

## 🚀 Features

- 🔐 JWT-based API authentication  
- 📊 ML-based stock predictions with matplotlib chart generation  
- 🎨 TailwindCSS-powered UI  
- 💳 Stripe-based premium subscription (Web + Telegram)  
- 🤖 Telegram bot with free-tier limits  
- 🐳 Dockerized for easy deployment  

---

## 🛠️ Technologies

- Python 3.10  
- Django 4.x  
- Django REST Framework  
- TailwindCSS  
- Stripe API  
- Telegram Bot API  
- Docker + Gunicorn  

---

## 📦 Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/Vedan8/StockInsightPlatform.git
cd stock-insight
```

### 2. Create `.env`

```env
DEBUG=True
SECRET_KEY=your-secret-key
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
BOT_TOKEN=your_telegram_bot_token
SITE_URL=http://localhost:8000
```

### 3. Run with Docker

```bash
docker-compose up --build
```

---

## 📡 API Endpoints

| Method | Endpoint               | Description                    |
|--------|------------------------|--------------------------------|
| POST   | `/api/v1/token/`       | Get JWT access/refresh tokens |
| POST   | `/api/v1/predict/`     | Predict stock price           |
| GET    | `/api/v1/predictions/` | View past predictions         |

---

## 🔐 Authentication

- Web: Django session-based (`@login_required`)
- API: JWT (`Authorization: Bearer <access_token>`)

---

## 💳 Stripe Payments

- Web checkout: `/create-checkout-session/`
- Telegram checkout: `/telegram-checkout/<uidb64>/`
- Webhook: `/webhook/`

Success: `/success/`  
Cancel: `/cancel/`

---

## 🤖 Telegram Bot Commands

- `/start`: Link account  
- `/predict <TICKER>`: Predict next day price  
- `/latest`: View latest prediction  
- `/upgrade`: Get premium payment link  

Start the bot:

```bash
docker-compose run telegrambot
```

---

## 🎨 Tailwind & Static Files

```bash
python manage.py tailwind install
python manage.py tailwind build
python manage.py collectstatic --noinput
```

---

## 🩺 Healthcheck

Used for container monitoring:  
```
GET /healthz/
```

---

## 📜 License

MIT License — free for personal and commercial use.
