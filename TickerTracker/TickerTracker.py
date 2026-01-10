from flask import Flask, render_template
import yfinance as yf
import plotly.graph_objs as go
from plotly.offline import plot as plotly_plot
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from indeces import add_indeces

TICKER = "AAPL"
app = Flask(__name__)

bundle = joblib.load(f"model/{TICKER}.joblib")

FEATURES_LIST = bundle["features"]
WINDOW_SIZE = 40      
FLOOR_PROB = 0.40     
DAYS_TO_CHECK =  5
DAYS_TO_SHOW = 30
BEST_K = bundle["aggressive"]

@app.route('/')
def index():
    print(f"Scaricando dati per {TICKER}...")
    
    # Scarico dati sufficienti per fare i calcoli dei vari indici
    df = yf.download(TICKER, period="1y", interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return "Errore: Nessun dato disponibile."
    
    df = add_indeces(df)
    df_indicators = df.copy()

    df_chart = df_indicators.tail(DAYS_TO_SHOW).copy()
    df_chart.reset_index(inplace=True)
    df_chart['DateStr'] = df_chart['Date'].dt.strftime('%Y-%m-%d')

    # Plotly/HTML non riescono a tirar fuori da pandas i dati in modo corretto per poterli plottare.
    # Perciò c'è la necessità di trasformare tutto in liste, oggetti più "gestibili"

    dates_list = df_chart['DateStr'].tolist()
    prices_list = df_chart['Close'].tolist()
    
    trace = go.Scatter(
        x=dates_list,
        y=prices_list,
        mode='lines+markers',
        name='Close Price',
        line=dict(color='#007bff', width=2)
    )

    layout = go.Layout(
            title=f'',
            xaxis=dict(
                title='Data',
                
                tickmode='array',             
                tickvals=df_chart['DateStr'], 
                ticktext=df_chart['DateStr'], 
                tickangle=-90,                 
                automargin=True               
            ),
            yaxis=dict(title='Prezzo ($)'),
            template='plotly_dark',
            paper_bgcolor='#0b0b0b',
            plot_bgcolor='#0b0b0b',
            font=dict(color='#e9ecef'),
            margin=dict(l=40, r=40, t=60, b=100)
        )

    # Figura lineare (server-side Plotly)
    line_fig = go.Figure(data=[trace], layout=layout)
    line_div = plotly_plot(line_fig, include_plotlyjs=False, output_type='div')

    # Dati OHLC per candlestick
    ohlc_chart = df_chart.tail(DAYS_TO_SHOW).copy()
    ohlc_chart.reset_index(inplace=True)
    ohlc_chart['DateStr'] = ohlc_chart['Date'].dt.strftime('%Y-%m-%d')

    # Figura candlestick (server-side Plotly)
    candle = go.Candlestick(
        x=ohlc_chart['DateStr'].tolist(),
        open=ohlc_chart['Open'].tolist(),
        high=ohlc_chart['High'].tolist(),
        low=ohlc_chart['Low'].tolist(),
        close=ohlc_chart['Close'].tolist(),
        name='OHLC'
    )
    candle_layout = go.Layout(
        title=f'',
        xaxis=dict(
            title='Data',
            tickmode='array',
            tickvals=ohlc_chart['DateStr'].tolist(),
            ticktext=ohlc_chart['DateStr'].tolist(),
            tickangle=-90,
            automargin=True
        ),
        yaxis=dict(title='Prezzo ($)'),
        template='plotly_dark',
        paper_bgcolor='#0b0b0b',
        plot_bgcolor='#0b0b0b',
        font=dict(color='#e9ecef'),
        margin=dict(l=40, r=40, t=60, b=100)
    )
    candle_fig = go.Figure(data=[candle], layout=candle_layout)
    candle_div = plotly_plot(candle_fig, include_plotlyjs=False, output_type='div')

    # Generazione Previsioni 
    # Prendiamo le ultime DAYS_TO_CHECK righe
    last_rows = df_indicators.tail(DAYS_TO_CHECK).copy()
    # Per il warm start serviranno almeno WINDOW_SIZE giorni
    df_indicators = df_indicators.tail(DAYS_TO_SHOW + WINDOW_SIZE).copy()
    predictions_data = []
    model = bundle["model"]
    if model:
        try:

            X = df_indicators[FEATURES_LIST]
            dmatrix = xgb.DMatrix(X, feature_names=FEATURES_LIST)
            

            probs = model.predict(dmatrix)
            
            probs_series = pd.Series(probs, index=df_indicators.index)
            
            # Calcolo threshold dinamica

            roll_mean = probs_series.rolling(window=WINDOW_SIZE,min_periods=WINDOW_SIZE).mean()
            roll_std = probs_series.rolling(window=WINDOW_SIZE,min_periods=WINDOW_SIZE).std()
            
            # Formula: Media + Std * K
            dynamic_thresh_series = roll_mean + roll_std.mul(float(BEST_K))
            
            dynamic_thresh_series = dynamic_thresh_series.fillna(FLOOR_PROB)
            dynamic_thresh_series = np.maximum(dynamic_thresh_series, FLOOR_PROB)


            # Estrazione solo gli ultimi DAYS_TO_CHECK giorni per la visualizzazione
            last_rows = df_indicators.tail(DAYS_TO_CHECK)
            last_probs = probs_series.tail(DAYS_TO_CHECK)

            last_thresholds = pd.Series(dynamic_thresh_series).tail(DAYS_TO_CHECK)
            
            # Costruzione dati per l'HTML
            for i in range(len(last_rows)):
                date_val = last_rows.index[i]
                close_price = last_rows['Close'].iloc[i]
                
                prob_val = last_probs.iloc[i]
                thresh_val = last_thresholds.iloc[i]
                
                # Decisione basata sulla soglia dinamica di QUEL giorno
                signal = "BUY" if prob_val > thresh_val else "SELL"
                
                predictions_data.append({
                    'date': date_val.strftime('%Y-%m-%d'),
                    'close': round(close_price, 2),
                    'prob': round(prob_val * 100, 1),
                    'thresh': round(thresh_val * 100, 1),
                    'signal': signal,
                    'is_today': i == len(last_rows) - 1
                })  


        except Exception as e:
            print(f"Errore durante la predizione: {e}")
            predictions_data = []     

    # Nella stampa vogliamo vedere la predizione di oggi in cima
    predictions_data.reverse()

    return render_template('index.html', line_div=line_div, candle_div=candle_div, predictions=predictions_data, ticker=TICKER)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)