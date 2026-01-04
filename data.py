import os
import yfinance as yf
from TickerTracker.indeces import add_indeces
from TickerTracker.indeces import start, end
os.makedirs("csv", exist_ok=True)

# Nel file stocks.txt si possono inserire più sigle di vari ticker
# per scaricare i dati tutti in una volta sola

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]

for stock in stocks:
    try:
        df = yf.download(stock, start=start, end=end, auto_adjust=False)
        #print(df)
        if df is None or df.empty:
            print(f"  No data for {stock}, skipping.")
            continue

    # Aggiunge gli indicatori tecnici
        df = add_indeces(df)
        
        if len(df) < 100:
            print(f"  Warning: Only {len(df)} rows for {stock}, skipping")
            continue

    # Pulizia finale e salvataggio del CSV elaborato
        df.dropna(inplace=True)
    
        df.to_csv(f"csv/{stock}_indicators.csv")
        print(f"  Exported processed CSV: csv/{stock}_indicators_processed.csv (rows: {len(df)})\n")

    except Exception as e:
        print(f"Error processing {stock}: {e}")