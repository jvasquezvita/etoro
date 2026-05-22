import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests
import re

# 1. Configuración de la página estilo Terminal de Trading
st.set_page_config(
    page_title="AI & Tech Live Scalping Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Gestión dinámica de acciones en el estado de la sesión (Session State)
if "tickers" not in st.session_state:
    st.session_state.tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM", "IONQ"]

if "seleccionado" not in st.session_state:
    st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None

# NUEVA FUNCIÓN: Raspador directo de respaldo para obtener el precio real instantáneo sin usar la API congelada
def obtener_precio_tiempo_real_directo(ticker_symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_symbol}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        # Extraer el último precio del flujo en tiempo real (incluye pre/post mercado si está disponible)
        meta = data['chart']['result'][0]['meta']
        precio = meta.get('regularMarketPrice')
        
        # Si estamos fuera de horario, intentar capturar el precio extendido actual
        df_result = data['chart']['result'][0]['indicators']['quote'][0]['close']
        if df_result and len(df_result) > 0 and df_result[-1] is not None:
            precio = float(df_result[-1])
            
        return precio
    except:
        return None

# 3. Función de extracción ligera combinada
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Intentar obtener el precio ultra fresco usando nuestra nueva función directa
        precio_actual = obtener_precio_tiempo_real_directo(ticker_symbol)
        
        # Descargamos el historial únicamente para calcular el RSI y las Medias Móviles
        df = ticker.history(period="5d", interval="15m", prepost=True) 

        if df.empty:
            df = ticker.history(period="1mo", interval="1d")

        if df.empty:
            return None

        # Si nuestra función directa falló, usamos el último cierre de la vela como plan de respaldo
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
        
        # Rangos mínimos y máximos para el slider de volatilidad
        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())

        # Ajuste preventivo para que el slider no falle si el precio actual se sale por el pre-mercado
        if precio_actual < min_periodo: min_periodo = precio_actual * 0.99
        if precio_actual > max_periodo: max_periodo = precio_actual * 1.01

        # RECOMENDACIÓN TÁCTICA INTRADÍA
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            nota = f"RSI en sobreventa rápida ({rsi_actual}). Excelente ventana si el precio coquetea con el soporte."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            nota = f"RSI en sobrecompra ({rsi_actual}). Riesgo alto de retroceso técnico inmediato."
        else:
            senal = "🟡 MONITORIZAR"
            nota = f"Precio en equilibrio en gráfico rápido (RSI: {rsi_actual}). Esperar aproximación a zonas clave."

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
            "nota": nota
        }
    except:
        return None

# --- PANEL DE CONTROL LATERAL ---
st.sidebar.markdown("## 🛠️ Panel de Control")

# Sección 1: Añadir Acción
nuevo_ticker = st.sidebar.text_input("Añadir símbolo (Ej: TSLA, AAPL, IONQ):").upper().strip()
if st.sidebar.button("➕ Añadir Acción"):
    if nuevo_ticker and nuevo_ticker not in st.session_state.tickers:
        try:
            test_ticker = yf.Ticker(nuevo_ticker)
            test_df = test_ticker.history(period="1d")
            if not test_df.empty:
                st.session_state.tickers.append(nuevo_ticker)
                st.session_state.seleccionado = nuevo_ticker
                st.sidebar.success(f"{nuevo_ticker} añadido!")
                st.rerun()
            else:
                st.sidebar.error("Símbolo no encontrado en Yahoo Finance.")
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
    st.info("Añade una acción desde la barra lateral para empezar.")
    st.stop()


# --- INTERFAZ GRÁFICA PRINCIPAL ---
st.title("⚡ AI Day Trading Scalper Dashboard (Live Bypass)")
st.caption(f"Actualización del flujo: Forzado en vivo mediante consulta JSON directa — Sincronización: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

col_izq, col_der = st.columns([1.1, 1])

# --- COLUMNA IZQUIERDA: MONITOR DE SCALPING INTERACTIVO ---
with col_izq:
    st.markdown("### 📋 Monitor de Scalping Activo (Haz clic para enfocar)")
    
    for t in st.session_state.tickers:
        data = obtener_datos_ticker(t)
        if data:
            es_seleccionado = (t == st.session_state.seleccionado)
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([1.1, 1, 0.9])
                with c1:
                    label_boton = f"🎯 {t}" if es_seleccionado else f"{t}"
                    if st.button(label_boton, key=f"btn_{t}", use_container_width=True):
                        st.session_state.seleccionado = t
                        st.rerun()
                    st.caption(data["senal"])
                with c2:
                    st.metric(
                        label="Precio en Vivo", 
                        value=f"${data['precio']:.2f}", 
                        delta=f"{data['cambio']:.2f}%"
                    )
                with c3:
                    st.markdown(f"**Soporte:** ${data['soporte']:.2f}")
                    st.markdown(f"**RSI (15m):** {data['rsi']}")
                    st.progress(data["rsi"] / 100)

# --- COLUMNA DERECHA: ENFOQUE TÁCTICO APALANCADO ---
with col_der:
    seleccionado_actual = st.session_state.seleccionado
    st.markdown(f"### 🔍 Ejecución de Orden Corta: {seleccionado_actual}")
    main = obtener_datos_ticker(seleccionado_actual)
    
    if main:
        with st.container(border=True):
            st.header(f"📊 {seleccionado_actual} — ${main['precio']:.2f}")
            st.metric(label="Último Precio Detectado", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            
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
            
            st.markdown("**Rango de oscilación del precio en esta sesión:**")
            st.slider(
                label="Rango de Volatilidad Reciente",
                min_value=main["min_5d"],
                max_value=main["max_5d"],
                value=main["precio"],
                disabled=True
            )

        with st.expander("📚 CONSEJOS DE CONTROL DE DAÑOS (APALANCAMIENTO)", expanded=True):
            st.markdown("""
            * **Bypass Exitoso:** Este código incluye la función `obtener_precio_tiempo_real_directo()`, la cual se salta la API estándar de descarga histórica de Yahoo y extrae directamente los paquetes JSON rápidos que alimentan los gráficos de su web principal.
            """)

# --- 🔄 BUCLE DE REFRESCO AUTOMÁTICO ---
time.sleep(15)
st.rerun()
