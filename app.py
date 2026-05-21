import datetime
import yfinance as yf
import pandas as pd
import streamlit as st

# 1. Configuración de la interfaz estilo terminal de trading
st.set_page_config(
    page_title="Crypto & Tech Aggressive Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. Inyección de estilos CSS estables
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #0d0e12;
        color: #e2e8f0;
    }
    .card {
        background-color: #14171f;
        border: 1px solid #232936;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .main-card {
        background-color: #14171f;
        border: 2px solid #10b981;
        border-radius: 12px;
        padding: 25px;
    }
    .badge-wait {
        background-color: #eab30822;
        color: #eab308;
        border: 1px solid #eab308;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-buy {
        background-color: #22c55e22;
        color: #22c55e;
        border: 1px solid #22c55e;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .price-up { color: #22c55e; font-weight: bold; }
    .price-down { color: #ef4444; font-weight: bold; }
    .rsi-bar-bg {
        background-color: #1e293b;
        height: 6px;
        border-radius: 3px;
        width: 100%;
        position: relative;
        margin-top: 5px;
    }
    .rsi-bar-fill {
        background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
        height: 6px;
        border-radius: 3px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Función de extracción de datos blindada contra fallas de API
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Uso estricto de '6mo' requerido por la API de Yahoo
        df = ticker.history(period="6mo") 
        if df.empty or len(df) < 15:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2])
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo del RSI (14) libre de errores de división por cero
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        # Evitar Warning por división nula si el mercado está plano
        avg_loss = avg_loss.replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi.iloc[-1]), 2)

        # Soporte dinámico basado en la Media Móvil de 50 días
        sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1])

        # Datos históricos de 1 año
        hist_1y = ticker.history(period="1y")
        min_52w = float(hist_1y["Low"].min())
        max_52w = float(hist_1y["High"].max())

        # Configuración de Algoritmo de Señales
        if rsi_actual < 40:
            senal = "OPORTUNIDAD DE COMPRA"
            badge_class = "badge-buy"
            nota = "Activo en zona de descuento o sobreventa diaria. Buen margen de entrada."
        else:
            senal = "ESPERAR"
            badge_class = "badge-wait"
            nota = "Precio en equilibrio relativo. Monitorear retroceso hacia el soporte dinámico."

        # Control para cuando Yahoo oculta la metadata de nombre comercial
        nombre_limpio = ticker_symbol
        try:
            if ticker.info and "longName" in ticker.info:
                nombre_limpio = ticker.info["longName"]
        except:
            pass

        return {
            "nombre": nombre_limpio,
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": rsi_actual,
            "soporte": round(sma_50 * 0.96, 2),
            "resistencia": round(precio_actual * 1.08, 2),
            "stop_loss": round(sma_50 * 0.91, 2),
            "target": round(precio_actual * 1.22, 2),
            "min_52w": min_52w,
            "max_52w": max_52w,
            "senal": senal,
            "badge": badge_class,
            "nota": nota,
        }
    except:
        return None

# 4. Estructura de visualización del Dashboard
st.title("🎯 AI Tech & Growth Live Dashboard")
st.caption(f"Visualización automatizada de datos de mercado — Activa")

# Tu lista de seguimiento de eToro
tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM"]

# Barra lateral limpia para interactuar con el foco derecho
st.sidebar.markdown("### Navegación")
seleccionado = st.sidebar.selectbox("Seleccionar activo para expandir:", tickers)

# División en dos columnas principales
col_izq, col_der = st.columns([1.2, 1])

# --- PROCESAMIENTO COLUMNA IZQUIERDA ---
with col_izq:
    st.subheader("Lista de Monitoreo")
    for t in tickers:
        if t == seleccionado:
            continue
            
        data = obtener_datos_ticker(t)
        if data:
            color_cambio = "price-up" if data["cambio"] >= 0 else "price-down"
            signo = "+" if data["cambio"] >= 0 else ""

            st.markdown(
                f"""
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:1.3rem; font-weight:bold; color:#fff;">{t}</span>
                            <span class="{data['badge']}" style="margin-left:10px;">{data['senal']}</span>
                            <div style="font-size:0.8rem; color:#64748b;">{data['nombre']}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.3rem; font-weight:bold; color:#fff;">${data['precio']:.2f}</div>
                            <div class="{color_cambio}">{signo}{data['cambio']:.2f}%</div>
                        </div>
                    </div>
                    <div style="margin-top:10px; font-size:0.85rem;">
                        <span style="color:#64748b;">RSI (14): {data['rsi']}</span>
                        <div class="rsi-bar-bg"><div class="rsi-bar-fill" style="width:{min(max(data['rsi'], 0), 100)}%"></div></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.8rem;">
                        <div><span style="color:#64748b;">SOPORTE</span><br><strong style="color:#38bdf8;">${data['soporte']:.2f}</strong></div>
                        <div><span style="color:#64748b;">RESISTENCIA</span><br><strong style="color:#f97316;">${data['resistencia']:.2f}</strong></div>
                        <div><span style="color:#64748b;">RIESGO</span><br><strong style="color:#e11d48;">ALTO</strong></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# --- PROCESAMIENTO COLUMNA DERECHA (EL BLOQUE QUE FALLABA) ---
with col_der:
    st.subheader("Foco Detallado de Operación")
    main_data = obtener_datos_ticker(seleccionado)

    if main_data:
        color_cambio = "price-up" if main_data["cambio"] >= 0 else "price-down"
        signo = "+" if main_data["cambio"] >= 0 else ""

        # Aquí renderizamos tu bloque HTML dinámicamente usando las variables reales del mercado
        st.markdown(
            f"""
            <div class="main-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h1 style="margin:0; color:#fff; font-size:2.5rem;">{seleccionado}</h1>
                        <div style="color:#64748b; margin-bottom:15px;">{main_data['nombre']}</div>
                    </div>
                    <div style="text-align:right;">
                        <h1 style="margin:0; color:#fff; font-size:2.5rem;">${main_data['precio']:.2f}</h1>
                        <div class="{color_cambio}" style="font-size:1.2rem;">{signo}{main_data['cambio']:.2f}%</div>
                    </div>
                </div>
                
                <div style="background-color:#1e293b55; border: 1px solid #334155; padding:15px; border-radius:8px; margin-bottom:20px;">
                    <div style="color:#eab308; font-weight:bold; font-size:0.9rem; margin-bottom:5px;">⚠️ SUGERENCIA: {main_data['senal']}</div>
                    <p style="font-size:0.9rem; margin:0; color:#cbd5e1;">{main_data['nota']}</p>
                </div>

                <div style="display:flex; justify-content:space-between; text-align:center; margin-bottom:25px;">
                    <div style="background:#0d0e12; padding:10px 20px; border-radius:6px; flex:1; margin-right:5px;">
                        <span style="font-size:0.75rem; color:#64748b;">🎯 Entrada Estimada</span><br>
                        <strong style="color:#22c55e; font-size:1.1rem;">${main_data['soporte']:.2f}</strong>
                    </div>
                    <div style="background:#0d0e12; padding:10px 20px; border-radius:6px; flex:1; margin-right:5px;">
                        <span style="font-size:0.75rem; color:#64748b;">🛑 Stop Loss sugerido</span><br>
                        <strong style="color:#ef4444; font-size:1.1rem;">${main_data['stop_loss']:.2f}</strong>
                    </div>
                    <div style="background:#0d0e12; padding:10px 20px; border-radius:6px; flex:1;">
                        <span style="font-size:0.75rem; color:#64748b;">🏆 Objetivo (Target)</span><br>
                        <strong style="color:#3b82f6; font-size:1.1rem;">${main_data['target']:.2f}</strong>
                    </div>
                </div>

                <div style="margin-bottom:20px;">
                    <span style="font-size:0.85rem; color:#64748b;">RSI DIARIO: {main_data['rsi']}</span>
                    <div class="rsi-bar-bg"><div class="rsi-bar-fill" style="width:{min(max(main_data['rsi'], 0), 100)}%"></div></div>
                </div>

                <div>
                    <span style="font-size:0.85rem; color:#64748b;">HISTÓRICO EN RANGO DE 52 SEMANAS</span>
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#64748b; margin-top:5px;">
                        <span>Mínimo: ${main_data['min_52w']:.2f}</span>
                        <span>Máximo: ${main_data['max_52w']:.2f}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Pie de página dinámico
st.markdown("---")
st.markdown(
    "<marquee scrollamount='4' style='color:#10b981; font-family:monospace; font-size: 0.9rem;'> "
    "⚡ Sistema de Monitoreo Agresivo de Portafolio en Línea Activo... Conexión con Yahoo Finance API Estable... "
    "</marquee>",
    unsafe_allow_html=True,
)
