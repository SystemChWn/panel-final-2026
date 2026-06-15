import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import time
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN Y FUNCIONES ---
st.set_page_config(layout="wide")

def obtener_hora_local():
    tz = pytz.timezone('America/Mexico_City')
    return datetime.now(tz)

def asignar_rondines_por_puntos(df):
    df = df.sort_values(by="Fecha_Hora")
    rondines = []
    contador_rondin = 1
    ultimo_punto = 0
    
    for punto in df["Punto_QR"]:
        try:
            punto_int = int(str(punto).replace("Punto ", ""))
        except:
            punto_int = 0
        if punto_int < ultimo_punto and punto_int < 10: 
            contador_rondin += 1
            if contador_rondin > 6: contador_rondin = 1 
        rondines.append(f"Rondin {contador_rondin}")
        ultimo_punto = punto_int
    df["Rondin_Asignado"] = rondines
    return df

# --- 2. INTERFAZ VISUAL ---
col_logo, col_titulo = st.columns([0.06, 0.94], gap="small")
with col_logo:
    st.image("https://lh3.googleusercontent.com/d/1YuA-V3W27vrLeDszpzRYNJnwMKGvpHpA", width=55)
with col_titulo:
    st.title("PANEL DE SUPERVISIÓN")

# --- 3. CARGA DE DATOS ---
sheet_id = "1PjB61hZhT1SXO7eRgRgnxo39W2o5AaFdhFTjPz2eb7k"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

try:
    df_raw = pd.read_csv(f"{url}&nocache={time.time()}")
    df_raw = df_raw.fillna("")
    df_raw["Punto_QR"] = df_raw["Punto_QR"].astype(str).str.replace(".0", "", regex=False).str.strip()
    fecha_convertida = pd.to_datetime(df_raw["Fecha_Hora"], errors="coerce", dayfirst=True)
    df_raw["Dia_Num"] = fecha_convertida.dt.day.fillna(0).astype(int)
    df_raw["Mes_Num"] = fecha_convertida.dt.month.fillna(0).astype(int)
    df_raw["Anio_Num"] = fecha_convertida.dt.year.fillna(0).astype(int)
    df_raw = asignar_rondines_por_puntos(df_raw)
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# --- 4. SIDEBAR Y FILTROS ---
ahora = obtener_hora_local()
anio_sel = st.sidebar.selectbox("AÑO", [2026, 2027, 2028], index=0)
mes_sel = st.sidebar.selectbox("MES", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=ahora.month-1)
dia_sel = st.sidebar.selectbox("DÍA", list(range(1, 32)), index=ahora.day-1)
mes_num = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(mes_sel) + 1

df_filtrado = df_raw[(df_raw["Anio_Num"]==anio_sel) & (df_raw["Mes_Num"]==mes_num) & (df_raw["Dia_Num"]==dia_sel)].copy()

# --- 5. MATRIZ DE RONDINES ---
columnas_rondines = ["Rondin 1", "Rondin 2", "Rondin 3", "Rondin 4", "Rondin 5", "Rondin 6"]
matriz = pd.DataFrame({"Punto_QR": [f"Punto {i}" for i in range(1, 45)]})

for col in columnas_rondines:
    matriz[col] = "—"
    registros = df_filtrado[df_filtrado["Rondin_Asignado"] == col]
    for _, f in registros.iterrows():
        pt = f["Punto_QR"]
        matriz.loc[matriz["Punto_QR"] == pt, col] = "SI"
        matriz.loc[matriz["Punto_QR"] == f"Punto {pt}", col] = "SI"

# --- 6. VISUALIZACIÓN ---
dash1, dash2 = st.columns(2)
with dash2:
    st.subheader("ESTATUS DEL RONDÍN ACTUAL")
    rondin_activo = df_filtrado["Rondin_Asignado"].iloc[-1] if not df_filtrado.empty else "Rondin 1"
    progreso = (matriz[rondin_activo] == "SI").sum() / 44
    st.write(f"Rondín en curso: **{rondin_activo}**")
    st.progress(float(progreso))

st.dataframe(matriz, use_container_width=True, hide_index=True)
st_autorefresh(interval=120000)
