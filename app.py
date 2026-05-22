import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA (Modo Ancho y Enfoque de Terminal)
st.set_page_config(
    page_title="WAR ROOM — RADAR POLARIZADO",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# REEMPLAZA AQUÍ TU API KEY DE TWELVE DATA
API_KEY_TWELVE = "a38e308378f54c20ba80c8992d919f1e"

# 2. LISTA MAESTRA DE TICKERS (Mantiene tu orden estructural de procesamiento)
if "tickers" not in st.session_state:
    st.session_state.tickers = [
        "VRT", "ANET", "NVDA", "AMD", "MU", 
        "ARM", "QCOM", "TSLA", "GOOG", "RKLB", 
        "SMCI", "BTC/USD"
    ]

if "seleccionado" not in st.session_state:
    st.session_state.seleccionado = st.session_state.tickers[0]

# Ocultar menús de Streamlit para una experiencia limpia de trading
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# FUNCIÓN: Extracción de precio extendido mediante Twelve Data
def obtener_precio_overnight_real(ticker_symbol):
    if API_KEY_TWELVE == "a38e308378f54c20ba80c8992d919f1e":
        return None
    try:
        url = f"https://api.twwervedata.com/price?symbol={ticker_symbol}&apikey={API_KEY_TWELVE}&include_pre_post=true"
        response = requests.get(url, timeout=3).json()
        if "price" in response:
            return float(response["price"])
    except:
        pass
    return None

# 3. FUNCIÓN HÍBRIDA DE CÁLCULO TÉCNICO CON PARÁMETROS DE RIESGO AJUSTADOS
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

        # RSI (14) - Motor de clasificación polarizada
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi_series.iloc[-1]), 2) if not rsi_series.empty else 50.0

        # CALIBRACIÓN DE COLORES SEGÚN UMBRALES DE RIESGO INTENSOS (RSI 32 / 68)
        if rsi_actual <= 32:
            bg_color = "#0f3d1b"  # Verde Neón (Sobreventa)
            border_color = "#00ff41"
            senal = "🟢 COMPRA INMEDIATA"
        elif rsi_actual >= 68:
            bg_color = "#4d1111"  # Rojo Sangre (Sobrecompra)
            border_color = "#ff3333"
            senal = "🔴 SHORT / LIQUIDAR"
        else:
            bg_color = "#1e222d"  # Gris Neutro de equilibrio
            border_color = "#363a45"
            senal = "🟡 EN EQUILIBRIO"

        # MATEMÁTICA DE SOPORTE Y STOP LOSS AJUSTADO PARA ETORO (x5 / x10)
        window_size = min(50, len(df))
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        
        soporte_estimado = round(sma_50 * 0.995, 2)
        stop_loss_calibrado = round(soporte_estimado * 0.992, 2) # SL ceñido al 0.8%
        target_corto = round(precio_actual * 1.015, 2)          # Target rápido de 1.5%

        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())
        if precio_actual < min_periodo: min_periodo = precio_actual * 0.99
        if precio_actual > max_periodo: max_periodo = precio_actual * 1.01
        
        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.02, 2), 
            "stop_loss": stop_loss_calibrado,
            "target": target_corto,
            "min_5d": min_periodo,
            "max_5d": max_periodo,
            "bg_color": bg_color,
            "border_color": border_color,
            "senal": senal
        }
    except:
        return None


# --- INTERFAZ DE COMANDO CENTRAL ---
st.title("🦅 WAR ROOM: RADAR EN VIVO CLASIFICADO POR RSI")
st.caption(f"Refresco táctico automático: 15s — Sincronización del Servidor: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# Descarga inicial de la sesión actual de mercado
datos_completos = {}
for t in st.session_state.tickers:
    res = obtener_datos_ticker(t)
    if res:
        datos_completos[t] = res

# DISTRIBUCIÓN POLARIZADA EN TRES COLUMNAS GRANDES EN PANTALLA
col_longs, col_shorts, col_orden = st.columns([1.1, 1.1, 1])

# --- COLUMNA 1: ZONA DE COMPRA / LONGS (RSI <= 50) ---
with col_longs:
    st.markdown("### 🟢 ZONA LONGS (RSI Low / Compra)")
    
    # Filtramos solo activos con RSI menor o igual a 50
    activos_long = {k: v for k, v in datos_completos.items() if v["rsi"] <= 50}
    
    if not activos_long:
        st.caption("No hay activos en sobreventa o equilibrio en este momento.")
    else:
        for t, data in activos_long.items():
            es_seleccionado = (t == st.session_state.seleccionado)
            borde_final = "#ffb703" if es_seleccionado else data["border_color"]
            grosor_borde = "3px" if es_seleccionado else "1px"
            
            with st.container(border=True):
                st.markdown(f"""
                    <div style="background-color: {data['bg_color']}; padding: 10px; border-radius: 4px; border: {grosor_borde} solid {borde_final}; text-align: center;">
                        <span style="font-size: 18px; font-weight: bold; color: white;">{t}</span> | 
                        <span style="font-size: 20px; font-weight: bold; color: #00ff41;">${data['precio']:.2f}</span><br>
                        <span style="font-size: 13px; color: #cfd6e4;">RSI: <b>{data['rsi']}</b> ({data['senal']})</span>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"🎯 Analizar {t}", key=f"long_{t}", use_container_width=True):
                    st.session_state.seleccionado = t
                    st.rerun()

# --- COLUMNA 2: ZONA DE CORTOS / SHORTS (RSI > 50) ---
with col_shorts:
    st.markdown("### 🔴 ZONA SHORTS (RSI High / Venta)")
    
    # Filtramos solo activos con RSI mayor a 50
    activos_short = {k: v for k, v in datos_completos.items() if v["rsi"] > 50}
    
    if not activos_short:
        st.caption("No hay activos sobrecomprados en este momento.")
    else:
        for t, data in activos_short.items():
            es_seleccionado = (t == st.session_state.seleccionado)
            borde_final = "#ffb703" if es_seleccionado else data["border_color"]
            grosor_borde = "3px" if es_seleccionado else "1px"
            
            with st.container(border=True):
                st.markdown(f"""
                    <div style="background-color: {data['bg_color']}; padding: 10px; border-radius: 4px; border: {grosor_borde} solid {borde_final}; text-align: center;">
                        <span style="font-size: 18px; font-weight: bold; color: white;">{t}</span> | 
                        <span style="font-size: 20px; font-weight: bold; color: #ff3333;">${data['precio']:.2f}</span><br>
                        <span style="font-size: 13px; color: #cfd6e4;">RSI: <b>{data['rsi']}</b> ({data['senal']})</span>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"🎯 Analizar {t}", key=f"short_{t}", use_container_width=True):
                    st.session_state.seleccionado = t
                    st.rerun()

# --- COLUMNA 3: PANEL DE ACCIÓN TÁCTICA PARA ETORO (FIJO A LA DERECHA) ---
with col_orden:
    target_ticker = st.session_state.seleccionado
    st.markdown(f"### ⚡ PANEL DE EJECUCIÓN")
    
    if target_ticker in datos_completos:
        main = datos_completos[target_ticker]
        
        # Color dinámico para la cabecera del panel táctico según su clasificación actual
        header_color = "🟢 LONG" if main["rsi"] <= 50 else "🔴 SHORT"
        
        with st.container(border=True):
            st.markdown(f"<h4>📊 {target_ticker} — {header_color}</h4>", unsafe_allow_html=True)
            
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                st.metric(label="Precio Actual", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            with c_t2:
                st.metric(label="RSI Actual", value=f"{main['rsi']} / 100")
            
            st.info(f"**Estado:** {main['senal']}")
            st.markdown("---")
            st.markdown("##### 🚨 Parámetros Listos para Copiar a eToro")
            
            # Formato de números limpios y directos para evitar titubeos
            st.error(f"🛑 STOP LOSS: **${main['stop_loss']:.2f}**")
            st.info(f"🎯 ENTRADA ÓPTIMA: **${main['soporte']:.2f}**")
            st.success(f"🏆 TARGET CORTO: **${main['target']:.2f}**")
            
            st.markdown("---")
            st.caption("Rango de la sesión actual:")
            st.slider(
                label="Rango de Volatilidad Reciente",
                min_value=main["min_5d"],
                max_value=main["max_5d"],
                value=main["precio"],
                disabled=True,
                label_visibility="collapsed"
            )
            
            # Utilidades rápidas de administración
            with st.expander("🛠️ Control de Lista"):
                ticker_a_eliminar = st.selectbox("Eliminar activo:", st.session_state.tickers)
                if st.button("🗑️ Confirmar"):
                    st.session_state.tickers.remove(ticker_a_eliminar)
                    st.session_state.seleccionado = st.session_state.tickers[0]
                    st.rerun()
    else:
        st.warning("Selecciona un ticker del panel izquierdo o central para proyectar los datos de eToro.")

# --- BUCLE DE REFRESCO AUTOMÁTICO ---
time.sleep(15)
st.rerun()
