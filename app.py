import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime
import pytz

# ---------- Config do CSV da planilha com usuários ativos ----------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcElw5weHbiGxzET7fbS8F3PfjBEfBbTRqH-FK4hOxt7ekTXRcrITxGMB6pMGjvM95b5fmnYiZAj46/pub?gid=0&single=true&output=csv"

def carregar_usuarios_ativos():
    df = pd.read_csv(URL_PLANILHA)
    ativos = df[df['status_plano'].str.upper() == "ACTIVE"]
    return ativos['email'].str.lower().dropna().tolist()

if "logado" not in st.session_state:
    st.session_state.logado = False

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
    # Link estilizado abaixo do botão
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
                display:inline-block;
                transition: background-color 0.3s;
                " onmouseover="this.style.backgroundColor='#ff1c1c'" onmouseout="this.style.backgroundColor='#ff4b4b'">
                🔥 Assinar Agora 🔥
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )            
    st.stop()

# Se chegou aqui, usuário está logado
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

# Corretoras ----
def binance_link(symbol):
    return f"https://www.binance.com/pt/trade/{symbol.replace('-USDT', '_USDT?type=cross')}"

def hyperliquid_link(symbol):    
    return f"https://app.hyperliquid.xyz/trade/{symbol.replace('-USDT', '')}"  

def bybit_link(symbol):    
    return f"https://www.bybit.com/trade/usdt/{symbol.replace('-', '')}"

def mexc_link(symbol):    
    return f"https://www.mexc.com/pt-BR/futures/{symbol.replace('-', '_')}"

def kucoin_link(symbol):    
    return f"https://www.kucoin.com/pt/trade/margin/{symbol}"
# Fim Corretoras -----

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

    # Se algum valor for NaN
    if pd.isna(last_k) or pd.isna(prev_k) or pd.isna(last_d) or pd.isna(prev_d):
        return None, "Indefinido"

    # Detecta cruzamento
    if prev_k <= prev_d and last_k > last_d:
        return last_k, "🚀 Cruzamento para cima"
    if prev_k >= prev_d and last_k < last_d:
        return last_k, "⛔ Cruzamento para baixo"

    # D subindo abaixo de K
    if last_d < last_k and last_d > prev_d:
        return last_k, "📈 Subindo"

    # D descendo acima de K
    if last_d > last_k and last_d < prev_d:
        return last_k, "📉 Descendo"

    # Caso nenhum dos acima
    return last_k, "⚪ Neutro"


st.title("📊 Monitor de Criptomoedas")

# ======================
# Escolha dos timeframes
# ======================
opcoes_timeframe = {
    "15 Minutos": "15m",
    "30 Minutos": "30m",
    "1 Hora": "1h",
    "2 Horas": "2h",
    "4 Horas": "4h",
    "Diário": "1d",
    "Semanal": "1w"
}

col1, col2, col3 = st.columns(3)
with col1:
    tf1_label = st.selectbox("⏳ Primeiro Timeframe", list(opcoes_timeframe.keys()), index=2)  # padrão 1h
with col2:
    tf2_label = st.selectbox("⏳ Segundo Timeframe", list(opcoes_timeframe.keys()), index=3)  # padrão 4h
with col3:
    corretora_label = st.selectbox("🏦 Corretora", ["Binance", "Bybit", "Hyperliquid", "mexc", "kucoin"], index=0)

tf1 = opcoes_timeframe[tf1_label]
tf2 = opcoes_timeframe[tf2_label]


# ====== Escolha do tipo de candle para indicadores ======
tipo_candle = st.radio(
    "📊 Tipo de Candle para Indicadores:",
    ["Heikin Ashi", "Velas Comuns"],
    index=0,
    horizontal=True
)

def carregar_dados(symbols):
    resultados = []
    progresso = st.progress(0)
    status_text = st.empty()
    total = len(symbols)
    for i, symbol in enumerate(symbols):
        status_text.text(f"Carregando dados: {symbol} ({i+1}/{total})")
        try:
            # -------- Timeframe 1 --------
            ohlcv_tf1 = exchange.fetch_ohlcv(symbol, timeframe=tf1, limit=100)
            df_tf1 = pd.DataFrame(ohlcv_tf1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_tf1['timestamp'] = pd.to_datetime(df_tf1['timestamp'], unit='ms')
            ha_df_tf1 = get_heikin_ashi(df_tf1)

            tendencia_tf1 = analyze_ha_trend(ha_df_tf1)
            volume_alerta_tf1 = detect_volume_spike(df_tf1)

            # Escolha de base para indicadores
            base_tf1 = ha_df_tf1 if tipo_candle == "Heikin Ashi" else df_tf1

            # RSI
            rsi_tf1 = RSIIndicator(close=base_tf1["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf1["close"], window=14).rsi()
            rsi_valor_tf1 = round(rsi_tf1.iloc[-1], 2)
            rsi_status_tf1 = f"{rsi_valor_tf1} - {classificar_rsi(rsi_valor_tf1)}"

            # Stoch RSI
            stochrsi_k_tf1, stochrsi_d_tf1 = calculate_stochrsi(base_tf1["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf1["close"])
            stoch_value_tf1, stoch_signal_tf1 = stochrsi_signal(stochrsi_k_tf1, stochrsi_d_tf1)
            stoch_str_tf1 = f"{round(stoch_value_tf1 * 100, 2)} ({stoch_signal_tf1})" if stoch_value_tf1 is not None else stoch_signal_tf1
        
            
            # EMA 20
            ema_tf1 = EMAIndicator(close=base_tf1["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf1["close"], window=20).ema_indicator()
            ema_signal_tf1 = " ⬆️ 🟢 " if (base_tf1["HA_Close"].iloc[-1] if tipo_candle == "Heikin Ashi" else base_tf1["close"].iloc[-1]) > ema_tf1.iloc[-1] else " ⬇️ 🔴 "

            # -------- Timeframe 2 --------
            ohlcv_tf2 = exchange.fetch_ohlcv(symbol, timeframe=tf2, limit=100)
            df_tf2 = pd.DataFrame(ohlcv_tf2, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_tf2['timestamp'] = pd.to_datetime(df_tf2['timestamp'], unit='ms')
            ha_df_tf2 = get_heikin_ashi(df_tf2)

            tendencia_tf2 = analyze_ha_trend(ha_df_tf2)
            volume_alerta_tf2 = detect_volume_spike(df_tf2)

            # Escolha de base para indicadores
            base_tf2 = ha_df_tf2 if tipo_candle == "Heikin Ashi" else df_tf2

            # RSI
            rsi_tf2 = RSIIndicator(close=base_tf2["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf2["close"], window=14).rsi()
            rsi_valor_tf2 = round(rsi_tf2.iloc[-1], 2)
            rsi_status_tf2 = f"{rsi_valor_tf2} - {classificar_rsi(rsi_valor_tf2)}"

            # Stoch RSI
            stochrsi_k_tf2, stochrsi_d_tf2 = calculate_stochrsi(base_tf2["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf2["close"])
            stoch_value_tf2, stoch_signal_tf2 = stochrsi_signal(stochrsi_k_tf2, stochrsi_d_tf2)
            stoch_str_tf2 = f"{round(stoch_value_tf2 * 100, 2)} ({stoch_signal_tf2})" if stoch_value_tf2 is not None else stoch_signal_tf2
            
            # EMA 20
            ema_tf2 = EMAIndicator(close=base_tf2["HA_Close"] if tipo_candle == "Heikin Ashi" else base_tf2["close"], window=20).ema_indicator()
            ema_signal_tf2 = " ⬆️ 🟢 " if (base_tf2["HA_Close"].iloc[-1] if tipo_candle == "Heikin Ashi" else base_tf2["close"].iloc[-1]) > ema_tf2.iloc[-1] else " ⬇️ 🔴 "

            resultados.append((
                symbol,
                tendencia_tf1, tendencia_tf2,
                rsi_status_tf1, rsi_status_tf2,
                stoch_str_tf1, stoch_str_tf2,
                ema_signal_tf1, ema_signal_tf2,
                volume_alerta_tf1, volume_alerta_tf2
            ))

        except Exception as e:
            resultados.append((symbol, f"Erro: {str(e)}", "", "", "", "", "", "", "", "", ""))

        progresso.progress((i+1) / total)

    status_text.text("Carregamento concluído!")

    return pd.DataFrame(
        resultados,
        columns=[
            "Par",
            f"Tendência {tf1_label}", f"Tendência {tf2_label}",
            f"RSI {tf1_label}", f"RSI {tf2_label}",
            f"Stoch RSI {tf1_label}", f"Stoch RSI {tf2_label}",
            f"EMA20 {tf1_label}", f"EMA20 {tf2_label}",
            f"Vol {tf1_label}", f"Vol {tf2_label}"
        ]
    )

# Edição Corretoras ---
corretoras_links = {
    "Binance": {
        "func": binance_link,
        "color": "#262624",
        "text_color": "white",
        "emoji": "🟠"
    },
    "Bybit": {
        "func": bybit_link,
        "color": "#262624",
        "text_color": "white",
        "emoji": "🟡"
    },
    "Hyperliquid": {
        "func": hyperliquid_link,
        "color": "#262624",
        "text_color": "white",
        "emoji": "🔵"
    },    
    "kucoin": {
        "func": kucoin_link,
        "color": "#262624",
        "text_color": "white",
        "emoji": "🟢"
    },
    "mexc": {
        "func": mexc_link,
        "color": "#262624",
        "text_color": "white",
        "emoji": "⚪"
    }
}

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
    filtro_principais_input = st.text_input("🔍 Pesquise uma ou mais Moedas Principais (separe por vírgula 😉)", key="filtro_principais").upper()
    
    if filtro_principais_input:
        # Definindo a lista de filtros
        filtros = [f.strip() for f in filtro_principais_input.split(",") if f.strip()]

        # Filtra se qualquer um dos termos aparecer no "Par"
        df_filtrado_principais = st.session_state.df_principais[
            st.session_state.df_principais["Par"].apply(
                lambda x: any(f in x for f in filtros)
            )
        ]

        if not df_filtrado_principais.empty:
            cols = st.columns(min(len(df_filtrado_principais), 5))

            for idx, par in enumerate(df_filtrado_principais["Par"]):
                url = tradingview_link(par)
                btn_html = f"""
                    <a href="{url}" target="_blank" style="
                        text-decoration:none;
                        color:white;
                        background-color:#07097d;
                        padding:4px 9px;
                        border-radius:3px;
                        display:inline-block;
                        margin: 2px 3px;
                        font-weight:bold;">
                        📊 {par}
                    </a>
                """
                link_func = corretoras_links[corretora_label]["func"]
                corr_url = link_func(par)
                corr_btn = f"""
                    <a href="{corr_url}" target="_blank" style="
                        text-decoration:none;
                        color:{corretoras_links[corretora_label]['text_color']};
                        background-color:{corretoras_links[corretora_label]['color']};
                        padding:4px 9px;
                        border-radius:3px;
                        font-weight:bold;">
                        {corretoras_links[corretora_label]['emoji']} {corretora_label}
                    </a>
                """
                cols[idx % 5].markdown(btn_html + corr_btn, unsafe_allow_html=True)

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
    filtro_restantes_input = st.text_input(
        "🔍 Pesquise uma ou mais outras Moedas (separe por vírgula 😉)",
        key="filtro_restantes"
    ).upper()

    if filtro_restantes_input:
        # Lista de termos para buscar
        filtros = [f.strip() for f in filtro_restantes_input.split(",") if f.strip()]

        # Filtra se qualquer termo aparecer no "Par"
        df_filtrado_restantes = st.session_state.df_restantes[
            st.session_state.df_restantes["Par"].apply(
                lambda x: any(f in x for f in filtros)
            )
        ]

        if not df_filtrado_restantes.empty:
            cols = st.columns(min(len(df_filtrado_restantes), 5))  # Máximo 5 colunas por linha

            for idx, par in enumerate(df_filtrado_restantes["Par"]):
                url = tradingview_link(par)
                btn_html = f"""
                    <a href="{url}" target="_blank" style="
                        text-decoration:none;
                        color:white;
                        background-color:#07097d;
                        padding:4px 9px;
                        border-radius:3px;
                        display:inline-block;
                        margin: 2px 3px;
                        font-weight:bold;
                        ">
                        📊 {par}
                    </a>
                """

                link_func = corretoras_links[corretora_label]["func"]
                corr_url = link_func(par)
                corr_btn = f"""
                    <a href="{corr_url}" target="_blank" style="
                        text-decoration:none;
                        color:{corretoras_links[corretora_label]['text_color']};
                        background-color:{corretoras_links[corretora_label]['color']};
                        padding:4px 9px;
                        border-radius:3px;
                        font-weight:bold;">
                        {corretoras_links[corretora_label]['emoji']} {corretora_label}
                     </a>
                 """

                cols[idx % 5].markdown(btn_html + corr_btn, unsafe_allow_html=True)

            st.dataframe(df_filtrado_restantes, use_container_width=True)

    else:
        st.dataframe(st.session_state.df_restantes, use_container_width=True)








