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
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        
        # Rangos históricos estables para la barra de progreso de 52 semanas
        hist_1y = ticker.history(period="1y")
        if not hist_1y.empty:
            min_periodo = float(hist_1y["Low"].min())
            max_periodo = float(hist_1y["High"].max())
        else:
            min_periodo = float(df["Low"].min())
            max_periodo = float(df["High"].max())

        # RECOMENDACIÓN TÁCTICA INTRADÍA: Umbrales ajustados a 35 y 65
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            badge = "COMPRA"
            nota = f"RSI en sobreventa rápida ({rsi_actual}). Excelente ventana si el precio coquetea con el soporte."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            badge = "VENTA"
            nota = f"RSI en sobrecompra ({rsi_actual}). Riesgo alto de retroceso técnico inmediato. Protege capital."
        else:
            senal = "🟡 MONITORIZAR"
            badge = "ESPERAR"
            nota = f"Precio en equilibrio en gráfico rápido (RSI: {rsi_actual}). Esperar aproximación a zonas clave."

        # CÁLCULO DE STOP LOSS GUÍA: 1.5% por debajo del soporte para absorber ruido en x5 o x10
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
st.title("⚡ AI Day Trading Scalper Dashboard")
st.caption(f"Frecuencia de monitoreo: Velas de 1 minuto — Auto-refresco (Cada 15s) — Sincronización: {datetime.datetime.now().strftime('%H:%M:%S')}")
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
                        label="Precio Actual", 
                        value=f"${data['precio']:.2f}", 
                        delta=f"{data['cambio']:.2f}%"
                    )
                with c3:
                    st.markdown(f"**Soporte:** ${data['soporte']:.2f}")
                    st.markdown(f"**RSI (1m):** {data['rsi']}")
                    st.progress(data["rsi"] / 100)

# --- COLUMNA DERECHA: ENFOQUE TÁCTICO APALANCADO ---
with col_der:
    st.markdown(f"### 🔍 Ejecución de Orden Corta: {seleccionado}")
    main = obtener_datos_ticker(seleccionado)
    
    if main:
        with st.container(border=True):
            st.header(f"📊 {seleccionado} — ${main['precio']:.2f}")
            st.metric(label="Último Precio Registrado", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            
            # Alerta de sugerencia dinámica
            st.info(f"**{main['senal']}**\n\n{main['nota']}")
            
            st.markdown("#### 🚨 Parámetros de Configuración Obligatoria para eToro (x5 / x10)")
            
            met1, met2, met3 = st.columns(3)
            with met1:
                st.metric(label="🎯 Entrada Óptima (Soporte)", value=f"${main['soporte']:.2f}")
            with met2:
                st.metric(label="🛑 Stop Loss Recomendado", value=f"${main['stop_loss']:.2f}")
            with met3:
                st.metric(label="🏆 Target de Salida Corto", value=f"${main['target']:.2f}")
            
            st.markdown("---")
            
            st.markdown(f"**RSI Inmediato (Últimas 14 velas):** {main['rsi']} / 100")
            st.progress(main["rsi"] / 100)
            
            st.markdown("---")
            
            st.markdown("**Rango de oscilación del precio (Histórico anual):**")
            st.slider(
                label="Rango de Volatilidad (Mín / Máx 52 Semanas)",
                min_value=main["min_5d"],
                max_value=main["max_5d"],
                value=main["precio"],
                disabled=True
            )

        # MANUAL EXPANDIBLE DE SEGURIDAD EN PANTALLA
        with st.expander("📚 CONSEJOS DE CONTROL DE DAÑOS (APALANCAMIENTO)", expanded=True):
            st.markdown("""
            * **El desfase regulatorio:** Recuerda que la API pública de Yahoo puede traer de **10 a 15 minutos de retraso** según las condiciones de la bolsa de Nueva York. Tu Dashboard es una **brújula de estrategia** (te dice dónde están los soportes y si hay sobrecompra/sobreventa), pero a la hora de abrir la operación, el precio de entrada definitivo es el que dicte **eToro**.
            * **Ejecución del Stop Loss:** A apalancamiento x10, si el precio real cae al *Stop Loss Recomendado*, tu cuenta perderá aproximadamente entre un **15% y un 20%** de esa operación. No quitar el stop loss es la única forma de evitar que una caída repentina te liquide el 100% del margen.
            """)

# --- 🔄 BUCLE DE ACTUALIZACIÓN AUTOMÁTICA EN SEGUNDO PLANO ---
time.sleep(15)
st.rerun()
