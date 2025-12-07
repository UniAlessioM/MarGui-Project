import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator,ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import ROCIndicator, WilliamsRIndicator
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator

os.makedirs("csv", exist_ok=True)

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f if line.strip()]


def add_indeces(data):

    #Rimozione del livello ridondante dal DataFrame
    #ovvero quello con il Ticker come valore di ogni riga e colonna
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    
    # Ritorno percentuale sul prezzo di chiusura
    data["Return"] = data["Close"].pct_change()

    # MACD (Moving Average Convergence Divergence)
    # In genere si usa insieme all'RSI perché uno compensa i limiti dell'altro

    macd = MACD(close=data["Close"], window_slow=26, window_fast=12, window_sign=9)
    data["MACD"]        = macd.macd()
    data["MACD_Signal"] = macd.macd_signal()
    data["MACD_Hist"]   = macd.macd_diff()


    # Media mobile semplice a 20 giorni

    sma_window = 20
    #per vedere i dati effettivi, dobbiamo accedervi dall'oggetto
    #creato dalla funzione SMAIndicator
    ema_obj = SMAIndicator(data["Close"],window=sma_window,fillna=False)
    data["SMA"] = ema_obj.sma_indicator()

    # Medie mobili esponenziali

    ema_window1 = 20
    #per vedere i dati effettivi, dobbiamo accedervi dall'oggetto
    #creato dalla funzione EMAIndicator
    ema_obj = EMAIndicator(data["Close"],window=ema_window1,fillna=False)
    data["EMA20"] = ema_obj.ema_indicator()

    vol_ema_50 =  EMAIndicator(data["Volume"],window=ema_window1,fillna=False)
    data["Vol_EMA20"] = vol_ema_50.ema_indicator()

    # Media mobile ponderata
    #data['WMA20'] = data["Close"].rolling(window=window, min_periods=1).apply(

    RSIwindow = 14

    #Ho usato un calcolo standard di libreria per calcolare RSI
    closeValues = data['Close']
    rsi_14 = RSIIndicator(close=closeValues, window=RSIwindow)
    data["RSI"] = rsi_14.rsi()


    # Deviazione std degli ultimi 20 giorni
    window = 20
    std = data["Close"].rolling(window=window, min_periods=1).std()
    
    # Bande di Bollinger
    # Quando il prezzo si avvicina alla banda superiore (Boll_Up) può indicare condizioni di ipercomprato
    # e una possibile inversione al ribasso. Viceversa, vicino alla banda inferiore (Boll_Down) può indicare
    # condizioni di ipervenduto e una potenziale inversione al rialzo.
    
    data["Boll_Up"] = data["SMA"] + 2 *std
    data["Boll_Down"] = data["SMA"] - 2 *std

    
    data["Dist_low_band"] = (data["Close"] - data["Boll_Down"])/data["Close"]
    data["Dist_up_band"] = (data["Close"] - data["Boll_Up"])/data["Close"]

    # Lo Stochastic misura il prezzo corrente rispetto all'intervallo di prezzi in un certo periodo.
    # Ha due componenti: %K e %D. %K rappresenta la posizione del prezzo di chiusura rispetto al minimo/massimo
    # del periodo e varia da 0 a 100. Valori vicini a 0 indicano area di ipervenduto (vicino ai minimi del range),
    # valori vicini a 100 indicano area di ipercomprato (vicino ai massimi del range). %D è la versione smussata di %K
    # ed è spesso calcolata come media mobile di %K.

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

    r_ema_20_window = 20
    r_ema_20 = EMAIndicator(data["Return"],window=r_ema_20_window,fillna=False)


    # Media esponenziale mobile calcolata sui ritorni.
    data["R_EMA20"] = r_ema_20.ema_indicator()

   
    adx = ADXIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=14)
    data["ADX"] = adx.adx()
    data["+DI"] = adx.adx_pos()
    data["-DI"] = adx.adx_neg()

    atr = AverageTrueRange(high=data["High"], low=data["Low"], close=data["Close"], window=14)
    data["ATR"] = atr.average_true_range()

    bb = BollingerBands(close=data["Close"], window=20, window_dev=2)
    data["BB_pctB"] = (data["Close"] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())

    roc = ROCIndicator(close=data["Close"], window=10)
    data["ROC"] = roc.roc()

    wr = WilliamsRIndicator(high=data["High"], low=data["Low"], close=data["Close"], lbp=14)
    data["W%R"] = wr.williams_r()

    obv = OnBalanceVolumeIndicator(close=data["Close"], volume=data["Volume"])
    data["OBV"] = obv.on_balance_volume()

    cmf = ChaikinMoneyFlowIndicator(high=data["High"], low=data["Low"], close=data["Close"], volume=data["Volume"], window=20)
    data["CMF"] = cmf.chaikin_money_flow()

    data["MACD_norm"] = data["MACD"] / data["Close"]


    data["RSI_diff"] = data["RSI"] - data["RSI"].rolling(14).mean()
    data["DI_diff"] = data["+DI"] - data["-DI"]

    # Questi catturano il momentum o la velocità di cambiamento dell'indicatore.
    data["SMA_slope"] = data["SMA"].diff()
    data["RSI_slope"] = data["RSI"].diff()
    data["MACD_slope"] = data["MACD"].diff()
    data["%K_slope"] = data["%K"].diff()
    data["%D_slope"] = data["%D"].diff()
    data["ATR_slope"] = data["ATR"].diff()
    data["OBV_slope"] = data["OBV"].diff()
    data["ADX_slope"] = data["ADX"].diff()


    #Valori Booleani Semplici

    # Crossover EMA breve/lunga: Positiva se EMA50 > EMA200
    
    # Distanza del prezzo dalla SMA: Percentuale sopra/sotto la media
    #data["Price_vs_SMA_pct"] = (data["Close"] - data["SMA"]) / data["SMA"]

    # Posizione dell'RSI rispetto ai livelli di ipercomprato/ipervenduto
    data["RSI_overbought"] = np.where(data["RSI"] > 70, 1, 0)
    data["RSI_oversold"] = np.where(data["RSI"] < 30, 1, 0)

    # Posizione dello Stochastic rispetto ai livelli di ipercomprato/ipervenduto
    data["Stoch_overbought"] = np.where(data["%K"] > 80, 1, 0)
    data["Stoch_oversold"] = np.where(data["%K"] < 20, 1, 0)

    # MACD crossover (la linea MACD incrocia la linea Signal)
    # 1 se MACD_Hist è positivo (MACD > Signal), -1 se negativo, 0 se circa nullo
    # Utile come segnale di momentum
    data["MACD_crossover_signal"] = np.where(data["MACD_Hist"] > 0, 1, np.where(data["MACD_Hist"] < 0, -1, 0))
    
    # Range di prezzo normalizzato: ampiezza giornaliera in relazione all'ATR
    #data["Daily_Range_vs_ATR"] = (data["High"] - data["Low"]) / data["ATR"]


    # Ritorni traslati nel tempo ("lag") e medie esponenziali sui ritorni
    # Le EMA sono utili in predizione perché pesano maggiormente i dati più recenti
    # rispetto ai ritorni semplici

    #lags = [1, 3, 7, 14]
    #features = ["Close", "Return"]

    #for f in features:
    #    for l in lags:
    #        data[f"{f}_lag{l}"] = data[f].shift(l)
    #    
    #data["MACD_lag1"] = data["MACD"].shift(1)
    #data["ATR_lag1"] = data["ATR"].shift(1)
    #data["BB_pctB_lag1"] = data["BB_pctB"].shift(1)
    #data["ROC_lag1"] = data["ROC"].shift(1)
    #data["W%R_lag1"] = data["W%R"].shift(1)
    #data["OBV_lag1"] = data["OBV"].shift(1)
    #data["CMF_lag1"] = data["CMF"].shift(1)

    # --- FEATURE AVANZATE --- #

        # 1. FEATURE DI INTERAZIONE 
    # L'idea è che la combinazione di due segnali sia più potente dei segnali singoli.
    # Un RSI alto con volumi in crescita è un segnale molto diverso da un RSI alto con volumi deboli.

    # Calcoliamo prima la variazione percentuale del volume
    data['Vol_pct_change'] = data['Volume'].pct_change()

    # Interazione: RSI * Variazione Volume. Valori alti indicano forte momentum con supporto del volume.
    data['RSI_x_Vol_Change'] = data['RSI'] * data['Vol_pct_change']


    #  2. FEATURE DI NORMALIZZAZIONE CONTESTUALE 
    # L'obiettivo è rendere un indicatore confrontabile nel tempo e tra diversi asset.
    # Un ATR di 0.5$ su un'azione da 10$ è alta volatilità. Su un'azione da 500$ è quasi nulla.

    # ATR normalizzato dal prezzo di chiusura (Volatilità Percentuale)
    # Ci dice l'ampiezza media del movimento giornaliero come percentuale del prezzo.
    data['ATR_pct'] = (data['ATR'] / data['Close']) * 100


    #  3. INDICATORI DI SECONDO LIVELLO 
    # Calcoliamo indicatori su altri indicatori per catturare il loro "momentum" o "trend".

    # Media Mobile dell'RSI. Se RSI > RSI_SMA10, il momentum sta accelerando al rialzo.
    data['RSI_SMA15'] = data['RSI'].rolling(window=15).mean()

    # Distanza dell'RSI dalla sua media mobile. Segnala accelerazioni/decelerazioni del momentum.
    data['RSI_vs_SMA'] = data['RSI'] - data['RSI_SMA15']

    # Deviazione Standard del MACD Histogram. Misura la "volatilità del momentum".
    # Valori alti indicano che il momentum sta cambiando molto rapidamente.
    data['MACD_Hist_Std20'] = data['MACD_Hist'].rolling(window=20).std()

    return data.drop(columns=["Adj Close"])

start = "2018-01-01"
end = "2025-11-20"

print("Fetching and adding market index features (SP500-45)...")


# Scarica i dati di un indice di settore
sp = yf.download("^SP500-45", start=start, end=end, auto_adjust=False)


if sp is not None and not sp.empty:
    if isinstance(sp.columns, pd.MultiIndex):
        sp.columns = sp.columns.droplevel(1)
    sp['SP_Return'] = sp['Close'].pct_change()
    sp['SP_RSI'] = RSIIndicator(close=sp['Close'], window=14).rsi()
    sp['SP_SMA20'] = SMAIndicator(close=sp['Close'], window=20).sma_indicator()
    sp['SP_Dist_SMA'] = (sp['Close'] - sp['SP_SMA20']) / sp['SP_SMA20']
    sp500_features = sp[['SP_Return', 'SP_RSI', 'SP_Dist_SMA']]
    

else:
    print("Failed to fetch SP500-45 data.")



for stock in stocks:
    try:
        df = yf.download(stock, start=start, end=end, auto_adjust=False)
        #print(df)
        if df is None or df.empty:
            print(f"  No data for {stock}, skipping.")
            continue

    # Aggiunge gli indicatori tecnici
        df = add_indeces(df)
        if(sp is not None and not sp.empty):
            df = df.join(sp500_features)
        
        if len(df) < 100:
            print(f"  Warning: Only {len(df)} rows for {stock}, skipping")
            continue

    # Pulizia finale e salvataggio del CSV elaborato
        df.dropna(inplace=True)
    
        df.to_csv(f"csv/{stock}_indicators.csv")
        print(f"  Exported processed CSV: csv/{stock}_indicators_processed.csv (rows: {len(df)})\n")

    except Exception as e:
        print(f"Error processing {stock}: {e}")