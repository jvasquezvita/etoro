import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests
import os

# 1. CONFIGURACIÓN DE LA PÁGINA (Modo Ancho y Enfoque de Terminal)
st.set_page_config(
    page_title="WAR ROOM",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# REEMPLAZA AQUÍ TU API KEY DE TWELVE DATA
API_KEY_TWELVE = "a38e308378f54c20ba80c8992d919f1e"

# ARCHIVO DE ALMACENAMIENTO PERMANENTE
ARCHIVO_TICKERS = "mis_tickers.txt"

# LISTA INICIAL POR DEFECTO
TICKERS_DEFECTO = [
    "VRT", "ANET", "NVDA", "AMD", "MU", 
    "ARM", "QCOM", "TSLA", "GOOG", "RKLB", 
    "SMCI", "BTC/USD"
]

def cargar_tickers_permanentes():
    if os.path.exists(ARCHIVO_TICKERS):
        with open(ARCHIVO_TICKERS, "r") as f:
            lineas = f.read().splitlines()
            tickers = [linea.strip().upper() for linea in lineas if linea.strip()]
            if tickers: return tickers
    return TICKERS_DEFECTO

def guardar_tickers_permanentes(lista_tickers):
    with open(ARCHIVO_TICKERS, "w") as f:
        for ticker in lista_tickers:
            f.write(f"{ticker}\n")

if "tickers" not in st.session_state:
    st.session_state.tickers = cargar_tickers_permanentes()

if "seleccionado" not in st.session_state:
    st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None

# Ocultar menús de Streamlit para ganar más espacio en pantalla
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    </style>
""", unsafe_allow_html=True)

def obtener_precio_overnight_real(ticker_symbol):
    if API_KEY_TWELVE == "a38e308378f54c20ba80c8992d919f1e": return None
    try:
        url = f"https://api.twelvedata.com/price?symbol={ticker_symbol}&apikey={API_KEY_TWELVE}&include_pre_post=true"
        response = requests.get(url, timeout=3).json()
        if "price" in response: return float(response["price"])
    except: pass
    return None

def obtener_datos_ticker(ticker_symbol):
    try:
        yf_symbol = "BTC-USD" if ticker_symbol == "BTC/USD" else ticker_symbol
        ticker = yf.Ticker(yf_symbol)
        precio_actual = obtener_precio_overnight_real(ticker_symbol)
        df = ticker.history(period="5d", interval="15m", prepost=True) 

        if df.empty: df = ticker.history(period="1mo", interval="1d")
        if df.empty: return None
        if not precio_actual: precio_actual = float(df["Close"].iloc[-1])
            
        precio_anterior = float(df["Close"].iloc[-2]) if len(df) > 1 else precio_actual
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi_series.iloc[-1]), 2) if not rsi_series.empty else 50.0

        if rsi_actual <= 32:
            bg_color = "#0f3d1b"
            border_color = "#00ff41"
            senal = "🟢 COMPRA"
        elif rsi_actual >= 68:
            bg_color = "#4d1111"
            border_color = "#ff3333"
            senal = "🔴 SHORT"
        else:
            bg_color = "#1e222d"
            border_color = "#363a45"
            senal = "🟡 NEUTRO"

        window_size = min(50, len(df))
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        soporte_estimado = round(sma_50 * 0.995, 2)
        
        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "stop_loss": round(soporte_estimado * 0.992, 2),
            "target": round(precio_actual * 1.015, 2),
            "min_5d": float(df["Low"].min()),
            "max_5d": float(df["High"].max()),
            "bg_color": bg_color,
            "border_color": border_color,
            "senal": senal
        }
    except: return None

# --- CARGA DE DATOS ---
datos_completos = {}
if st.session_state.tickers:
    for t in st.session_state.tickers:
        res = obtener_datos_ticker(t)
        if res: datos_completos[t] = res

# Reloj de sincronización superior ultra minimalista
st.caption(f"🔄 15s | Sync: {datetime.datetime.now().strftime('%H:%M:%S')}")

# DISTRIBUCIÓN POLARIZADA EN TRES COLUMNAS
col_longs, col_shorts, col_orden = st.columns([1.1, 1.1, 1])

# --- COLUMNA 1: ZONA DE COMPRA / LONGS (RSI <= 50) ---
with col_longs:
    st.markdown("### 🟢 LONGS (RSI Asc)")
    activos_long = {k: v for k, v in datos_completos.items() if v["rsi"] <= 50}
    activos_long_ordenados = dict(sorted(activos_long.items(), key=lambda item: item[1]["rsi"]))
    
    for t, data in activos_long_ordenados.items():
        es_seleccionado = (t == st.session_state.seleccionado)
        borde_final = "#ffb703" if es_seleccionado else data["border_color"]
        grosor_borde = "3px" if es_seleccionado else "1px"
        
        with st.container(border=True):
            st.markdown(f"""
                <div style="background-color: {data['bg_color']}; padding: 8px; border-radius: 4px; border: {grosor_borde} solid {borde_final}; text-align: center;">
                    <span style="font-size: 16px; font-weight: bold; color: white;">{t}</span> | 
                    <span style="font-size: 18px; font-weight: bold; color: #00ff41;">${data['precio']:.2f}</span><br>
                    <span style="font-size: 12px; color: #cfd6e4;">RSI: <b>{data['rsi']}</b> ({data['senal']})</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🎯 Ver {t}", key=f"long_{t}", use_container_width=True):
                st.session_state.seleccionado = t
                st.rerun()

# --- COLUMNA 2: ZONA DE CORTOS / SHORTS (RSI > 50) ---
with col_shorts:
    st.markdown("### 🔴 SHORTS (RSI Desc)")
    activos_short = {k: v for k, v in datos_completos.items() if v["rsi"] > 50}
    activos_short_ordenados = dict(sorted(activos_short.items(), key=lambda item: item[1]["rsi"], reverse=True))
    
    for t, data in activos_short_ordenados.items():
        es_seleccionado = (t == st.session_state.seleccionado)
        borde_final = "#ffb703" if es_seleccionado else data["border_color"]
        grosor_borde = "3px" if es_seleccionado else "1px"
        
        with st.container(border=True):
            st.markdown(f"""
                <div style="background-color: {data['bg_color']}; padding: 8px; border-radius: 4px; border: {grosor_borde} solid {borde_final}; text-align: center;">
                    <span style="font-size: 16px; font-weight: bold; color: white;">{t}</span> | 
                    <span style="font-size: 18px; font-weight: bold; color: #ff3333;">${data['precio']:.2f}</span><br>
                    <span style="font-size: 12px; color: #cfd6e4;">RSI: <b>{data['rsi']}</b> ({data['senal']})</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🎯 Ver {t}", key=f"short_{t}", use_container_width=True):
                st.session_state.seleccionado = t
                st.rerun()

# --- COLUMNA 3: PANEL DE ACCIÓN TÁCTICA E INYECCIÓN ---
with col_orden:
    st.markdown("### 🛠️ CONFIGURACIÓN")
    
    # Pestañas ultra compactas para agregar o eliminar activos sin ocupar espacio vertical
    tab_agregar, tab_eliminar = st.tabs(["➕ Agregar", "🗑️ Eliminar"])
    
    with tab_agregar:
        c_in, c_btn = st.columns([1.5, 1])
        with c_in:
            nuevo_ticker = st.text_input("Símbolo:", key="txt_nuevo", label_visibility="collapsed").upper().strip()
        with c_btn:
            btn_add = st.button("Inyectar", use_container_width=True)
            
        if btn_add and nuevo_ticker and nuevo_ticker not in st.session_state.tickers:
            try:
                test_sym = "BTC-USD" if nuevo_ticker in ["BTC/USD", "BTC-USD"] else nuevo_ticker.replace("/", "-")
                if not yf.Ticker(test_sym).history(period="1d").empty:
                    st.session_state.tickers.append(nuevo_ticker)
                    guardar_tickers_permanentes(st.session_state.tickers)
                    st.session_state.seleccionado = nuevo_ticker
                    st.rerun()
            except: pass

    with tab_eliminar:
        if st.session_state.tickers:
            c_sel, c_del = st.columns([1.5, 1])
            with c_sel:
                ticker_a_eliminar = st.selectbox("Borrar:", st.session_state.tickers, label_visibility="collapsed")
            with c_del:
                btn_del = st.button("Borrar", use_container_width=True)
                
            if btn_del:
                st.session_state.tickers.remove(ticker_a_eliminar)
                guardar_tickers_permanentes(st.session_state.tickers)
                st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None
                st.rerun()

    st.markdown("---")
    
    target_ticker = st.session_state.seleccionado
    if target_ticker in datos_completos:
        main = datos_completos[target_ticker]
        header_color = "🟢 LONG" if main["rsi"] <= 50 else "🔴 SHORT"
        
        with st.container(border=True):
            st.markdown(f"<b>📊 {target_ticker} — {header_color}</b>", unsafe_allow_html=True)
            
            c_t1, c_t2 = st.columns(2)
            with c_t1: st.metric(label="Precio", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            with c_t2: st.metric(label="RSI", value=f"{main['rsi']}/100")
            
            st.error(f"🛑 STOP LOSS: ${main['stop_loss']:.2f}")
            st.info(f"🎯 ENTRADA ÓPTIMA: ${main['soporte']:.2f}")
            st.success(f"🏆 TARGET: ${main['target']:.2f}")
            
            with st.expander("📘 Info Colores", expanded=False):
                st.markdown(r"""
                * **🟢 Verde (RSI <= 32):** Sobreventa (Compra).
                * **🔴 Rojo (RSI >= 68):** Sobrecompra (Short).
                * **🟡 Gris (33-67):** Zona Neutral.
                """)
                
# --- REFRESCO AUTOMÁTICO ---
time.sleep(15)
st.rerun()
