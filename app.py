import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz

st.set_page_config(page_title="Monitor de Criptomoedas", layout="wide")

# ======================
# Lista de moedas principais
# ======================
symbols_principais = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "XMR-USDT", "ENA-USDT", "DOGE-USDT", "CRO-USDT", "FARTCOIN-USDT", "ADA-USDT", "LTC-USDT",
    "SUI-USDT", "SEI-USDT", "PEPE-USDT", "LINK-USDT", "HYPE-USDT", "TON-USDT", "UNI-USDT", "PENGU-USDT", "AVAX-USDT", "TRX-USDT", "HBAR-USDT",
    "NEAR-USDT", "ONDO-USDT", "SHIB-USDT", "TAO-USDT", "XLM-USDT", "DOT-USDT", "MNT-USDT", "FET-USDT", "INJ-USDT", "WIF-USDT", "TIA-USDT", "BNB-USDT",
    "BONK-USDT", "CRV-USDT", "XPR-USDT", "CFX-USDT", "SPX-USDT", "BCH-USDT", "ARB-USDT", "KAS-USDT", "S-USDT", "AAVE-USDT", "ALGO-USDT", "HAIO-USDT",
    "APT-USDT", "ICP-USDT", "PUMP-USDT", "POPCAT-USDT", "ATOM-USDT", "VET-USDT", "FIL-USDT", "JUP-USDT", "OP-USDT", "RAY-USDT", "SAND-USDT", "IOTA-USDT",
    "THETA-USDT", "PENDLE-USDT", "CAKE-USDT", "AERO-USDT", "GRT-USDT", "LDO-USDT", "IMX-USDT"
]

exchange = ccxt.kucoin()

# ======================
# Funções auxiliares
# ======================
def get_symbols_restantes():
    all_markets = exchange.load_markets()
    all_usdt_pairs = [m.replace("/", "-") for m in all_markets if m.endswith("/USDT")]
    excecoes = {"WAXP-USDT", "VAIOT-USDT", "BSV-USDT", "BIFIF-USDT", "ALT-USDT", "VRADOWN-USDT", "USDP-USDT"}  # moedas que não quer mostrar em "outras"
    return sorted([s for s in all_usdt_pairs if s not in symbols_principais and s not in excecoes])


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

def count_consecutive_candles(df):
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
    volumes = df['volume'][:-1]
    last_volume = df['volume'].iloc[-1]
    mean = volumes.mean()
    std = volumes.std()
    if last_volume > mean + N * std:
        return "🚨 Atenção"
    return ""

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

def tradingview_link(symbol):
    # Ajuste para transformar "BTC-USDT" em "BTCUSDT"
    return f"https://www.tradingview.com/chart/?symbol=KUCOIN:{symbol.replace('-', '')}"

def calculate_stochrsi(close, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    rsi = RSIIndicator(close=close, window=rsi_period).rsi()
    min_rsi = rsi.rolling(window=stoch_period).min()
    max_rsi = rsi.rolling(window=stoch_period).max()
    stochrsi_k = ((rsi - min_rsi) / (max_rsi - min_rsi)).rolling(window=smooth_k).mean()
    stochrsi_d = stochrsi_k.rolling(window=smooth_d).mean()
    return stochrsi_k, stochrsi_d

def stochrsi_signal(stochrsi_k, stochrsi_d):
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

def carregar_dados(symbols):
    resultados = []
    progresso = st.progress(0)
    status_text = st.empty()
    total = len(symbols)
    for i, symbol in enumerate(symbols):
        status_text.text(f"Carregando dados: {symbol} ({i+1}/{total})")
        try:
            ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms')
            ha_df_1h = get_heikin_ashi(df_1h)

            tendencia_1h = analyze_ha_trend(ha_df_1h)
            volume_alerta = detect_volume_spike(df_1h)
            rsi_1h = RSIIndicator(close=ha_df_1h["HA_Close"], window=14).rsi()
            rsi_valor_1h = round(rsi_1h.iloc[-1], 2)
            rsi_status_1h = f"{rsi_valor_1h} - {classificar_rsi(rsi_valor_1h)}"
            stochrsi_k_1h, stochrsi_d_1h = calculate_stochrsi(ha_df_1h['HA_Close'])
            stoch_signal_1h, stoch_value_1h = stochrsi_signal(stochrsi_k_1h, stochrsi_d_1h)
            stoch_str_1h = f"{stoch_signal_1h} ({round(stoch_value_1h, 2)})" if stoch_value_1h is not None else stoch_signal_1h

            ohlcv_4h = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
            df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_4h['timestamp'] = pd.to_datetime(df_4h['timestamp'], unit='ms')
            ha_df_4h = get_heikin_ashi(df_4h)

            tendencia_4h = analyze_ha_trend(ha_df_4h)
            volume_alerta_4h = detect_volume_spike(df_4h)
            rsi_4h = RSIIndicator(close=ha_df_4h["HA_Close"], window=14).rsi()
            rsi_valor_4h = round(rsi_4h.iloc[-1], 2)
            rsi_status_4h = f"{rsi_valor_4h} - {classificar_rsi(rsi_valor_4h)}"
            stochrsi_k_4h, stochrsi_d_4h = calculate_stochrsi(ha_df_4h['HA_Close'])
            stoch_signal_4h, stoch_value_4h = stochrsi_signal(stochrsi_k_4h, stochrsi_d_4h)
            stoch_str_4h = f"{stoch_signal_4h} ({round(stoch_value_4h, 2)})" if stoch_value_4h is not None else stoch_signal_4h

            resultados.append((symbol, tendencia_1h, tendencia_4h, rsi_status_1h, rsi_status_4h,
                               stoch_str_1h, stoch_str_4h, volume_alerta, volume_alerta_4h))
        except Exception as e:
            resultados.append((symbol, f"Erro: {str(e)}", "", "", "", "", "", "", ""))
        progresso.progress((i+1) / total)
    status_text.text("Carregamento concluído!")
    return pd.DataFrame(resultados, columns=["Par", "Tendência 1h", "Tendência 4h", "RSI 1h", "RSI 4h", "Stoch RSI 1h", "Stoch RSI 4h", "Vol 1h", "Vol 4h"])

# ======================
# Interface
# ======================

st.title("📊 Monitor de Criptomoedas")

def hora_atual_formatada():
    return datetime.now(pytz.timezone("America/Sao_Paulo")).strftime('%d/%m/%Y %H:%M:%S')

# Sessões
if "df_principais" not in st.session_state:
    st.session_state.df_principais = None
if "df_restantes" not in st.session_state:
    st.session_state.df_restantes = None
if "hora_principais" not in st.session_state:
    st.session_state.hora_principais = None
if "hora_restantes" not in st.session_state:
    st.session_state.hora_restantes = None

# --- Moedas Principais ---
st.subheader("🏆 Moedas Principais")
if st.button("🔄 Atualizar Dados", key="btn_atualizar_principais"):
    st.session_state.df_principais = carregar_dados(symbols_principais)
    st.session_state.hora_principais = hora_atual_formatada()

if st.session_state.hora_principais:
    st.caption(f"⏱️ Última atualização: {st.session_state.hora_principais}")

if st.session_state.df_principais is not None:
    filtro_principais = st.text_input("🔍 Pesquise um par em Moedas Principais", key="filtro_principais").upper()
    
    if filtro_principais:
        df_filtrado_principais = st.session_state.df_principais[
            st.session_state.df_principais["Par"].str.contains(filtro_principais)
        ]
        
        if not df_filtrado_principais.empty:
            
            cols = st.columns(min(len(df_filtrado_principais), 5))  # Máximo 5 colunas por linha
            
            for idx, par in enumerate(df_filtrado_principais["Par"]):
                url = tradingview_link(par)
                btn_html = f"""
                    <a href="{url}" target="_blank" style="
                        text-decoration:none;
                        color:white;
                        background-color:#002efb;
                        padding:4px 9px;
                        border-radius:3px;
                        display:inline-block;
                        margin: 2px 3px;
                        font-weight:bold;
                        ">
                        📊 {par}
                    </a>
                """
                cols[idx % 5].markdown(btn_html, unsafe_allow_html=True)
        st.dataframe(df_filtrado_principais, use_container_width=True)
    else:
        st.dataframe(st.session_state.df_principais, use_container_width=True)

# --- Outras Moedas ---
st.subheader("📋 Outras Moedas")
if st.button("🔄 Atualizar Dados", key="btn_atualizar_restantes"):
    symbols_restantes = get_symbols_restantes()
    st.session_state.df_restantes = carregar_dados(symbols_restantes)
    st.session_state.hora_restantes = hora_atual_formatada()

if st.session_state.hora_restantes:
    st.caption(f"⏱️ Última atualização: {st.session_state.hora_restantes}")

if st.session_state.df_restantes is not None:
    filtro_restantes = st.text_input("🔍 Pesquise um par em Outras Moedas", key="filtro_restantes").upper()
    
    if filtro_restantes:
        df_filtrado_restantes = st.session_state.df_restantes[
            st.session_state.df_restantes["Par"].str.contains(filtro_restantes)
        ]
        
        if not df_filtrado_restantes.empty:
            
            cols = st.columns(min(len(df_filtrado_restantes), 5))  # Máximo 5 colunas por linha
            
            for idx, par in enumerate(df_filtrado_restantes["Par"]):
                url = tradingview_link(par)
                btn_html = f"""
                    <a href="{url}" target="_blank" style="
                        text-decoration:none;
                        color:white;
                        background-color:#002efb;
                        padding:4px 9px;
                        border-radius:3px;
                        display:inline-block;
                        margin: 2px 3px;
                        font-weight:bold;
                        ">
                        📊 {par}
                    </a>
                """
                cols[idx % 5].markdown(btn_html, unsafe_allow_html=True)
        st.dataframe(df_filtrado_restantes, use_container_width=True)
    else:
        st.dataframe(st.session_state.df_restantes, use_container_width=True)








