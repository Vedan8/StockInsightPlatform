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
    date_str = datetime.now().strftime("%Y-%m-%d")  # Only date
    ticker_str = ticker.upper() if ticker else "UNKNOWN"

    # 1. Closing Price History
    plt.figure()
    df["Close"].plot(title="Closing Price History")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.tight_layout()
    path1 = f"staticfiles/charts/{ticker_str}_{date_str}_history.png"
    plt.savefig(path1)
    plt.close()

    # 2. Actual vs Predicted
    plt.figure()
    actual = df["Close"].values[-60:]
    actual_scaled = scaler.transform(actual.reshape(-1, 1))
    test_input = np.array(actual_scaled[-60:]).reshape(1, 60, 1)
    model = load_lstm_model()
    prediction_scaled = model.predict(test_input)
    predicted = scaler.inverse_transform(prediction_scaled)

    plt.plot(range(60), actual[-60:], label="Actual")
    plt.plot([60], predicted[0], 'ro', label="Predicted")
    plt.legend()
    plt.title("Actual vs. Predicted")
    plt.tight_layout()
    path2 = f"staticfiles/charts/{ticker_str}_{date_str}_predicted.png"
    plt.savefig(path2)
    plt.close()

    return path1, path2

