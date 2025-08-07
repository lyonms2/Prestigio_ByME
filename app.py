import requests
import pandas as pd

# Lista de moedas
TOP200 = {
    "BTC-USDT","ETH-USDT","BNB-USDT","SOL-USDT","XRP-USDT","DOGE-USDT",
    "ADA-USDT","AVAX-USDT","MATIC-USDT","DOT-USDT","TRX-USDT","SHIB-USDT",
    "UNI-USDT","LINK-USDT","ETC-USDT","FIL-USDT"
}

INTERVAL = "1h"  # Pode ser alterado
LIMIT = 100      # Velas

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.replace('-', '')}&interval={INTERVAL}&limit={LIMIT}"
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data, columns=[
        'time','open','high','low','close','volume','close_time','quote_asset_volume',
        'number_of_trades','taker_buy_base','taker_buy_quote','ignore'
    ])
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    return df

def heiken_ashi(df):
    ha_df = df.copy()
    ha_df['HA_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4
    ha_df['HA_open'] = 0.0
    ha_df['HA_open'].iloc[0] = (ha_df['open'].iloc[0] + ha_df['close'].iloc[0]) / 2
    for i in range(1, len(ha_df)):
        ha_df['HA_open'].iloc[i] = (ha_df['HA_open'].iloc[i-1] + ha_df['HA_close'].iloc[i-1]) / 2
    ha_df['HA_high'] = ha_df[['high', 'HA_open', 'HA_close']].max(axis=1)
    ha_df['HA_low'] = ha_df[['low', 'HA_open', 'HA_close']].min(axis=1)
    return ha_df

def rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def stochastic(df, k_period=14, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = 100 * (df['close'] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return k, d

resultados = []

for symbol in TOP200:
    df = get_klines(symbol)
    df = heiken_ashi(df)
    df['RSI'] = rsi(df)
    df['%K'], df['%D'] = stochastic(df)

    ultima = df.iloc[-1]
    penultima = df.iloc[-2]

    # Filtro principal: troca de cor Heiken Ashi
    if (penultima['HA_close'] > penultima['HA_open'] and ultima['HA_close'] < ultima['HA_open']) or \
       (penultima['HA_close'] < penultima['HA_open'] and ultima['HA_close'] > ultima['HA_open']):
        
        # Informações adicionais
        rsi_status = ""
        if ultima['RSI'] > 70:
            rsi_status = "Sobrecomprado"
        elif 60 <= ultima['RSI'] <= 70:
            rsi_status = "Comprado fraco"
        elif 30 <= ultima['RSI'] <= 40:
            rsi_status = "Vendido fraco"
        elif ultima['RSI'] < 30:
            rsi_status = "Sobrevendido"

        # Cruzamento Estocástico
        cruzamento = ""
        if df['%K'].iloc[-2] < df['%D'].iloc[-2] and df['%K'].iloc[-1] > df['%D'].iloc[-1]:
            cruzamento = "Cruzamento para CIMA"
        elif df['%K'].iloc[-2] > df['%D'].iloc[-2] and df['%K'].iloc[-1] < df['%D'].iloc[-1]:
            cruzamento = "Cruzamento para BAIXO"

        resultados.append({
            "Moeda": symbol,
            "RSI": round(ultima['RSI'], 2),
            "Status RSI": rsi_status,
            "Estocástico %K": round(ultima['%K'], 2),
            "Estocástico %D": round(ultima['%D'], 2),
            "Cruzamento Estocástico": cruzamento
        })

df_res = pd.DataFrame(resultados)
print(df_res)
