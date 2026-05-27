import datetime
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests
import os

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="WAR ROOM - 10X LEVERAGE", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# REEMPLAZA AQUÍ TU API KEY DE TWELVE DATA
API_KEY_TWELVE = "a38e308378f54c20ba80c8992d919f1e"

ARCHIVO_TICKERS = "mis_tickers.txt"
TICKERS_DEFECTO = ["VRT", "NVDA", "AMD", "QCOM", "TSLA", "GOOG", "SMCI", "BTC/USD"]

def cargar_tickers_permanentes():
    if os.path.exists(ARCHIVO_TICKERS):
        with open(ARCHIVO_TICKERS, "r") as f: 
            return [l.strip().upper() for l in f.read().splitlines() if l.strip()]
    return TICKERS_DEFECTO

def guardar_tickers_permanentes(lista_tickers):
    with open(ARCHIVO_TICKERS, "w") as f:
        for t in lista_tickers: 
            f.write(f"{t}\n")

if "tickers" not in st.session_state: 
    st.session_state.tickers = cargar_tickers_permanentes()
if "seleccionado" not in st.session_state: 
    st.session_state.seleccionado = st.session_state.tickers[0] if st.session_state.tickers else None

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    </style>
""", unsafe_allow_html=True)

def obtener_precio_overnight_real(ticker_symbol):
    if API_KEY_TWELVE == "a38e308378f54c20ba80c8992d919f1e": return None
    try:
        url = f"https://api.twelvedata.com/price?symbol={ticker_symbol}&apikey={API_KEY_TWELVE}&include_pre_post=true"
        res = requests.get(url, timeout=3).json()
        if "price" in res: return float(res["price"])
    except: pass
    return None

def obtener_datos_ticker(ticker_symbol):
    try:
        yf_symbol = "BTC-USD" if ticker_symbol == "BTC/USD" else ticker_symbol
        ticker = yf.Ticker(yf_symbol)
        precio_actual = obtener_precio_overnight_real(ticker_symbol)
        
        # ⚡ MARCO DE 15 MINUTOS: Máxima precisión para operaciones a x10
        df = ticker.history(period="5d", interval="15m", prepost=True) 

        if df.empty: return None
        if not precio_actual: precio_actual = float(df["Close"].iloc[-1])
            
        precio_anterior = float(df["Close"].iloc[-2]) if len(df) > 1 else precio_actual
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo de RSI
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0, 0.00001)
        rsi_actual = round(float((100 - (100 / (1 + rs))).iloc[-1]), 2) if not rs.empty else 50.0

        # PARÁMETROS ESTRICTOS PARA X10 (Target 1.2%, Stop 0.4%)
        if rsi_actual <= 30:
            bg_color, border_color, senal = "#0f3d1b", "#00ff41", "🟢 LONG x10"
            target = precio_actual * 1.012  
            stop = precio_actual * 0.996    
        elif rsi_actual >= 70:
            bg_color, border_color, senal = "#4d1111", "#ff3333", "🔴 SHORT x10"
            target = precio_actual * 0.988  
            stop = precio_actual * 1.004    
        else:
            bg_color, border_color, senal = "#1e222d", "#363a45", "🟡 NEUTRO"
            target = precio_actual * 1.012
            stop = precio_actual * 0.996
        
        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "stop_loss": round(stop, 2),
            "target": round(target, 2),
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

st.caption(f"🚀 SCALPING x10 | Marco: 15m | Sync: {datetime.datetime.now().strftime('%H:%M:%S')}")

col_longs, col_shorts, col_orden = st.columns([1.1, 1.1, 1])

# --- COLUMNA 1: LONGS ---
with col_longs:
    st.markdown("### 🟢 ENTRADAS LONG")
    activos_long = {k: v for k, v in datos_completos.items() if v["rsi"] <= 30}
    for t, data in dict(sorted(activos_long.items(), key=lambda item: item[1]["rsi"])).items():
        es_sel = (t == st.session_state.seleccionado)
        with st.container(border=True):
            st.markdown(f'''
                <div style="background-color: {data['bg_color']}; padding: 8px; border-radius: 4px; border: {'3px' if es_sel else '1px'} solid {'#ffb703' if es_sel else data['border_color']}; text-align: center;">
                    <span style="font-size: 16px; font-weight: bold; color: white;">{t}</span> | <span style="font-size: 18px; font-weight: bold; color: #00ff41;">${data['precio']:.2f}</span><br>
                    <span style="font-size: 12px; color: #cfd6e4;">RSI 15m: <b>{data['rsi']}</b></span>
                </div>
            ''', unsafe_allow_html=True)
            
            # Botón corregido
            if st.button(f"Ver {t}", key=f"long_{t}", use_container_width=True): 
                st.session_state.seleccionado = t
                st.rerun()

# --- COLUMNA 2: SHORTS ---
with col_shorts:
    st.markdown("### 🔴 ENTRADAS SHORT")
    activos_short = {k: v for k, v in datos_completos.items() if v["rsi"] >= 70}
    for t, data in dict(sorted(activos_short.items(), key=lambda item: item[1]["rsi"], reverse=True)).items():
        es_sel = (t == st.session_state.seleccionado)
        with st.container(border=True):
            st.markdown(f'''
                <div style="background-color: {data['bg_color']}; padding: 8px; border-radius: 4px; border: {'3px' if es_sel else '1px'} solid {'#ffb703' if es_sel else data['border_color']}; text-align: center;">
                    <span style="font-size: 16px; font-weight: bold; color: white;">{t}</span> | <span style="font-size: 18px; font-weight: bold; color: #ff3333;">${data['precio']:.2f}</span><br>
                    <span style="font-size: 12px; color: #cfd6e4;">RSI 15m: <b>{data['rsi']}</b></span>
                </div>
            ''', unsafe_allow_html=True)
            
            # Botón corregido
            if st.button(f"Ver {t}", key=f"short_{t}", use_container_width=True): 
                st.session_state.seleccionado = t
                st.rerun()

# --- COLUMNA 3: CONFIGURACIÓN Y RIESGO ---
with col_orden:
    st.markdown("### 🛠️ GESTIÓN X10")
    
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
            st.metric(label="Precio Actual", value=f"${main['precio']:.2f}", delta=f"RSI: {main['rsi']}")
            
            st.error(f"🛑 **STOP LOSS**: ${main['stop_loss']:.2f} (-4% capital real a x10)")
            st.success(f"🏆 **TAKE PROFIT**: ${main['target']:.2f} (+12% capital real a x10)")
            
            st.caption("Nota: Cálculos basados en apalancamiento estricto 10x. No mover el Stop Loss bajo ninguna circunstancia.")

# Refresco automático cada 20 segundos para no saturar la API
time.sleep(20) 
st.rerun()
