import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time

# 1. Configuración de la página estilo Terminal de Trading
st.set_page_config(
    page_title="AI & Tech Live Scalping Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Gestión dinámica de acciones en el estado de la sesión (Session State)
if "tickers" not in st.session_state:
    st.session_state.tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM", "IONQ"]

# 3. Función de extracción optimizada y blindada contra mercado cerrado
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Intento 1: Máxima resolución en tiempo real (Velas de 1 minuto de los últimos 3 días)
        df = ticker.history(period="3d", interval="1m") 
        
        # SISTEMA FALLBACK: Si el mercado está cerrado o la API de 1m no responde, bajamos la resolución
        if df.empty or len(df) < 15:
            # Plan B: Velas de 15 minutos de los últimos 5 días
            df = ticker.history(period="5d", interval="15m")
            if df.empty:
                # Plan C: Historial diario del último mes (Garantiza datos históricos en fin de semana)
                df = ticker.history(period="1mo", interval="1d")

        if df.empty:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2]) if len(df) > 1 else precio_actual
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo seguro del RSI (14 períodos)
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi_series.iloc[-1]), 2) if not rsi_series.empty else 50.0

        # Soporte dinámico rápido: Media Móvil de 50 períodos (SMA 50)
        window_size = min(50, len(df))
        sma
