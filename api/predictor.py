import os
import yfinance as yf
import numpy as np
from datetime import datetime
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

MODEL_PATH = os.getenv("MODEL_PATH", "stock_prediction_model.keras")

def fetch_stock_data(ticker):
    end = datetime.now()
    start = end.replace(year=end.year - 10)
    df = yf.download(ticker, start=start, end=end)
    if df.empty:
        raise ValueError("No data found for ticker: " + ticker)
    return df[["Close", "Open", "High", "Low", "Volume"]]

def load_lstm_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Model file not found: " + MODEL_PATH)
    return load_model(MODEL_PATH)

def generate_prediction(df):
    data = df[["Close"]].values
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)

    # Use last 60 days for prediction input
    X_input = scaled_data[-60:]
    X_input = X_input.reshape(1, X_input.shape[0], 1)

    model = load_lstm_model()
    pred_scaled = model.predict(X_input)
    pred = scaler.inverse_transform(pred_scaled)

    return pred[0][0], scaler

def create_charts(df, prediction, scaler, ticker=None):
    from copy import deepcopy
    date_str = datetime.now().strftime("%Y-%m-%d")
    ticker_str = ticker.upper() if ticker else "UNKNOWN"

    # 1. Closing Price History
    plt.figure(figsize=(10, 6))
    df["Close"].plot(title=f"{ticker_str} Closing Price History", grid=True)
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    path1 = f"staticfiles/charts/{ticker_str}_{date_str}_history.png"
    plt.savefig(path1)
    plt.close()

    # 2. Actual vs Predicted over last 60 days
    actual_prices = df["Close"].values[-120:]  # Need extra for sliding window
    actual_scaled = scaler.transform(actual_prices.reshape(-1, 1))

    model = load_lstm_model()
    predicted_prices = []

    # Use sliding window to predict each day in the last 60 days
    for i in range(60):
        input_seq = actual_scaled[i:i+60].reshape(1, 60, 1)
        pred_scaled = model.predict(input_seq, verbose=0)
        pred = scaler.inverse_transform(pred_scaled)[0][0]
        predicted_prices.append(pred)

    # Actual for last 60 days
    actual_last_60 = actual_prices[-60:]

    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(range(60), actual_last_60, label="Actual", color="blue")
    plt.plot(range(60), predicted_prices, label="Predicted", color="orange")
    plt.title(f"{ticker_str} - Last 60 Days: Actual vs Predicted", fontsize=14)
    plt.xlabel("Day (0 = 60 days ago)", fontsize=12)
    plt.ylabel("Price (USD)", fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    path2 = f"staticfiles/charts/{ticker_str}_{date_str}_predicted.png"
    plt.savefig(path2)
    plt.close()

    return path1, path2
