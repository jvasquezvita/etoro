import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests

# 1. Configuración de la página estilo Terminal de Trading
st.set_page_config(
    page_title="AI & Tech Live Scalping Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# REEMPLAZA AQUÍ TU API KEY DE TWELVE DATA
# Consíguela gratis en twelvedata.com para activar el flujo nocturno en los activos disponibles
API_KEY_TWELVE = "a38e308378f54c20ba80c8992d919f1e"

# 2. LISTA CON EL ORDEN ESTRICTO SOLICITADO
if "tickers" not in st.session_state:
    st.session_state.tickers = [
        "VRT", "ANET", "NVDA", "AMD", "MU", 
        "ARM", "QCOM", "TSLA", "GOOG", "RKLB", 
        "SMCI", "BTC/USD"
    ]

if "seleccionado" not in st.session_state:
    st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None

# FUNCIÓN: Extracción del precio real de mercado extendido mediante Twelve Data
def obtener_precio_overnight_real(ticker_symbol):
    if API_KEY_TWELVE == "a38e308378f54c20ba80c8992d919f1e":
        return None
    try:
        url = f"https://api.twelvedata.com/price?symbol={ticker_symbol}&apikey={API_KEY_TWELVE}&include_pre_post=true"
        response = requests.get(url, timeout=5).json()
        if "price" in response:
            return float(response["price"])
    except:
        pass
    return None

# 3. Función híbrida (Precio en vivo de Twelve Data + Indicadores de estructura de Yahoo)
def obtener_datos_ticker(ticker_symbol):
    try:
        # Mapeo de formato para Yahoo Finance si el ticker es BTC/USD
        yf_symbol = "BTC-USD" if ticker_symbol == "BTC/USD" else ticker_symbol
        ticker = yf.Ticker(yf_symbol)
        
        # 1. Intentar capturar el precio Overnight real con Twelve Data
        precio_actual = obtener_precio_overnight_real(ticker_symbol)
        
        # 2. Descargamos el historial estructural para medias móviles y RSI
        df = ticker.history(period="5d", interval="15m", prepost=True) 

        if df.empty:
            df = ticker.history(period="1mo", interval="1d")

        if df.empty:
            return None

        # Fallback de respaldo si el activo está congelado de noche en la API pública o Twelve falla
        if not precio_actual:
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
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        
        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())

        if precio_actual < min_periodo: min_periodo = precio_actual * 0.99
        if precio_actual > max_periodo: max_periodo = precio_actual * 1.01

        # RECOMENDACIÓN TÁCTICA INTRADÍA
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            nota = f"RSI en sobreventa técnica ({rsi_actual}). Excelente ventana si el precio coquetea con el soporte."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            nota = f"RSI en sobrecompra técnica ({rsi_actual}). Riesgo alto de retroceso inmediato."
        else:
            senal = "🟡 MONITORIZAR"
            nota = f"Precio en equilibrio en gráfico rápido (RSI: {rsi_actual}). Esperar aproximación a zonas clave."

        soporte_estimado = round(sma_50 * 0.995, 2)
        stop_loss_recommended = round(soporte_estimado * 0.985, 2)

        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.015, 2), 
            "stop_loss": stop_loss_recommended,
            "target": round(precio_actual * 1.03, 2),
            "min_5d": min_periodo,
            "max_5d": max_periodo,
            "senal": senal,
            "nota": nota
        }
    except:
        return None

# --- PANEL DE CONTROL LATERAL ---
st.sidebar.markdown("## 🛠️ Panel de Control")

# Sección 1: Añadir Acción
nuevo_ticker = st.sidebar.text_input("Añadir símbolo manualmente (Ej: AVGO, META):").upper().strip()
if st.sidebar.button("➕ Añadir Acción"):
    if nuevo_ticker and nuevo_ticker not in st.session_state.tickers:
        try:
            yf_test = "BTC-USD" if nuevo_ticker == "BTC/USD" else nuevo_ticker
            test_ticker = yf.Ticker(yf_test)
            test_df = test_ticker.history(period="1d")
            if not test_df.empty:
                st.session_state.tickers.append(nuevo_ticker)
                st.session_state.seleccionado = nuevo_ticker
                st.sidebar.success(f"{nuevo_ticker} añadido!")
                st.rerun()
            else:
                st.sidebar.error("Símbolo no encontrado.")
        except:
            st.sidebar.error("Error al validar el símbolo.")

# Sección 2: Eliminar Acción
st.sidebar.markdown("---")
if len(st.session_state.tickers) > 0:
    ticker_a_eliminar = st.sidebar.selectbox("Eliminar una acción:", st.session_state.tickers, key="selectbox_eliminar")
    if st.sidebar.button("🗑️ Eliminar Acción"):
        st.session_state.tickers.remove(ticker_a_eliminar)
        if st.session_state.seleccionado == ticker_a_eliminar:
            st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None
        st.sidebar.warning(f"{ticker_a_eliminar} eliminado.")
        st.rerun()

# Sección 3: Selector de Enfoque Manual
st.sidebar.markdown("---")
if st.session_state.tickers:
    if st.session_state.seleccionado not in st.session_state.tickers:
        st.session_state.seleccionado = st.session_state.tickers[0]
        
    index_actual = st.session_state.tickers.index(st.session_state.seleccionado)
    selector_manual = st.sidebar.selectbox("🎯 ACCIÓN EN ENFOQUE:", st.session_state.tickers, index=index_actual)
    if selector_manual != st.session_state.seleccionado:
        st.session_state.seleccionado = selector_manual
        st.rerun()
else:
    st.info("Añade una acción para empezar.")
    st.stop()


# --- INTERFAZ GRÁFICA PRINCIPAL ---
st.title("⚡ AI & Tech Scalper Dashboard (Pure Tech 24h)")
st.caption(f"Frecuencia de refresco: Cada 15s sin bloqueos — Sincronización de terminal: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

col_izq, col_der = st.columns([1.1, 1])

# --- COLUMNA IZQUIERDA: MONITOR DE SCALPING INTERACTIVO ---
with col_izq:
