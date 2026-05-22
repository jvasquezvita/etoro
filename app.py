import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA (Modo Ancho y Estilo Oscuro Nativo)
st.set_page_config(
    page_title="WAR ROOM — AI & Tech Scalper",
    layout="wide",
    initial_sidebar_state="collapsed" # Escondemos la barra lateral para maximizar el espacio de la cuadrícula
)

# REEMPLAZA AQUÍ TU API KEY DE TWELVE DATA
API_KEY_TWELVE = "a38e308378f54c20ba80c8992d919f1e"

# 2. LISTA CON EL ORDEN ESTRICTO SOLICITADO
if "tickers" not in st.session_state:
    st.session_state.tickers = [
        "VRT", "ANET", "NVDA", "AMD", "MU", 
        "ARM", "QCOM", "TSLA", "GOOG", "RKLB", 
        "SMCI", "CEL", "BTC/USD"
    ]

if "seleccionado" not in st.session_state:
    st.session_state.seleccionado = st.session_state.tickers[0]

# INYECCIÓN DE CSS PERSONALIZADO (Para crear el efecto de terminal Bloomberg/TradingView)
st.markdown("""
    <style>
    /* Ocultar elementos innecesarios de Streamlit para enfoque puro */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Forzar fuentes monoespaciadas en los bloques de trading */
    .stMetric value {
        font-family: 'Courier New', Courier, monospace !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# FUNCIÓN: Extracción del precio real de mercado extendido mediante Twelve Data
def obtener_precio_overnight_real(ticker_symbol):
    if API_KEY_TWELVE == "a38e308378f54c20ba80c8992d919f1e":
        return None
    try:
        url = f"https://api.twelvedata.com/price?symbol={ticker_symbol}&apikey={API_KEY_TWELVE}&include_pre_post=true"
        response = requests.get(url, timeout=3).json()
        if "price" in response:
            return float(response["price"])
    except:
        pass
    return None

# 3. FUNCIÓN HÍBRIDA DE EXTRACCIÓN Y CÁLCULO TÉCNICO
def obtener_datos_ticker(ticker_symbol):
    try:
        yf_symbol = "BTC-USD" if ticker_symbol == "BTC/USD" else ticker_symbol
        ticker = yf.Ticker(yf_symbol)
        
        precio_actual = obtener_precio_overnight_real(ticker_symbol)
        df = ticker.history(period="5d", interval="15m", prepost=True) 

        if df.empty:
            df = ticker.history(period="1mo", interval="1d")
        if df.empty:
            return None

        if not precio_actual:
            precio_actual = float(df["Close"].iloc[-1])
            
        precio_anterior = float(df["Close"].iloc[-2]) if len(df) > 1 else precio_actual
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # RSI (14)
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi_series.iloc[-1]), 2) if not rsi_series.empty else 50.0

        # SMA 50
        window_size = min(50, len(df))
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        
        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())

        # Colores de la Matriz basados en el nivel de riesgo de RSI
        if rsi_actual <= 35:
            bg_color = "#0f3d1b"  # Verde Neón Oscuro (Sobrevendido - COMPRA)
            border_color = "#00ff41"
            senal = "🟢 COMPRA"
        elif rsi_actual >= 65:
            bg_color = "#4d1111"  # Rojo Oscuro (Sobrecomprado - VENTA)
            border_color = "#ff3333"
            senal = "🔴 SHORT/VENTA"
        else:
            bg_color = "#1e222d"  # Gris Oscuro de trading neutro
            border_color = "#363a45"
            senal = "🟡 MONITOR"

        soporte_estimado = round(sma_50 * 0.995, 2)
        
        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.015, 2), 
            "stop_loss": round(soporte_estimado * 0.985, 2),
            "target": round(precio_actual * 1.03, 2),
            "min_5d": min_periodo,
            "max_5d": max_periodo,
            "bg_color": bg_color,
            "border_color": border_color,
            "senal": senal
        }
    except:
        return None


# --- INTERFAZ DE COMANDO CENTRAL ---
st.title("🦅 WAR ROOM: MATRIZ DE RIESGO EN TIEMPO REAL")
st.caption(f"Refresco táctico: 15s — Sincronización del Servidor: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# Procesamos los datos de todos los tickers en un diccionario para la matriz
datos_completos = {}
for t in st.session_state.tickers:
    res = obtener_datos_ticker(t)
    if res:
        datos_completos[t] = res

# DIVISIÓN ASIMÉTRICA PRINCIPAL: 70% MATRIZ DE ESCANEO / 30% ORDEN DE EJECUCIÓN eTORO
col_matriz, col_ejecucion = st.columns([2.3, 1])

with col_matriz:
    st.markdown("### 🎛️ Matriz de Conciencia Situacional (Grid 4x4)")
    
    # Parámetros del Grid
    columnas_por_fila = 4
    lista_tickers = list(datos_completos.keys())
    
    # Renderizado dinámico de la cuadrícula
    for i in range(0, len(lista_tickers), columnas_por_fila):
        bloque_tickers = lista_tickers[i:i+columnas_por_fila]
        cols_grid = st.columns(columnas_por_fila)
        
        for idx, t in enumerate(bloque_tickers):
            data = datos_completos[t]
            es_seleccionado = (t == st.session_state.seleccionado)
            
            # Resaltar si está seleccionado con un borde dorado de enfoque
            borde_final = "#ffb703" if es_seleccionado else data["border_color"]
            grosor_borde = "3px" if es_seleccionado else "1px"
            
            with cols_grid[idx]:
                # Caja de color personalizada usando HTML/CSS
                st.markdown(f"""
                    <div style="background-color: {data['bg_color']}; 
                                padding: 12px; 
                                border-radius: 6px; 
                                border: {grosor_borde} solid {borde_final};
                                margin-bottom: 10px;
                                text-align: center;">
                        <span style="font-size: 20px; font-weight: bold; color: white;">{t}</span><br>
                        <span style="font-size: 24px; font-weight: bold; color: #00ff41;">${data['precio']:.2f}</span><br>
                        <span style="font-size: 14px; color: #cfd6e4;">RSI: <b>{data['rsi']}</b> | {data['senal']}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón invisible de Streamlit para capturar el click de enfoque
                if st.button(f"🎯 Enfocar {t}", key=f"btn_{t}", use_container_width=True):
                    st.session_state.seleccionado = t
                    st.rerun()

# --- PANEL DE EJECUCIÓN DIRECTA (COLUMNA DERECHA) ---
with col_ejecucion:
    target_ticker = st.session_state.seleccionado
    st.markdown(f"### ⚡ PANEL DE ACCIÓN EXTREMA: {target_ticker}")
    
    if target_ticker in datos_completos:
        main = datos_completos[target_ticker]
        
        with st.container(border=True):
            # Panel de control de flujo
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                st.metric(label=f"Precio {target_ticker}", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            with c_t2:
                st.metric(label="RSI Relativo", value=f"{main['rsi']} / 100")
            
            st.markdown("---")
            st.markdown("#### 🚨 Configuración Clave de Orden Apalancada en eToro")
            
            # Datos puros sin adornos para lectura de alta velocidad
            st.error(f"🛑 STOP LOSS RECOMENDADO: **${main['stop_loss']:.2f}**")
            st.info(f"🎯 PRECIO ENTRADA ÓPTIMO: **${main['soporte']:.2f}**")
            st.success(f"🏆 TARGET DE SALIDA CORTO: **${main['target']:.2f}**")
            
            st.markdown("---")
            st.caption("Rango de volatilidad de la sesión:")
            st.slider(
                label="Canal de Precio (5d)",
                min_value=main["min_5d"],
                max_value=main["max_5d"],
                value=main["precio"],
                disabled=True,
                label_visibility="collapsed"
            )
            
            # Panel de utilidades de emergencia por si necesitas forzar o borrar tickers rápido
            with st.expander("🛠️ Gestión de Radar"):
                ticker_a_eliminar = st.selectbox("Eliminar del Radar:", st.session_state.tickers)
                if st.button("🗑️ Confirmar Eliminación"):
                    st.session_state.tickers.remove(ticker_a_eliminar)
                    st.session_state.seleccionado = st.session_state.tickers[0]
                    st.rerun()
    else:
        st.warning("Selecciona una acción del Grid para cargar los datos de eToro.")

# --- BUCLE DE REFRESCO AUTOMÁTICO DE TERMINAL ---
time.sleep(15)
st.rerun()
