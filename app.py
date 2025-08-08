import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz

st.set_page_config(page_title="Análise Heikin-Ashi com Volume e RSI", layout="wide")

symbols = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "XMR-USDT", "ENA-USDT", "DOGE-USDT",
    "FARTCOIN-USDT", "ADA-USDT", "LTC-USDT", "SUI-USDT", "SEI-USDT", "PEPE-USDT", "LINK-USDT",
    "HYPE-USDT", "TON-USDT", "UNI-USDT", "PENGU-USDT", "AVAX-USDT", "TRX-USDT", "HBAR-USDT",
    "NEAR-USDT", "NODE-USDT", "ONDO-USDT", "SHIB-USDT", "TAO-USDT", "XLM-USDT", "TRUMP-USDT",
    "DOT-USDT", "FET-USDT", "INJ-USDT", "WIF-USDT", "TIA-USDT", "BNB-USDT", "ILV-USDT",
    "ZBCN-USDT", "IKA-USDT", "SUP-USDT", "GAIA-USDT", "BONK-USDT", "XU3O8-USDT", "NOBODY-USDT",
    "AGT-USDT", "URANUS-USDT", "A47-USDT", "SNAKES-USDT", "NEWT-USDT", "CRV-USDT", "TROLL-USDT",
    "VRA-USDT", "XPR-USDT", "USELESS-USDT", "THINK-USDT", "CFX-USDT", "SPX-USDT", "BCH-USDT",
    "ARB-USDT", "KAS-USDT", "S-USDT", "AAVE-USDT", "ES-USDT", "XNY-USDT", "OM-USDT", "MANYU-USDT",
    "ZRO-USDT", "ICNT-USDT", "ALGO-USDT", "HAIO-USDT", "APT-USDT", "ICP-USDT", "NOC-USDT"
]

exchange = ccxt.kucoin()

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
    # Conta quantas velas consecutivas têm mesma cor da última vela
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
        return "🔼 Reversão p/ Alta"
    elif prev['HA_Close'] > prev['HA_Open'] and last['HA_Close'] < last['HA_Open']:
        return "🔽 Reversão p/ Baixa"
    elif last_bull and prev['HA_Close'] > prev['HA_Open']:
        return f"🟢 Continuação de Alta ({count} velas)"
    elif not last_bull and prev['HA_Close'] < prev['HA_Open']:
        return f"🔴 Continuação de Baixa ({count} velas)"
    else:
        return "🔍 Indefinido"


def detect_volume_spike(df, N=2):
    volumes = df['volume'][:-1]
    last_volume = df['volume'].iloc[-1]
    mean = volumes.mean()
    std = volumes.std()
    if last_volume > mean + N * std:
        return "🚨 Pico de Volume"
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
    return f"https://www.tradingview.com/chart/?symbol=KUCOIN:{symbol.replace('-', '')}"

def carregar_dados():
    resultados = []
    for symbol in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='30m', limit=20)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            ha_df = get_heikin_ashi(df)

            tendencia = analyze_ha_trend(ha_df)
            volume_alerta = detect_volume_spike(df)

            rsi = RSIIndicator(close=ha_df["HA_Close"], window=14).rsi()
            rsi_valor = round(rsi.iloc[-1], 2)
            rsi_status = f"{rsi_valor} - {classificar_rsi(rsi_valor)}"

            resultados.append((symbol, tendencia, rsi_status, volume_alerta))
        except Exception as e:
            resultados.append((symbol, f"Erro: {str(e)}", "", ""))

    return pd.DataFrame(resultados, columns=["Par", "Tendência", "RSI", "Volume"])

st.title("📊 Monitor de Criptomoedas")
st.caption("🔄 Clique no botão abaixo para atualizar os dados")

fuso_brasil = pytz.timezone("America/Sao_Paulo")
hora_brasil = datetime.now(fuso_brasil)
st.markdown(f"⏱️ Última atualização: **{hora_brasil.strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)**")

if "df_result" not in st.session_state:
    st.session_state.df_result = None

if st.button("🔄 Atualizar Dados"):
    st.session_state.df_result = carregar_dados()

if st.session_state.df_result is not None:
    st.dataframe(st.session_state.df_result, use_container_width=True)

    filtro_link = st.text_input("🔍 Pesquise um par para abrir gráfico TradingView", "").upper()

    if filtro_link:
        filtrados = [par for par in st.session_state.df_result["Par"] if filtro_link in par]

        st.markdown("### 🔗 Gráficos TradingView")
        for par in filtrados:
            url = tradingview_link(par)
            # Botão estilizado via markdown + HTML para abrir nova aba
            btn_html = f"""
                <a href="{url}" target="_blank" style="
                    text-decoration:none;
                    color:white;
                    background-color:#4CAF50;
                    padding:8px 18px;
                    border-radius:6px;
                    display:inline-block;
                    margin: 4px 6px;
                    font-weight:bold;
                    ">
                    📊 {par}
                </a>
            """
            st.markdown(btn_html, unsafe_allow_html=True)

