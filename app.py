import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Analisador Heikin Ashi + Indicadores", layout="wide")

st.title("📊 Analisador Heikin Ashi + RSI + Estocástico")

# Entrada de dados
symbol = st.text_input("Par de moedas (ex: BTC-USDT)", value="BTC-USDT")
interval = st.selectbox("Intervalo", ["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
limit = st.slider("Quantidade de candles", 20, 500, 100)

if st.button("Analisar"):
    try:
        # Pegando dados da API da Binance
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol.replace('-', '')}&interval={interval}&limit={limit}"
        data = requests.get(url).json()
        
        # Criando DataFrame
        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        
        # Convertendo para numérico
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

        # Criando candles Heikin Ashi
        ha_df = df.copy()
        ha_df["ha_close"] = (ha_df["open"] + ha_df["high"] + ha_df["low"] + ha_df["close"]) / 4
        ha_df["ha_open"] = 0.0
        ha_df.loc[0, "ha_open"] = (ha_df.loc[0, "open"] + ha_df.loc[0, "close"]) / 2

        for i in range(1, len(ha_df)):
            ha_df.loc[i, "ha_open"] = (ha_df.loc[i-1, "ha_open"] + ha_df.loc[i-1, "ha_close"]) / 2

        ha_df["ha_high"] = ha_df[["high", "ha_open", "ha_close"]].max(axis=1)
        ha_df["ha_low"] = ha_df[["low", "ha_open", "ha_close"]].min(axis=1)

        # RSI
        def rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        ha_df["RSI"] = rsi(ha_df["ha_close"])

        # Estocástico
        low_min = ha_df["low"].rolling(window=14).min()
        high_max = ha_df["high"].rolling(window=14).max()
        ha_df["%K"] = ((ha_df["close"] - low_min) / (high_max - low_min)) * 100
        ha_df["%D"] = ha_df["%K"].rolling(window=3).mean()

        # Identificação de troca de cor no último candle
        last_color = "Alta" if ha_df.iloc[-2]["ha_close"] > ha_df.iloc[-2]["ha_open"] else "Baixa"
        current_color = "Alta" if ha_df.iloc[-1]["ha_close"] > ha_df.iloc[-1]["ha_open"] else "Baixa"
        troca_cor = last_color != current_color

        # Cruzamento do estocástico
        cruzamento_cima = ha_df.iloc[-2]["%K"] < ha_df.iloc[-2]["%D"] and ha_df.iloc[-1]["%K"] > ha_df.iloc[-1]["%D"]
        cruzamento_baixo = ha_df.iloc[-2]["%K"] > ha_df.iloc[-2]["%D"] and ha_df.iloc[-1]["%K"] < ha_df.iloc[-1]["%D"]

        # Exibição
        st.subheader("📈 Últimos Candles")
        st.dataframe(ha_df[["ha_open", "ha_high", "ha_low", "ha_close", "RSI", "%K", "%D"]].tail(10))

        st.subheader("📌 Sinais")
        st.write(f"Troca de cor no último candle: **{'Sim' if troca_cor else 'Não'}**")
        st.write(f"Cruzamento Estocástico para cima: **{'Sim' if cruzamento_cima else 'Não'}**")
        st.write(f"Cruzamento Estocástico para baixo: **{'Sim' if cruzamento_baixo else 'Não'}**")
    
    except Exception as e:
        st.error(f"Erro: {e}")
