def obtener_datos_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Intento 1: Intentar máxima resolución (Velas de 1 minuto)
        df = ticker.history(period="3d", interval="1m") 
        
        # Si el mercado está cerrado o falla el de 1m, usamos el plan de respaldo (Velas de 15m o 1d)
        if df.empty or len(df) < 15:
            # Plan B: Traer los datos consolidados más recientes
            df = ticker.history(period="5d", interval="15m")
            if df.empty:
                df = ticker.history(period="1mo", interval="1d")

        if df.empty:
            return None

        precio_actual = float(df["Close"].iloc[-1])
        precio_anterior = float(df["Close"].iloc[-2]) if len(df) > 1 else precio_actual
        cambio_pct = float(((precio_actual - precio_anterior) / precio_anterior) * 100)

        # Cálculo seguro del RSI (14)
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().replace(0, 0.00001)
        rs = avg_gain / avg_loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_actual = round(float(rsi_series.iloc[-1]), 2) if not rsi_series.empty else 50.0

        # Soporte dinámico: Media Móvil de 50 períodos (o el máximo disponible si hay pocas velas)
        window_size = min(50, len(df))
        sma_50 = float(df["Close"].rolling(window=window_size).mean().iloc[-1])
        
        # Rangos históricos estables para que la barra no se rompa
        hist_1y = ticker.history(period="1y")
        if not hist_1y.empty:
            min_periodo = float(hist_1y["Low"].min())
            max_periodo = float(hist_1y["High"].max())
        else:
            min_periodo = float(df["Low"].min())
            max_periodo = float(df["High"].max())

        # Configuración de señales según el RSI intradía
        if rsi_actual <= 35:
            senal = "🟢 COMPRA INTRADÍA"
            badge = "COMPRA"
            nota = f"RSI en sobreventa rápida ({rsi_actual}). Monitorear si el precio coquetea con el soporte."
        elif rsi_actual >= 65:
            senal = "🔴 VENTA / RECOGER GANANCIAS"
            badge = "VENTA"
            nota = f"RSI en sobrecompra ({rsi_actual}). Riesgo alto de retroceso técnico inmediato."
        else:
            senal = "🟡 MONITORIZAR"
            badge = "ESPERAR"
            nota = f"Precio en equilibrio en gráfico rápido (RSI: {rsi_actual}). Esperar aproximación a zonas clave."

        soporte_estimado = round(sma_50 * 0.995, 2)
        stop_loss_recomendado = round(soporte_estimado * 0.985, 2)

        return {
            "precio": precio_actual,
            "cambio": cambio_pct,
            "rsi": min(max(int(rsi_actual), 0), 100),
            "soporte": soporte_estimado,
            "resistencia": round(precio_actual * 1.015, 2), 
            "stop_loss": stop_loss_recommended,
            "target": round(precio_actual * 1.03, 2),
            "min_5d": min_periodo, # Cambiado internamente a rango amplio para evitar colapsos visuales
            "max_5d": max_periodo,
            "senal": senal,
            "badge": badge,
            "nota": nota
        }
    except Exception as e:
        # Si todo lo demás falla, evitamos meter ceros para no romper el CSS
        return None
