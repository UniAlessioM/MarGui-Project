import pandas as pd
import numpy as np

target_window = 5
TICKER = "AAPL"

def calculate_target(df, window=target_window, profit_take_pct=1.5, stop_loss_pct=1.5):
    
    #Calcola le etichette binarie (0 o 1) basandosi sul metodo a due barriere.

    #Args:
    #    df (pd.DataFrame): DataFrame con i dati di prezzo (deve contenere 'Close', 'High', 'Low').
    #    window (int): L'orizzonte temporale massimo in giorni per raggiungere una barriera.
    #    profit_take_pct (float): La soglia percentuale per la barriera di profitto.
    #    stop_loss_pct (float): La soglia percentuale per la barriera di stop-loss.

    #Returns:
    #    pd.Series: Una serie di etichette (0, 1).
    
    
    targets = []
    
    # Converti le percentuali in moltiplicatori
    profit_multiplier = 1 + (profit_take_pct / 100)
    stop_multiplier = 1 - (stop_loss_pct / 100)

    for i in range(len(df)):
        # Controlla se ci sono abbastanza dati futuri per la finestra
        if i + window >= len(df):
            targets.append(np.nan)
            continue

        start_price = df['Close'].iloc[i]
        
        # Calcola le barriere per questo specifico punto di partenza
        upper_barrier = start_price * profit_multiplier
        lower_barrier = start_price * stop_multiplier
        
        target_label = 0  # Default: consideriamo un timeout come una non-vittoria (0)
        
        # Ciclo sui giorni futuri per vedere quale barriera viene toccata prima
        for j in range(1, window + 1):
            future_high = df['High'].iloc[i + j]
            future_low = df['Low'].iloc[i + j]
            
            # 1. Controlla se la barriera di profitto è stata raggiunta
            if future_high >= upper_barrier:
                target_label = 1
                break  # Esci dal ciclo interno, abbiamo un vincitore!
            
            # 2. Controlla se la barriera di stop-loss è stata raggiunta
            if future_low <= lower_barrier:
                target_label = 0
                break  # Esci dal ciclo interno, abbiamo un perdente!
        
        # Se il ciclo finisce senza un 'break', l'etichetta rimane il default (0)
        targets.append(target_label)
        
    return pd.Series(targets, index=df.index)