import os
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator

os.makedirs("csv", exist_ok=True)

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]


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

    data["Return-1"] = data["Return"].shift(1)
    data["Return-3"] = data["Return"].shift(3)
    data["Return-7"] = data["Return"].shift(7)

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
    data["EMA200"] = ema_obj.ema_indicator()


    vol_ema_200 = EMAIndicator(data["Volume"],window=ema_window2,fillna=False)
    data["Vol_EMA200"] = vol_ema_200.ema_indicator()

    # Wheited moving average
    #data['WMA20'] = data["Close"].rolling(window=window, min_periods=1).apply(
    #    lambda prices: np.dot(prices, np.arange(1, len(prices)+1))/np.arange(1, len(prices)+1).sum()
    #   if len(prices) > 0 else np.nan, raw=True)
    
    # Relative Strength index (RSI)
    #Exceeding Fair Value: The stock's price has become unsustainable and is 
    # trading above what its underlying fundamentals might justify. 
    #Market Euphoria: A period of high buying interest and optimism, 
    # sometimes fueled by fear of missing out (FOMO), 
    # can push prices to seemingly unsustainable levels. 
    #Potential for a Reversal: An overbought condition signals 
    # that a pullback or decline in price is likely, 
    # as investors may start selling to lock in profits. 
    RSIwindow = 14

    #Ho usato un calcolo standard di libreria per calcolare RSI
    closeValues = data['Close']
    rsi_14 = RSIIndicator(close=closeValues, window=RSIwindow)
    data["RSI"] = rsi_14.rsi()

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
    


    # Bollinger Bands
    # When the price moves close to the upper band (Boll_Up), 
    # it may indicate overbought conditions, suggesting a potential price reversal to the downside.
    # Conversely, when the price approaches the lower band (Boll_Down), 
    # it may indicate oversold conditions, suggesting a potential price reversal to the upside.
    
    data["Boll_Up"] = data["SMA"] + 2 *data["Close_STD20"]
    data["Boll_Down"] = data["SMA"] - 2 *data["Close_STD20"]



    data["Return_STD20"] = data["Close"].rolling(window=window, min_periods=1).std()
    data["Return_STD10"] = data["Close"].rolling(window=window-10, min_periods=1).std()



    #Stochastics measures the current price of a stock relative to it’s price range over a specific period of time. It has two components: %K and %D. -
    #%K represents the current closing price of the stock relative to the highest and lowest prices over a defined period and it ranges from O to 100.
    #When %K is near 0, it suggests the stock is trading near the lower end of its price range, indicating an oversold condition. When %K is near 100, it
    #suggests the stock is trading near the upper end of its price range, indicating an overbought condition. - %D is the smoothed version of %K and is
    #often represented as moving average of %K.

    # window: periodicità per %K (solitamente 14)
    # smooth_window: periodicità per %D (solitamente 3)
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

    return data


data_set = {}
#Vengono prelevati i dati delle varie aziente segnate in stocks.txt
for stock in stocks:
    try:
        df = yf.download(stock, start="2015-01-01", end="2025-09-01", auto_adjust=True)

        if df is None or df.empty:
            print(f"  No data for {stock}, skipping.")
            continue

        # Add indicators
        df = add_indeces(df)

        # Data quality: drop rows where Close is NaN (early)
        initial_rows = len(df)
        close_nan_count = df['Close'].isna().sum()
        df = df.dropna(subset=['Close'])
        print(f"  Removed {close_nan_count} rows with NaN Close values")

        # Remove rows where more than 50% of columns are NaN
        df = df.dropna(thresh=int(len(df.columns) * 0.5))
        print(f"  Kept {len(df)}/{initial_rows} rows after cleaning")

        if len(df) < 100:
            print(f"  Warning: Only {len(df)} rows for {stock}, skipping")
            continue

        #Inserimento delle etichette BUY/SELL/HOLD
        #df["BSH"] = df.apply(BSH_labeling, axis=1)

        
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
