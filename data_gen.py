import os
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator

os.makedirs("csv", exist_ok=True)

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]

def scale_rsi(rsi):
    return (rsi - 50) / 50   # RSI=50 → 0 (neutral), RSI=100 → +1, RSI=0 → -1

def scale_return(ret, cap=0.05):  # cap returns at ±5%
    return np.clip(ret / cap, -1, 1)

def scale_macd(macd, signal):
    diff = macd - signal
    return np.tanh(diff)  # squash into (-1,1)

def scale_bollinger(close, boll_up, boll_down):
    mid = (boll_up + boll_down) / 2
    half_width = (boll_up - boll_down) / 2
    return np.clip((close - mid) / half_width, -1, 1)

#Criterio dietro alle etichette BUY / SELL / HOLD
def BSH_labeling(row):
    # BUY:
    if (    
        row["RSI"] <= 60 and
        row["%K"] <= 70 and
        row["EMA50"] >= row["EMA200"] and 
        row["Volume"] > row["Vol_EMA200"]):  
        return "BUY"
    
    # SELL
    if (row["RSI"] > 60 and 
          row["%K"] > 70 and
          (row["Close"] < row["EMA50"] or row["Close"] < row["EMA200"]) and
          row["Volume"] < row["Vol_EMA200"]):
        return "SELL"
    
    # HOLD
    else:
        return "HOLD"

    
def add_indeces(data):
    #Rimozione del livello ridondante dal DataFrame
    #ovvero quello con il Ticker come valore di ogni riga e colonna
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    
    # Calculate % change last value
    data["Return"] = data["Close"].pct_change()
    data["Return_mean_5"] = data["Return"].rolling(window=5, min_periods=1).std()
    data["Return_std_5"] = data["Return"].rolling(window=5, min_periods=1).std()
    data["Return_mean_10"] = data["Return"].rolling(window=10, min_periods=1).std()

    # Simple moving average 20 days

    sma_window = 20
    #per vedere i dati effettivi, dobbiamo accedervi dall'oggetto
    #creato dalla funzione SMAIndicator
    ema_obj = SMAIndicator(data["Close"],window=sma_window,fillna=False)
    data["SMA"] = ema_obj.sma_indicator()

    # Exponetial moving average

    ema_window1 = 50
    ema_window2 = 200
    #per vedere i dati effettivi, dobbiamo accedervi dall'oggetto
    #creato dalla funzione EMAIndicator
    ema_obj = EMAIndicator(data["Close"],window=ema_window1,fillna=False)
    data["EMA50"] = ema_obj.ema_indicator()
    ema_obj = EMAIndicator(data["Close"],window=ema_window2,fillna=False)
    #data["EMA200"] = ema_obj.ema_indicator()


    vol_ema_200 = EMAIndicator(data["Volume"],window=ema_window2,fillna=False)
    #data["Vol_EMA200"] = vol_ema_200.ema_indicator()

    RSIwindow = 14

    #Ho usato un calcolo standard di libreria per calcolare RSI
    closeValues = data['Close']
    rsi_14 = RSIIndicator(close=closeValues, window=RSIwindow)
    #data["RSI"] = rsi_14.rsi()

    # Moving Average Convergence Divergence
    # Solitamente è bene usare RSI e MACD insieme poichè l'uno "aggiusta il tiro" dell'altro
    macd = MACD(data["Close"])

    macd_line = macd.macd()
    data["MACD"] = macd_line

    signal_line = macd.macd_signal()
    data["MACD_Signal"] = signal_line

    # Deviazione std degli ultimi 20 giorni
    window = 20
    data["Close_STD20"] = data["Close"].rolling(window=window, min_periods=1).std()
    
    data["Boll_Up"] = data["SMA"] + 2 *data["Close_STD20"]
    data["Boll_Down"] = data["SMA"] - 2 *data["Close_STD20"]

    lags = [1, 3, 7]
    features = ["Close", "Return"]

    for f in features:
        for l in lags:
            data[f"{f}_lag{l}"] = data[f].shift(l)


    #data["Tec_Sentiment"] = (
    #    0.3 * scale_return(data["Return"]) +
    #    0.3 * scale_rsi(data["RSI"]) +
    #    0.2 * scale_macd(data["MACD"], data["MACD_Signal"]) +
    #    0.2 * scale_bollinger(data["Close"], data["Boll_Up"], data["Boll_Down"])
    #)

    #data["Smoth_Tec_Sentiment10"] = data["Tec_Sentiment"].ewm(span=10).mean()

    stoch_oscillator = StochasticOscillator(
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        window=14,            # Periodo per %K
        smooth_window=3,      # Periodo per %D (SMA di %K)
        fillna=False
    )

    # Calcola %K (stoch_k)
    data['%K'] = stoch_oscillator.stoch()

    # Calcola %D (stoch_d)
    data['%D'] = stoch_oscillator.stoch_signal()

    data["Dist_low_band"] = (data["Close"] - data["Boll_Down"])/data["Close"]
    data["Dist_up_band"] = (data["Close"] - data["Boll_Up"])/data["Close"]

    return data.drop(columns=['Open', 'Low', 'High'])


#Vengono prelevati i dati delle varie aziente segnate in stocks.txt
for stock in stocks:
    try:
        df = yf.download(stock, start="2015-01-01", end="2025-09-01", auto_adjust=True)

        if df is None or df.empty:
            print(f"  No data for {stock}, skipping.")
            continue

        # Add indicators
        df = add_indeces(df)


        
        # Final cleanup and save processed CSV
        df = df.dropna()
        #df = df[["Close","High","Low","Open","Volume","Vol_EMA200","Return","SMA","EMA50","EMA200","RSI","MACD","MACD_Signal","Boll_Up","Boll_Down","%K","%D","BSH"]]

        # Conteggio delle etichette BUY/SELL/HOLD usando pandas
        #bsh_counts = df['BSH'].value_counts()
        #print(f"  Conteggio etichette per {stock}:")
        #print(bsh_counts)
        #print(f"  Totale righe: {len(df)}")
        #print("-" * 40)

        df.to_csv(f"csv/{stock}_indicators.csv")
        print(f"  Exported processed CSV: csv/{stock}_indicators_processed.csv (rows: {len(df)})")

    except Exception as e:
        print(f"Error processing {stock}: {e}")
