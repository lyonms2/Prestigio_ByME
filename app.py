import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime
import pytz

# -------------------------------
# Configuração da planilha CSV
# -------------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcElw5weHbiGxzET7fbS8F3PfjBEfBbTRqH-FK4hOxt7ekTXRcrITxGMB6pMGjvM95b5fmnYiZAj46/pub?gid=0&single=true&output=csv"

# -------------------------------
# Função para carregar usuários ativos
# -------------------------------
def carregar_usuarios_ativos():
    df = pd.read_csv(URL_PLANILHA)
    ativos = df[df['status_plano'].str.upper() == "ACTIVE"]
    return ativos['email'].str.lower().dropna().tolist()

# -------------------------------
# Inicializa sessão de login
# -------------------------------
if "logado" not in st.session_state:
    st.session_state.logado = False

# -------------------------------
# Tela de login
# -------------------------------
if not st.session_state.logado:
    st.title("🔒 Acesso Restrito")
    email = st.text_input("Digite seu e-mail cadastrado")
    if st.button("Entrar"):
        usuarios_ativos = carregar_usuarios_ativos()
        if email.lower() in usuarios_ativos:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error(" ❌ E-mail não autorizado ou assinatura inativa.")
    
    # Link para assinatura
    st.markdown(
        """
        <div style="text-align:center; margin-top:10px;">
            <a href="https://go.hotmart.com/U101275018E" target="_blank" style="
                background: linear-gradient(90deg, #ff6600, #ff3300);
                color:white;
                padding:10px 20px;
                text-decoration:none;
                border-radius:8px;
                font-weight:bold;
                display:inline-block;">
                🔥 Assinar Agora 🔥
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )            
    st.stop()

# -------------------------------
# Página principal após login
# -------------------------------
st.set_page_config(page_title="Monitor de Criptomoedas", layout="wide")
st.title("📊 Monitor de Criptomoedas")

# -------------------------------
# Configurações iniciais
# -------------------------------
exchange = ccxt.kucoin()

symbols_principais = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "XMR-USDT",
    "ENA-USDT", "DOGE-USDT", "CRO-USDT", "FARTCOIN-USDT", "ADA-USDT",
    "LTC-USDT", "SUI-USDT", "SEI-USDT", "PEPE-USDT", "LINK-USDT",
    "HYPE-USDT", "TON-USDT", "UNI-USDT", "PENGU-USDT", "AVAX-USDT",
    "TRX-USDT", "HBAR-USDT", "NEAR-USDT", "ONDO-USDT", "SHIB-USDT",
    "TAO-USDT", "XLM-USDT", "DOT-USDT", "MNT-USDT", "FET-USDT",
    "INJ-USDT", "WIF-USDT", "TIA-USDT", "BNB-USDT", "BONK-USDT",
    "CRV-USDT", "XPR-USDT", "CFX-USDT", "SPX-USDT", "BCH-USDT",
    "ARB-USDT", "KAS-USDT", "S-USDT", "AAVE-USDT", "ALGO-USDT",
    "HAIO-USDT", "APT-USDT", "ICP-USDT", "PUMP-USDT", "POPCAT-USDT",
    "ATOM-USDT", "VET-USDT", "FIL-USDT", "JUP-USDT", "OP-USDT",
    "RAY-USDT", "SAND-USDT", "IOTA-USDT", "THETA-USDT", "PENDLE-USDT",
    "CAKE-USDT", "AERO-USDT", "GRT-USDT", "LDO-USDT", "IMX-USDT"
]

# -------------------------------
# Funções de análise de candles
# -------------------------------
def get_heikin_ashi(df):
    """Converte velas comuns em Heikin Ashi"""
    ha_df = df.copy()
    ha_df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'][0] + df['close'][0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_df['HA_Close'][i-1]) / 2)
    ha_df['HA_Open'] = ha_open
    ha_df['HA_High'] = ha_df[['HA_Open', 'HA_Close', 'high']].max(axis=1)
    ha_df['HA_Low'] = ha_df[['HA_Open', 'HA_Close', 'low']].min(axis=1)
    return ha_df[['timestamp', 'HA_Open', 'HA_High', 'HA_Low', 'HA_Close']]

def count_consecutive_candles(df):
    """Conta velas consecutivas de alta ou baixa"""
    last_bull = df.iloc[-1]['HA_Close'] > df.iloc[-1]['HA_Open']
    count = 0
    for i in range(len(df)-1, -1, -1):
        is_bull = df.iloc[i]['HA_Close'] > df.iloc[i]['HA_Open']
        if is_bull == last_bull:
            count += 1
        else:
            break
    return count, last_bull

def analyze_ha_trend(df):
    """Analisa tendência usando Heikin Ashi"""
    count, last_bull = count_consecutive_candles(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['HA_Close'] < prev['HA_Open'] and last['HA_Close'] > last['HA_Open']:
        return "🔼 Reversão Alta"
    elif prev['HA_Close'] > prev['HA_Open'] and last['HA_Close'] < last['HA_Open']:
        return "🔽 Reversão Baixa"
    elif last_bull and prev['HA_Close'] > prev['HA_Open']:
        return f"🟢 Alta ({count} velas)"
    elif not last_bull and prev['HA_Close'] < prev['HA_Open']:
        return f"🔴 Baixa ({count} velas)"
    else:
        return "🔍 Indefinido"

def detect_volume_spike(df, N=2):
    """Detecta aumento de volume"""
    volumes = df['volume'][:-1]
    last_volume = df['volume'].iloc[-1]
    mean = volumes.mean()
    std = volumes.std()
    if last_volume > mean + N * std:
        return "🚨 Atenção"
    return ""

def classificar_rsi(valor):
    """Classifica RSI"""
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
    """Calcula Stoch RSI"""
    rsi = RSIIndicator(close=close, window=rsi_period).rsi()
    min_rsi = rsi.rolling(window=stoch_period).min()
    max_rsi = rsi.rolling(window=stoch_period).max()
    stochrsi_k = ((rsi - min_rsi) / (max_rsi - min_rsi)).rolling(window=smooth_k).mean()
    stochrsi_d = stochrsi_k.rolling(window=smooth_d).mean()
    return stochrsi_k, stochrsi_d

def stochrsi_signal(stochrsi_k, stochrsi_d):
    """Gera sinal de Stoch RSI"""
    last_k = stochrsi_k.iloc[-1]
    prev_k = stochrsi_k.iloc[-2]
    last_d = stochrsi_d.iloc[-1]
    prev_d = stochrsi_d.iloc[-2]
    if pd.isna(last_k) or pd.isna(prev_k) or pd.isna(last_d) or pd.isna(prev_d):
        return "Indefinido", None
    if last_d < last_k and last_d > prev_d:
        return "📈 Subindo", last_d
    if last_d > last_k and last_d < prev_d:
        return "📉 Descendo", last_d
    return "🚨 Cruzando", last_d

# -------------------------------
# UT Bot Alert
# -------------------------------
def ut_bot_alert(df, candle_type="Heikin Ashi", atr_period=1, multiplier=2):
    """Sinal simplificado do UT Bot"""
    df = df.copy()
    df['UT_Signal'] = "Neutro"
    col = 'HA_Close' if candle_type == "Heikin Ashi" else 'close'
    for i in range(1, len(df)):
        if df[col].iloc[i] > df[col].iloc[i-1] + multiplier*df[col].iloc[i-1]*0.01:
            df.at[i, 'UT_Signal'] = "📈 Compra"
        elif df[col].iloc[i] < df[col].iloc[i-1] - multiplier*df[col].iloc[i-1]*0.01:
            df.at[i, 'UT_Signal'] = "📉 Venda"
    return df

# -------------------------------
# Funções de obtenção de dados e cálculos de indicadores
# -------------------------------
def obter_dados(symbol, timeframe):
    """Busca OHLCV de um símbolo e converte timestamp"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def get_base_candle(df):
    """Seleciona velas para indicadores (Heikin Ashi ou comum)"""
    return get_heikin_ashi(df) if tipo_candle == "Heikin Ashi" else df

def calcular_sinais(base_df, raw_df):
    """Calcula todos os indicadores e sinais"""
    # Tendência Heikin Ashi
    tendencia = analyze_ha_trend(get_heikin_ashi(raw_df))
    # Volume spike
    volume = detect_volume_spike(raw_df)
    # RSI
    close_col = base_df["HA_Close"] if tipo_candle == "Heikin Ashi" else base_df["close"]
    rsi_val = round(RSIIndicator(close=close_col, window=14).rsi().iloc[-1], 2)
    rsi = f"{rsi_val} - {classificar_rsi(rsi_val)}"
    # Stoch RSI
    stoch_k, stoch_d = calculate_stochrsi(close_col)
    stoch_signal, stoch_val = stochrsi_signal(stoch_k, stoch_d)
    stoch = f"{stoch_signal} ({round(stoch_val * 100, 2)})" if stoch_val is not None else stoch_signal
    # EMA20
    ema_val = EMAIndicator(close=close_col, window=20).ema_indicator().iloc[-1]
    ema = " ⬆️ 🟢 " if close_col.iloc[-1] > ema_val else " ⬇️ 🔴 "
    # UT Bot Alert
    ut_df = ut_bot_alert(base_df, candle_type=tipo_candle, atr_period=1, multiplier=2)
    ut = ut_df['UT_Signal'].iloc[-1]
    return {"tendencia": tendencia, "volume": volume, "rsi": rsi, "stoch": stoch, "ema": ema, "ut": ut}

# -------------------------------
# Função principal para carregar dados
# -------------------------------
def carregar_dados(symbols):
    resultados = []
    progresso = st.progress(0)
    status_text = st.empty()
    total = len(symbols)

    for i, symbol in enumerate(symbols):
        status_text.text(f"Carregando dados: {symbol} ({i+1}/{total})")
        try:
            # Timeframe 1
            df_tf1 = obter_dados(symbol, tf1)
            base_tf1 = get_base_candle(df_tf1)
            sinais_tf1 = calcular_sinais(base_tf1, df_tf1)
            # Timeframe 2
            df_tf2 = obter_dados(symbol, tf2)
            base_tf2 = get_base_candle(df_tf2)
            sinais_tf2 = calcular_sinais(base_tf2, df_tf2)
            # Monta resultado
            resultado = {
                "symbol": symbol,
                f"{tf1} Tendência": sinais_tf1["tendencia"],
                f"{tf1} Volume": sinais_tf1["volume"],
                f"{tf1} RSI": sinais_tf1["rsi"],
                f"{tf1} StochRSI": sinais_tf1["stoch"],
                f"{tf1} EMA20": sinais_tf1["ema"],
                f"{tf1} UT Bot": sinais_tf1["ut"],
                f"{tf2} Tendência": sinais_tf2["tendencia"],
                f"{tf2} Volume": sinais_tf2["volume"],
                f"{tf2} RSI": sinais_tf2["rsi"],
                f"{tf2} StochRSI": sinais_tf2["stoch"],
                f"{tf2} EMA20": sinais_tf2["ema"],
                f"{tf2} UT Bot": sinais_tf2["ut"],
                "Link": f"https://www.kucoin.com/trade/{symbol.replace('-', '_')}"
            }
            resultados.append(resultado)
        except Exception as e:
            resultados.append({"symbol": symbol, "erro": str(e)})
        progresso.progress((i+1)/total)
    return pd.DataFrame(resultados)

# -------------------------------
# Configurações do usuário
# -------------------------------
tipo_candle = st.selectbox("Tipo de Candle", ["Heikin Ashi", "Normal"])
tf1 = st.selectbox("Timeframe 1", ["1m","5m","15m","30m","1h","4h","1d"], index=4)
tf2 = st.selectbox("Timeframe 2", ["1m","5m","15m","30m","1h","4h","1d"], index=5)

# -------------------------------
# Botão para carregar dados
# -------------------------------
if st.button("🔄 Carregar Dados"):
    df_result = carregar_dados(symbols_principais)
    st.dataframe(df_result)
