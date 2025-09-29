import os
import yfinance as yf
import pandas as pd
import numpy as np

os.makedirs("csv", exist_ok=True)

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]
    
def add_indicators(data):
    # Remove tiker row
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    
    window = 20 #std window size 

    # Calculate % change last value
    data["Return"] = data["Close"].pct_change()

    # Relative Strength index
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # Moving Average Convergence Divergence
    short, long, signal = 12, 26, 9
    data["MACD"] = data["Close"].ewm(span=short, adjust=False).mean() - data["Close"].ewm(span=long, adjust=False).mean()
    data["Signal_Line"] = data["MACD"].ewm(span=signal, adjust=False).mean()

    # Deviazione std
    data["STD20"] = data["Close"].rolling(window=window, min_periods=1).std()
    
    data = data.drop(columns=["Close", "Low", "High", "Open"])

    return data

for stock in stocks:
    try:
        print(f"Processing {stock}...")
        df = yf.download(stock, start="2015-01-01", end=pd.Timestamp.today().strftime('%Y-%m-%d'), auto_adjust=True)
        if df is None or df.empty:
            print(f"  No data for {stock}, skipping.")
            continue

        # Add indicators
        df = add_indicators(df)

        # Data quality: drop rows where Close is NaN (early)
        initial_rows = len(df)
        close_nan_count = df['Return'].isna().sum()
        df = df.dropna(subset=['Return'])
        print(f"  Removed {close_nan_count} rows with NaN Close values")

        # Remove rows where more than 50% of columns are NaN
        df = df.dropna(thresh=int(len(df.columns) * 0.5))
        print(f"  Kept {len(df)}/{initial_rows} rows after cleaning")

        if len(df) < 100:
            print(f"  Warning: Only {len(df)} rows for {stock}, skipping")
            continue

        # Create target and shift features (predict next day's Close)
        #df["Target"] = df["Return"].shift(-1)

        # Final cleanup and save processed CSV
        df = df.dropna()
        df.to_csv(f"csv/{stock}_indicators.csv")
        print(f"  Exported processed CSV: csv/{stock}_indicators_processed.csv (rows: {len(df)})")

    except Exception as e:
        print(f"Error processing {stock}: {e}")
