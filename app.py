import datetime
import yfinance as yf
import pandas as pd
import streamlit as st

# 1. Configuración de la página
st.set_page_config(
    page_title="AI & Tech Day Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Gestión dinámica de acciones usando el estado de la sesión
if "tickers" not in st.session_state:
    st.session_state.tickers = ["NVDA", "SMCI", "RKLB", "AMD", "VRT", "ANET", "MU", "QCOM"]

# 3. Función optimizada para datos Intradía (Velas de 15 minutos)
def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Datos de los últimos 3 días con intervalos de 15 minutos
        df = ticker.history(period="3d", interval="15m") 
        
        if df.empty or len(df) < 50:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2])
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo del RSI (14) basado en gráficos de 15 minutos
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_actual = round(float((100 - (100 / (1 + rs))).iloc[-1]), 2)

        # Soporte dinámico: Media Móvil de 50 períodos (velas de 15 min)
        sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1])
        
        # Rangos del periodo de 3 días para scalping/day trading
        min_periodo = float(df["Low"].min())
        max_periodo = float(df["High"].max())

        # RECOMENDACIÓN OPTIMIZADA: Umbrales ajustados a 35 y 65 para gráficos rápidos de 15m
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            badge = "COMPRA"
            nota = "RSI en sobreventa rápida (<=35). Monitorear si el precio está cerca del soporte para ejecutar entrada."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            badge = "VENTA"
            nota = "RSI en sobrecompra extrema (>=65). Riesgo alto de retroceso técnico. Excelente zona para tomar ganancias o ajustar Stop Loss."
        else:
            senal = "🟡 MONITORIZAR"
            badge = "ESPERAR"
            nota = "Precio en rango neutral de corto plazo. No perseguir el precio; esperar aproximación a zonas clave."

        # RECOMENDACIÓN DE STOP LOSS: Calculado rigurosamente al 1.5% por debajo de la SMA50 para soportar ruido en x5/x10
        soporte_estimado = round(sma_50 * 0.995, 2)
        stop_loss_recomendado = round(soporte_estimado * 0.985, 2)

        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.015, 2), 
            "stop_loss": stop_loss_recomendado,
            "target": round(precio_actual * 1.03, 2),  # Target del 3% aproximado
            "min_3d": min_periodo,
            "max_3d": max_periodo,
            "senal": senal,
            "badge": badge,
            "nota": nota
        }
    except:
        return None

# --- PANEL DE CONTROL LATERAL (Gestión de Acciones) ---
st.sidebar.markdown("## 🛠️ Panel de Control")

# Sección 1: Añadir Acción
nuevo_ticker = st.sidebar.text_input("Añadir símbolo (Ej: TSLA, AAPL, BTC-USD):").upper().strip()
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
                st.sidebar.error("Símbolo no encontrado en el mercado.")
        except:
            st.sidebar.error("Error al validar el símbolo.")

# Sección 2: Eliminar Acción
st.sidebar.markdown("---")
if len(st.session_state.tickers) > 0:
    ticker_a_eliminar = st.sidebar.selectbox("Eliminar una acción:", st.session_state.tickers)
    if st.sidebar.button("🗑️ Eliminar Acción"):
        st.session_state.tickers.remove(ticker_a_eliminar)
        st.sidebar.warning(f"{ticker_a_eliminar} eliminado.")
        st.rerun()

# Sección 3: Selección de enfoque para el panel derecho
st.sidebar.markdown("---")
if st.session_state.tickers:
    seleccionado = st.sidebar.selectbox("🎯 ACCIÓN EN ENFOQUE:", st.session_state.tickers)
else:
    st.info("Añade una acción desde la barra lateral para empezar.")
    st.stop()


# --- INTERFAZ GRÁFICA PRINCIPAL ---
st.title("⚡ AI Day Trading Live Dashboard (15m)")
st.caption(f"Velocidad de mercado: Intervalos de 15 minutos — Última actualización: {datetime.datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# Layout de dos columnas
col_izq, col_der = st.columns([1.1, 1])

# --- COLUMNA IZQUIERDA: LISTA EN TIEMPO REAL ---
with col_izq:
    st.markdown("### 📋 Monitor de Scalping")
    
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
                        label="Precio (15m)", 
                        value=f"${data['precio']:.2f}", 
                        delta=f"{data['cambio']:.2f}%"
                    )
                with c3:
                    st.markdown(f"**Soporte (SMA50):** ${data['soporte']:.2f}")
                    st.markdown(f"**RSI (15m):** {data['rsi']}")
                    st.progress(data["rsi"] / 100)

# --- COLUMNA DERECHA: ENFOQUE TÁCTICO APALANCADO & EXPEDIENTE DE GUÍA ---
with col_der:
    st.markdown(f"### 🔍 Ejecución de Orden: {seleccionado}")
    main = obtener_datos_ticker(seleccionado)
    
    if main:
        with st.container(border=True):
            st.header(f"📊 {seleccionado} — ${main['precio']:.2f}")
            st.metric(label="Último movimiento de vela", value=f"${main['precio']:.2f}", delta=f"{main['cambio']:.2f}%")
            
            # Alerta de sugerencia rápida
            st.info(f"**{main['senal']}**\n\n{main['nota']}")
            
            st.markdown("#### 🚨 Parámetros de Riesgo Críticos (Apalancamiento x5 / x10)")
            
            met1, met2, met3 = st.columns(3)
            with met1:
                st.metric(label="🎯 Entrada Óptima (Soporte)", value=f"${main['soporte']:.2f}")
            with met2:
                st.metric(label="🛑 Stop Loss Recomendado", value=f"${main['stop_loss']:.2f}")
            with met3:
                st.metric(label="🏆 Target Corto (3%)", value=f"${main['target']:.2f}")
            
            st.markdown("---")
            
            st.markdown(f"**RSI Intradía (15 min):** {main['rsi']} / 100")
            st.progress(main["rsi"] / 100)
            
            st.markdown("---")
            
            st.markdown("**Rango de oscilación del precio (Últimos 3 días):**")
            st.slider(
                label="Rango Mín/Máx Reciente",
                min_value=main["min_3d"],
                max_value=main["max_3d"],
                value=main["precio"],
                disabled=True
            )

        # 🧠 NUEVA SECCIÓN: CAJA DE GUÍA TÁCTICA PERMANENTE PARA OPERACIONES APALANCADAS
        with st.expander("📚 MANUAL DE CONFLUENCIA RÁPIDA (LEER ANTES DE OPERAR X5/X10)", expanded=True):
            st.markdown("""
            1. **La Regla de Confluencia Inquebrantable:** No abras una posición en eToro usando *únicamente* el indicador RSI. La entrada ideal ocurre cuando el precio actual toca o está muy cerca de la **Entrada Óptima (Soporte)** Y ADEMÁS el **RSI se encuentra en 35 o menos**.
            2. **Uso del Stop Loss Automatizado:** El *Stop Loss Recomendado* aquí calculado está diseñado para salvaguardar tu margen ante giros violentos de tendencia. A un apalancamiento de x10, si el precio cruza este Stop Loss, tu pérdida real en la cuenta rondará el **15% - 20%**. Si no usas este límite, una caída imprevista del 10% en el mercado **liquidará por completo tu capital (100% de pérdida)**.
            3. **Peligro por Extensión de Tendencia:** Durante noticias macroeconómicas o reportes trimestrales de ganancias, el RSI de 15m puede marcar sobreventa (25 o menos) y mantenerse congelado ahí mientras el precio se desploma de forma libre. Si el soporte de la SMA50 se quiebra de manera contundente, asume la pérdida corta y retírate; protege tu saldo para la siguiente oportunidad.
            """)
