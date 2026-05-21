import datetime
import yfinance as yf
import pandas as pd
import streamlit as st

# 1. Configuración de la página
st.set_page_config(
    page_title="AI & Tech Growth Tracker",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Función limpia para extraer métricas de Yahoo Finance
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="6mo") 
        
        if df.empty or len(df) < 15:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2])
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo clásico del RSI
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_actual = round(float(100 - (100 / (1 + rs))).iloc[-1]), 2)

        # Medias y soportes
        sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1])
        hist_1y = ticker.history(period="1y")
        min_52w = float(hist_1y["Low"].min())
        max_52w = float(hist_1y["High"].max())

        # Sistema de señales automatizado según RSI
        if rsi_actual < 42:
            senal = "🟢 OPORTUNIDAD DE COMPRA"
            nota = "Activo sobrevendido o en fuerte descuento diario. Margen técnico excelente."
        else:
            senal = "🟡 ESPERAR / TOMAR GANANCIAS"
            nota = "Precio en equilibrio relativo o sobrecomprado. Monitorear retrocesos a soportes."

        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100), # Asegurar rango 0-100 para la barra
            "soporte": round(sma_50 * 0.96, 2),
            "resistencia": round(precio_actual * 1.08, 2),
            "stop_loss": round(sma_50 * 0.91, 2),
            "target": round(precio_actual * 1.25, 2),
            "min_52w": min_52w,
            "max_52w": max_52w,
            "senal": senal,
            "nota": nota
        }
    except:
        return None

# --- ESTRUCTURA VISUAL ---
st.title("🎯 Tech & Growth Live Dashboard")
st.subheader("Monitoreo Técnico Automatizado para Operaciones en eToro")
st.markdown("---")

# Tus 8 activos de inversión agresiva
tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM"]

# Barra lateral para elegir el enfoque de trading
seleccionado = st.sidebar.selectbox("🎯 ENFOQUE DE TRADING:", tickers)

# División en dos columnas de Streamlit nativas
col_izq, col_der = st.columns([1.1, 1])

# --- COLUMNA IZQUIERDA: LISTA DE ACCIONES ---
with col_izq:
    st.markdown("### 📋 Lista de Seguimiento General")
    
    for t in tickers:
        data = obtener_datos_ticker(t)
        if data:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    st.markdown(f"### **{t}**")
                    st.caption(data["senal"])
                with c2:
                    st.metric(
                        label="Precio Actual", 
                        value=f"${data['precio']:.2f}", 
                        delta=f"{data['cambio']:.2f}%"
                    )
                with c3:
                    st.markdown(f"**Soporte:** ${data['soporte']:.2f}")
                    st.markdown(f"**RSI:** {data['rsi']}")
                    st.progress(data["rsi"] / 100)

# --- COLUMNA DERECHA: PANEL TÁCTICO DETALLADO (EL QUE MOSTRABA CÓDIGO) ---
with col_der:
    st.markdown(f"### 🔍 Foco de Operación Inmediata: {seleccionado}")
    main = obtener_datos_ticker(seleccionado)
    
    if main:
        # Contenedor principal destacado
        with st.container(border=True):
            st.header(f"💰 {seleccionado} — ${main['precio']:.2f}")
            st.metric(label="Variación diaria", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            
            # Bloque de Sugerencia/Alerta
            st.info(f"**{main['senal']}**\n\n{main['nota']}")
            
            st.markdown("#### 🛠️ Parámetros de Configuración en eToro")
            
            # Tres columnas nativas para los objetivos de trading
            met1, met2, met3 = st.columns(3)
            with met1:
                st.metric(label="🎯 Entrada Estimada", value=f"${main['soporte']:.2f}")
            with met2:
                st.metric(label="🛑 Stop Loss Sugerido", value=f"${main['stop_loss']:.2f}")
            with met3:
                st.metric(label="🏆 Objetivo (Target)", value=f"${main['target']:.2f}")
            
            st.markdown("---")
            
            # Indicador de Fuerza Relativa (RSI)
            st.markdown(f"**Fuerza de Mercado (RSI Diario):** {main['rsi']} / 100")
            st.progress(main["rsi"] / 100)
            st.caption("Fórmula: Corto de 30 = Sobrevendido (Comprar) | Sobre 70 = Muy Caro (Esperar)")
            
            st.markdown("---")
            
            # Rangos anuales históricos
            st.markdown("**Rango de precios de las últimas 52 semanas:**")
            st.slider(
                label="Desplazamiento Anual (Mínimo vs Máximo)",
                min_value=main["min_52w"],
                max_value=main["max_52w"],
                value=main["precio"],
                disabled=True
            )
