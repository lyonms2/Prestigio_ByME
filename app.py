import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz

st.set_page_config(page_title="Análise Heikin-Ashi com Volume, RSI e Stoch RSI", layout="wide")

# ====== LISTA DE PARES ======
symbols = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "XMR-USDT", "ENA-USDT", "DOGE-USDT",
    "ADA-USDT", "LTC-USDT", "SUI-USDT", "SEI-USDT", "PEPE-USDT", "LINK-USDT", "TON-USDT",
    "UNI-USDT", "AVAX-USDT", "TRX-USDT", "HBAR-USDT", "NEAR-USDT", "ONDO-USDT", "SHIB-USDT",
    "XLM-USDT", "DOT-USDT", "FET-USDT", "INJ-USDT", "WIF-USDT", "TIA-USDT", "BNB-USDT",
    "CRV-USDT", "VRA-USDT", "XPR-USDT", "CFX-USDT", "BCH-USDT", "ARB-USDT", "KAS-USDT",
    "AAVE-USDT", "APT-USDT", "ICP-USDT"
]

exchange = ccxt.kucoin()

# ====== FUNÇÕES BASE ======
def get_heikin_ashi(df):
    ha_df = df.copy()
    ha_df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'][0] + df['close'][0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_df['HA_Close'][i-1]) / 2)
    ha_df['HA_Open'] = ha_open
    ha_df['HA_High'] = ha_df[['HA_Open', 'HA_Close', 'high']].max(axis=1)
    ha_df['HA_Low'] = ha_df[['HA_Open', 'HA_Close', 'low']].min(axis=1)
    return ha_df[['timestamp', 'HA_Open', 'HA_High', 'HA_Low', 'HA_Close']]

def analyze_ha_trend(df):
    if len(df) < 2:
        return "Sem dados"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    last_bull = last['HA_Close'] > last['HA_Open']
    count = 1
    for i in range(len(df)-2, -1, -1):
        if (df.iloc[i]['HA_Close'] > df.iloc[i]['HA_Open']) == last_bull:
            count += 1
        else:
            break
    if prev['HA_Close'] < prev['HA_Open'] and last['HA_Close'] > last['HA_Open']:
        return "🔼 Reversão Alta"
    elif prev['HA_Close'] > prev['HA_Open'] and last['HA_Close'] < last['HA_Open']:
        return "🔽 Reversão Baixa"
    elif last_bull:
        return f"🟢 Alta ({count})"
    else:
        return f"🔴 Baixa ({count})"

def detect_volume_spike(df, N=2):
    if len(df) < 2:
        return ""
    last_volume = df['volume'].iloc[-1]
    mean = df['volume'][:-1].mean()
    std = df['volume'][:-1].std()
    return "🚨 Pico" if last_volume > mean + N * std else ""

def classificar_rsi(valor):
    if valor > 70:
        return "🚨 Sobrecomprado"
    elif valor > 60:
        return "📈 Compra Fraca"
    elif valor > 40:
        return "⚪ Neutro"
    elif valor > 30:
        return "📉 Venda Fraca"
    else:
        return "🚨 Sobrevendido"

def calculate_stochrsi(close, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    rsi = RSIIndicator(close=close, window=rsi_period).rsi()
    min_rsi = rsi.rolling(window=stoch_period).min()
    max_rsi = rsi.rolling(window=stoch_period).max()
    k = ((rsi - min_rsi) / (max_rsi - min_rsi)).rolling(window=smooth_k).mean()
    d = k.rolling(window=smooth_d).mean()
    return k, d

def stochrsi_signal(k, d):
    if len(k) < 2 or len(d) < 2 or k.isna().any() or d.isna().any():
        return "Indefinido", None
    last_k, prev_k = k.iloc[-1], k.iloc[-2]
    last_d, prev_d = d.iloc[-1], d.iloc[-2]
    if last_d < last_k and last_d > prev_d:
        return "📈 Subindo", last_d
    if last_d > last_k and last_d < prev_d:
        return "📉 Descendo", last_d
    return "🚨 Cruzando", last_d

def tradingview_link(symbol):
    return f"https://www.tradingview.com/chart/?symbol=KUCOIN:{symbol.replace('-', '')}"

# ====== PROCESSAR UM SÍMBOLO ======
def processar_symbol(symbol):
    try:
        for tf in ["15m", "1h"]:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            ha_df = get_heikin_ashi(df)
            tendencia = analyze_ha_trend(ha_df)
            if tf == "15m":
                rsi_val = RSIIndicator(close=ha_df["HA_Close"], window=14).rsi().iloc[-1]
                rsi_status = f"{rsi_val:.2f} - {classificar_rsi(rsi_val)}"
                k, d = calculate_stochrsi(ha_df['HA_Close'])
                stoch_sig, stoch_val = stochrsi_signal(k, d)
                stoch_str = f"{stoch_sig} ({stoch_val*100:.1f}%)" if stoch_val is not None else stoch_sig
                vol = detect_volume_spike(df)
            if tf == "1h":
                tendencia_1h = tendencia
        return (symbol, tendencia, tendencia_1h, rsi_status, stoch_str, vol, tradingview_link(symbol))
    except Exception as e:
        return (symbol, f"Erro: {str(e)}", "", "", "", "", "")

# ====== CARREGAR DADOS ======
def carregar_dados():
    df = pd.DataFrame(
        [processar_symbol(s) for s in symbols],
        columns=["Par", "Tendência 15m", "Tendência 1h", "RSI", "Stoch RSI", "Volume", "TradingView"]
    )
    return df

# ====== COLORIR ======
def colorir_tendencia(val):
    if "Alta" in val:
        return "background-color: lightgreen; color: black"
    elif "Baixa" in val:
        return "background-color: lightcoral; color: black"
    elif "Reversão" in val:
        return "background-color: khaki; color: black"
    return ""

# ====== UI ======
st.title("📊 Monitor de Criptomoedas")
fuso = pytz.timezone("America/Sao_Paulo")
st.caption(f"⏱️ Última atualização: {datetime.now(fuso).strftime('%d/%m/%Y %H:%M:%S')}")

if "df" not in st.session_state:
    st.session_state.df = None

if st.button("🔄 Atualizar Dados"):
    st.session_state.df = carregar_dados()

if st.session_state.df is not None:
    styled_df = st.session_state.df.style.applymap(colorir_tendencia, subset=["Tendência 15m", "Tendência 1h"])
    st.dataframe(styled_df, use_container_width=True)
