import os
import yfinance as yf
import pandas as pd
import numpy as n
from datetime import datetime
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator,ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import ROCIndicator, WilliamsRIndicator
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator

os.makedirs("csv", exist_ok=True)

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]


#Criterio dietro alle etichette BUY / SELL / HOLD

# ----------------------------------------
# Condizioni iniziali, poi modificate per testare il dataset
# 
# Buy if (ema50 >= ema200) OR (Volume > VOLEMA200)
# Sell if (RSI > 70 AND stoch_k > 80) OR (Close < ema50) OR (Close < ema200)
# Else Hold
# ----------------------------------------


def BSH_labeling(row):
    # BUY:
    if (row["EMA50"] >= row["EMA200"] and 
        row["Volume"] > row["Vol_EMA200"]):  
        return "BUY"
    
    # SELL
    if ((row["RSI"] > 68 and row["%K"] > 78) or
        (row["Close"] < row["EMA50"] or row["Close"] < row["EMA200"])):
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


    """
    BUY = Volume > vol.ema200:
    Interpretazione: Un segnale di acquisto è considerato più forte o convalidato quando il volume 
    di trading attuale è superiore alla sua media esponenziale a lungo termine (200 periodi).
    Significato: Questo suggerisce che c'è un interesse significativo e una partecipazione elevata 
    del mercato nel movimento di prezzo corrente. Se il prezzo sta salendo e il volume è superiore 
    alla sua EMA200, è un buon segno che gli acquirenti sono in forza e il trend rialzista potrebbe 
    essere sostenibile.
    SELL = Volume < vol.ema200:
    Interpretazione: Un segnale di vendita è considerato più forte o convalidato quando il volume 
    di trading attuale è inferiore alla sua media esponenziale a lungo termine.
    Significato: Questo può essere interpretato in diversi modi a seconda del contesto del prezzo:
    Se il prezzo sta scendendo e il volume è inferiore alla sua EMA200, il trend ribassista potrebbe 
    essere debole o non avere una forte convinzione.
    Se il prezzo sta salendo ma il volume è inferiore alla sua EMA200, 
    potrebbe indicare che il trend rialzista è debole, mancano acquirenti forti e 
    una potenziale inversione potrebbe essere imminente 
    (un segnale di "non conferma" per il trend rialzista).
    """


    vol_ema_200 = EMAIndicator(data["Volume"],window=ema_window2,fillna=False)
    data["Vol_EMA200"] = vol_ema_200.ema_indicator()
    vol_ema_50 =  EMAIndicator(data["Volume"],window=ema_window1,fillna=False)
    data["Vol_EMA50"] = vol_ema_50.ema_indicator()

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


    # Deviazione std degli ultimi 20 giorni
    window = 20
    std = data["Close"].rolling(window=window, min_periods=1).std()
    


    # Bollinger Bands
    # When the price moves close to the upper band (Boll_Up), 
    # it may indicate overbought conditions, suggesting a potential price reversal to the downside.
    # Conversely, when the price approaches the lower band (Boll_Down), 
    # it may indicate oversold conditions, suggesting a potential price reversal to the upside.
    
    data["Boll_Up"] = data["SMA"] + 2 *std
    data["Boll_Down"] = data["SMA"] - 2 *std


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

    #Feature engineering: 
    # Ritorni traslati nel tempo ("Lagged") e Media esp. mobile sui ritorni
    # Apparentemente EMA viene usata per le predizioni poichè è l'indice
    # che riesce a fornire un peso maggiore ai dati di mercato più recenti,
    # perciò si predilige all'uso del semplice return

    """
    For prediction models it is better to avoid the "leaking" problem where one feeds the model
    with the same parameters used for the data labeling. So, in order to avoid this problem,
    predictions will be made used other types of indices, like the EMA on returns and the price Lag.
    Of course, it also depends on the strategy used to label the dataset.
    """

    data["Lag1"] = data["Close"].pct_change(periods=1) * 100.0       
    data["Lag10"] = data["Close"].pct_change(periods=10) * 100.0
    data["Lag15"] = data["Close"].pct_change(periods=15) * 100.0
    data["Lag50"] = data["Close"].pct_change(periods=50) * 100.0

    r_ema_50_window = 50
    r_ema_20_window = 20

    r_ema_50 = EMAIndicator(data["Return"],window=r_ema_50_window,fillna=False)
    r_ema_20 = EMAIndicator(data["Return"],window=r_ema_20_window,fillna=False)


    # Media esponenziale mobile calcolata sui ritorni.
    data["R_EMA20"] = r_ema_20.ema_indicator()
    data["R_EMA50"] = r_ema_50.ema_indicator()

    # --- Trend strength ---
    adx = ADXIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=14)
    data["ADX"] = adx.adx()
    data["+DI"] = adx.adx_pos()
    data["-DI"] = adx.adx_neg()

    # --- Volatility ---
    atr = AverageTrueRange(high=data["High"], low=data["Low"], close=data["Close"], window=14)
    data["ATR"] = atr.average_true_range()

    bb = BollingerBands(close=data["Close"], window=20, window_dev=2)
    data["BB_pctB"] = (data["Close"] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())

    # --- Momentum ---
    roc = ROCIndicator(close=data["Close"], window=10)
    data["ROC"] = roc.roc()

    wr = WilliamsRIndicator(high=data["High"], low=data["Low"], close=data["Close"], lbp=14)
    data["W%R"] = wr.williams_r()

    
    # Moving Average Convergence Divergence
    # Solitamente è bene usare RSI e MACD insieme poichè l'uno "aggiusta il tiro" dell'altro


    macd = MACD(close=data["Close"], window_slow=26, window_fast=12, window_sign=9)
    data["MACD"]        = macd.macd()
    data["MACD_Signal"] = macd.macd_signal()
    data["MACD_Hist"]   = macd.macd_diff()

    # --- Volume-based ---
    #obv = OnBalanceVolumeIndicator(close=data["Close"], volume=data["Volume"])
    #data["OBV"] = obv.on_balance_volume()

    #cmf = ChaikinMoneyFlowIndicator(high=data["High"], low=data["Low"], close=data["Close"], volume=data["Volume"], window=20)
    #data["CMF"] = cmf.chaikin_money_flow()



    return data

#Vengono prelevati i dati delle varie aziente segnate in stocks.txt
for stock in stocks:
    try:
        df = yf.download(stock, start="2000-01-01", end=datetime.strftime(datetime.now(), "%Y-%m-%d"), auto_adjust=False)
        #print(df)
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
        df["BSH"] = df.apply(BSH_labeling, axis=1)


        # Final cleanup and save processed CSV
        df = df.dropna()
        df = df[["Close","High","Low","Open","Volume","Vol_EMA200","Vol_EMA50","Return","SMA","EMA50","EMA200",
                 "RSI","MACD","MACD_Signal","MACD_Hist","Boll_Up","Boll_Down","%K","%D","R_EMA50","R_EMA20",
                 "Lag1","Lag10","Lag15","Lag50","ADX","+DI","-DI","ATR","BB_pctB","ROC","W%R","BSH"]]

        # Conteggio delle etichette BUY/SELL/HOLD usando pandas
        bsh_counts = df['BSH'].value_counts()
        print(f"  Conteggio etichette per {stock}:")
        print(bsh_counts)
        print(f"  Totale righe: {len(df)}")
        print("-" * 40)

        df.to_csv(f"csv/{stock}_indicators.csv")
        print(f"  Exported processed CSV: csv/{stock}_indicators_processed.csv (rows: {len(df)})")

    except Exception as e:
        print(f"Error processing {stock}: {e}")
