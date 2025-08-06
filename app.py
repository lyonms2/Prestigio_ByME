import streamlit as st
import ccxt
import pandas as pd
from ta.trend import EMAIndicator
from datetime import datetime
import pytz

# Configuração da página
st.set_page_config(page_title="Análise Heikin-Ashi com Volume", layout="wide")

# Lista de pares fixos
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

# Inicializa KuCoin
exchange = ccxt.kucoin()

# Função para calcular Heikin Ashi
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

# Lógica para identificar tendência
def analyze_ha_trend(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['HA_Close'] < prev['HA_Open'] and last['HA_Close'] > last['HA_Open']:
        return "🔼 Reversão p/ Alta"
    elif prev['HA_Close'] > prev['HA_Open'] and last['HA_Close'] < last['HA_Open']:
        return "🔽 Reversão p/ Baixa"
    elif last['HA_Close'] > last['HA_Open'] and prev['HA_Close'] > prev['HA_Open']:
        return "🟢 Continuação de Alta"
    elif last['HA_Close'] < last['HA_Open'] and prev['HA_Close'] < prev['HA_Open']:
        return "🔴 Continuação de Baixa"
    else:
        return "🔍 Indefinido"

# Alerta de pico de volume
def detect_volume_spike(df, N=2):
    volumes = df['volume'][:-1]
    last_volume = df['volume'].iloc[-1]
    mean = volumes.mean()
    std = volumes.std()
    if last_volume > mean + N * std:
        return "🚨 Pico de Volume"
    return ""
# Classificação do RSI baseado no HA
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
        
# Função com cache de 30 minutos
@st.cache_data(ttl=1800)  # Atualiza a cada 1800 segundos = 30 minutos
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
            resultados.append((symbol, tendencia, volume_alerta))
        except Exception as e:
            resultados.append((symbol, f"Erro: {str(e)}", ""))
    return pd.DataFrame(resultados, columns=["Par", "Tendência", "Volume"])

# Título e informações
st.title("📊 Monitor de Criptomoedas - By XSpeck")
st.caption("🔁 Atualização automática a cada 30 minutos")

# Horário da última atualização

fuso_brasil = pytz.timezone("America/Sao_Paulo")
hora_brasil = datetime.now(fuso_brasil)
st.markdown(f"⏱️ Última atualização: **{hora_brasil.strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)**")


# Filtro de busca
filtro = st.text_input("🔍 Filtrar par (ex: BTC, ETH):", "").upper()

# Carregamento de dados
df_result = carregar_dados()

# Aplicar filtro se houver
if filtro:
    df_result = df_result[df_result["Par"].str.contains(filtro)]

# Exibir resultado
st.dataframe(df_result, use_container_width=True)

