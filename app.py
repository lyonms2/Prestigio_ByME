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
    if pd.isna(last_k) or pd.isna(prev_k) or pd.isna(last_d) or pd.isna(prev_d):
        return "Indefinido", None
    if last_d < last_k and last_d > prev_d:
        return "📈 Subindo", last_d
    if last_d > last_k and last_d < prev_d:
        return "📉 Descendo", last_d
    return "🚨 Cruzando", last_d

st.title("📊 Monitor de Criptomoedas")

# ======================
# Escolha dos timeframes
# ======================
opcoes_timeframe = {
    "15 Minutos": "15m",
    "30 Minutos": "30m",
    "1 Hora": "1h",
    "4 Horas": "4h",
    "Diário": "1d"
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
    """
    Função principal para carregar dados de múltiplos símbolos, calcular indicadores técnicos
    e sinais UT Bot Alert para dois timeframes diferentes, retornando um DataFrame consolidado.
    """
    resultados = []
    progresso = st.progress(0)
    status_text = st.empty()
    total = len(symbols)

    # Loop pelos símbolos selecionados
    for i, symbol in enumerate(symbols):
        status_text.text(f"Carregando dados: {symbol} ({i+1}/{total})")
        try:
            # ---------------------- Timeframe 1 ----------------------
            df_tf1 = obter_dados(symbol, tf1)  # Puxa OHLCV e converte timestamp
            base_tf1 = get_base_candle(df_tf1)  # Seleciona Heikin Ashi ou velas comuns
            sinais_tf1 = calcular_sinais(base_tf1, df_tf1)  # Calcula RSI, Stoch RSI, EMA20, UT Bot e volume

            # ---------------------- Timeframe 2 ----------------------
            df_tf2 = obter_dados(symbol, tf2)
            base_tf2 = get_base_candle(df_tf2)
            sinais_tf2 = calcular_sinais(base_tf2, df_tf2)

            # ---------------------- Consolidar resultados ----------------------
            resultados.append((
                symbol,
                sinais_tf1['tendencia'], sinais_tf2['tendencia'],
                sinais_tf1['rsi'], sinais_tf2['rsi'],
                sinais_tf1['stoch'], sinais_tf2['stoch'],
                sinais_tf1['ema'], sinais_tf2['ema'],
                sinais_tf1['volume'], sinais_tf2['volume'],
                sinais_tf1['ut'], sinais_tf2['ut']
            ))

        except Exception as e:
            # Em caso de erro, mantém o símbolo mas deixa colunas vazias
            resultados.append((symbol, f"Erro: {str(e)}", "", "", "", "", "", "", "", "", "", "", ""))

        progresso.progress((i + 1) / total)

    status_text.text("Carregamento concluído!")

    # ---------------------- Retornar DataFrame ----------------------
    return pd.DataFrame(
        resultados,
        columns=[
            "Par",
            f"Tendência {tf1_label}", f"Tendência {tf2_label}",
            f"RSI {tf1_label}", f"RSI {tf2_label}",
            f"Stoch RSI {tf1_label}", f"Stoch RSI {tf2_label}",
            f"EMA20 {tf1_label}", f"EMA20 {tf2_label}",
            f"Vol {tf1_label}", f"Vol {tf2_label}",
            f"UT Bot {tf1_label}", f"UT Bot {tf2_label}"
        ]
    )

# ---------------------- Funções auxiliares ----------------------
def obter_dados(symbol, timeframe):
    """
    Busca OHLCV de um símbolo em determinado timeframe e retorna DataFrame com timestamp convertido
    """
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def get_base_candle(df):
    """
    Retorna o DataFrame base de velas dependendo da configuração do usuário
    """
    if tipo_candle == "Heikin Ashi":
        return get_heikin_ashi(df)
    else:
        return df

def calcular_sinais(base_df, raw_df):
    """
    Calcula indicadores e sinais técnicos para o DataFrame base:
    - Tendência Heikin Ashi
    - Volume spike
    - RSI
    - Stoch RSI
    - EMA20
    - UT Bot Alert
    """
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

    return {
        "tendencia": tendencia,
        "volume": volume,
        "rsi": rsi,
        "stoch": stoch,
        "ema": ema,
        "ut": ut
    }


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

