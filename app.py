import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time

# 1. Configuración de la página
st.set_page_config(
    page_title="AI & Tech Live Scalping Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Gestión dinámica de acciones en el estado de la sesión
if "tickers" not in st.session_state:
    st.session_state.tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM", "IONQ"]

# 3. Función optimizada para datos en Tiempo Real / Corto Plazo (Velas de 1 minuto)
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # ACTUALIZACIÓN MÁXIMA: Últimos 5 días con velas de 1 minuto
        # Nota: '1m' solo permite extraer un máximo de 7 días atrás de historial.
        df = ticker.history(period="5d", interval="1m") 
        
        if df.empty or len(df) < 50:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2])
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo del RSI (14) basado en las últimas 14 velas de 1 minuto (Últimos 14 minutos)
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_actual = round(float((100 - (100 / (1 + rs))).iloc[-1]), 2)

        # Soporte dinámico rápido: Media Móvil de 50 períodos (últimos 50 minutos)
        sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1])
        
        # Máximos y mínimos de los últimos 5 días para Scalping
        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())

        # RECOMENDACIÓN TÁCTICA: Umbrales ajustados a 35 y 65 para scalping agresivo
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            badge = "COMPRA"
            nota = "RSI en sobreventa rápida (<=35). Excelente ventana si el precio coquetea con el soporte."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            badge = "VENTA"
            nota = "RSI en sobrecompra (>=65). Riesgo alto de retroceso. Ideal para tomar ganancias o ajustar SL."
        else:
            senal = "🟡 MONITORIZAR"
            badge = "ESPERAR"
            nota = "Precio en rango neutral de corto plazo. Paciencia; espera aproximación a zonas clave."

        # STOP LOSS ESTRÍCTO: 1.5% por debajo del soporte para proteger cuentas con x5 o x10
        soporte_estimado = round(sma_50 * 0.995, 2)
        stop_loss_recomendado = round(soporte_estimado * 0.985, 2)

        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.015, 2), 
            "stop_loss": stop_loss_recomendado,
            "target": round(precio_actual * 1.03, 2),
            "min_5d": min_periodo,
            "max_5d": max_periodo,
            "senal": senal,
            "badge": badge,
            "nota": nota
        }
    except:
        return None

# --- PANEL DE CONTROL LATERAL (Gestión Dinámica de Activos) ---
st.sidebar.markdown("## 🛠️ Panel de Control")

# Sección 1: Añadir Acción de forma dinámica
nuevo_ticker = st.sidebar.text_input("Añadir símbolo (Ej: TSLA, AAPL, BTC-USD, IONQ):").upper().strip()
if st.sidebar.button("➕ Añadir Acción"):
    if nuevo_ticker and nuevo_ticker not in st.session_state.tickers:
        try:
            test_ticker = yf.Ticker(nuevo_ticker)
            test_df = test_ticker.history(period="1d")
            if not test_df.empty:
                st.session_state.tickers.append(nuevo_ticker)
                st.sidebar.success(f"{nuevo_ticker} añadido!")
                st.rerun()
            else:
                st.sidebar.error("Símbolo no encontrado en Yahoo Finance.")
        except:
            st.sidebar.error("Error al validar el símbolo.")

# Sección 2: Eliminar Acción de forma dinámica
st.sidebar.markdown("---")
if len(st.session_state.tickers) > 0:
    ticker_a_eliminar = st.sidebar.selectbox("Eliminar una acción:", st.session_state.tickers)
    if st.sidebar.button("🗑️ Eliminar Acción"):
        st.session_state.tickers.remove(ticker_a_eliminar)
        st.sidebar.warning(f"{ticker_a_eliminar} eliminado.")
        st.rerun()

# Sección 3: Selección de enfoque táctico
st.sidebar.markdown("---")
if st.session_state.tickers:
    seleccionado = st.sidebar.selectbox("🎯 ACCIÓN EN ENFOQUE:", st.session_state.tickers)
else:
    st.info("Añade una acción desde la barra lateral para empezar.")
    st.stop()


# --- INTERFAZ GRÁFICA PRINCIPAL ---
st.title("⚡ AI Day Trading Scalper Dashboard (1m Live)")
st.caption(f"Velocidad de mercado: Velas de 1 minuto — Auto-refresco activado (Cada 15s) — Última actualización: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# Layout de dos columnas principales
col_izq, col_der = st.columns([1.1, 1])

# --- COLUMNA IZQUIERDA: LISTA DE MONITORIZACIÓN ---
with col_izq:
    st.markdown("### 📋 Monitor de Scalping Activo")
    
    for t in st.session_state.tickers:
        data = obtener_datos_ticker(t)
        if data:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    st.markdown(f"### **{t}**")
                    st.caption(data["senal"])
                with c2:
                    st.metric(
                        label="Precio Actual (1m)", 
                        value=f"${data['precio']:.2f}", 
                        delta=f"{data['cambio']:.2f}%"
                    )
                with c3:
                    st
