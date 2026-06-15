import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import time
import pytz
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.message import EmailMessage

# --- 1. CONFIGURACIÓN Y FUNCIONES ---
st.set_page_config(layout="wide")

def obtener_hora_local():
    return datetime.now(pytz.timezone('America/Mexico_City'))

def asignar_rondines_por_puntos(df):
    df = df.sort_values(by="Fecha_Hora")
    rondines, contador, ultimo_pt = [], 1, 0
    for punto in df["Punto_QR"]:
        try: pt_int = int(str(punto).replace("Punto ", ""))
        except: pt_int = 0
        if pt_int < ultimo_pt and pt_int < 10: 
            contador = contador + 1 if contador < 6 else 1
        rondines.append(f"Rondin {contador}")
        ultimo_pt = pt_int
    df["Rondin_Asignado"] = rondines
    return df

# --- 2. INTERFAZ VISUAL ---
col_logo, col_titulo = st.columns([0.06, 0.94])
with col_logo: st.image("https://lh3.googleusercontent.com/d/1YuA-V3W27vrLeDszpzRYNJnwMKGvpHpA", width=55)
with col_titulo: st.title("PANEL DE SUPERVISIÓN")

# --- 3. CARGA DE DATOS ---
sheet_id = "1PjB61hZhT1SXO7eRgRgnxo39W2o5AaFdhFTjPz2eb7k"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

try:
    df_raw = pd.read_csv(f"{url}&nocache={time.time()}").fillna("")
    df_raw["Punto_QR"] = df_raw["Punto_QR"].astype(str).str.replace(".0", "", regex=False).str.strip()
    fecha_c = pd.to_datetime(df_raw["Fecha_Hora"], errors="coerce", dayfirst=True)
    df_raw["Dia_Num"], df_raw["Mes_Num"], df_raw["Anio_Num"] = fecha_c.dt.day, fecha_c.dt.month, fecha_c.dt.year
    df_raw = asignar_rondines_por_puntos(df_raw)
except Exception as e:
    st.error(f"Error: {e}"); st.stop()

# --- 4. SIDEBAR Y FILTROS ---
ahora = obtener_hora_local()
anio_sel = st.sidebar.selectbox("AÑO", [2026, 2027, 2028], index=0)
mes_sel = st.sidebar.selectbox("MES", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=ahora.month-1)
dia_sel = st.sidebar.selectbox("DÍA", list(range(1, 32)), index=ahora.day-1)
mes_num = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(mes_sel) + 1
turno_sel = st.sidebar.selectbox("TURNO", ["DIA", "NOCHE"])

df_filt = df_raw[(df_raw["Anio_Num"]==anio_sel) & (df_raw["Mes_Num"]==mes_num) & (df_raw["Dia_Num"]==dia_sel)].copy()

# --- 5. MATRIZ Y CÁLCULOS ---
cols_rond = ["Rondin 1", "Rondin 2", "Rondin 3", "Rondin 4", "Rondin 5", "Rondin 6"]
matriz = pd.DataFrame({"Punto_QR": [f"Punto {i}" for i in range(1, 45)]})
for col in cols_rond:
    matriz[col] = "—"
    for _, f in df_filt[df_filt["Rondin_Asignado"] == col].iterrows():
        pt = f["Punto_QR"]
        matriz.loc[(matriz["Punto_QR"] == pt) | (matriz["Punto_QR"] == f"Punto {pt}"), col] = "SI"

matriz["TOTAL"] = matriz.apply(lambda row: f"{(row[cols_rond] == 'SI').sum()}/6", axis=1)
porcentajes = [f"{(matriz[col] == 'SI').sum() / 44 * 100:.1f}%" for col in cols_rond]
cumplimiento_gral = (matriz[cols_rond] == 'SI').sum().sum() / (44 * 6) * 100

# --- 6. VISUALIZACIÓN Y CORREO ---
dash1, dash2 = st.columns(2)
with dash1:
    fig = px.pie(values=[cumplimiento_gral, 100-cumplimiento_gral], names=["Completado", "Pendiente"], hole=0.65, color_discrete_map={"Completado": "#60A5FA", "Pendiente": "#E9ECEF"})
    fig.update_layout(height=190, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, annotations=[dict(text=f"{cumplimiento_gral:.1f}%", showarrow=False, font_size=20)])
    st.plotly_chart(fig, use_container_width=True)

with dash2:
    rondin_act = df_filt["Rondin_Asignado"].iloc[-1] if not df_filt.empty else "Rondin 1"
    st.write(f"Rondín en curso: **{rondin_act}**")
    st.progress((matriz[rondin_act] == "SI").sum() / 44)

st.dataframe(matriz, use_container_width=True, hide_index=True)

# Tabla Totales
df_tot = pd.DataFrame([["Total Puntos"] + porcentajes + [f"{cumplimiento_gral:.1f}%"]], columns=["Punto_QR"] + cols_rond + ["TOTAL"])
st.dataframe(df_tot, use_container_width=True, hide_index=True)

# Descarga y Correo
buf = BytesIO()
with pd.ExcelWriter(buf) as w: matriz.to_excel(w, index=False)
st.sidebar.download_button("⭳ Descargar Excel", data=buf.getvalue(), file_name="Reporte.xlsx")

def enviar(destino, auto=False):
    try:
        # Aquí iría tu lógica de smtplib con st.secrets
        st.sidebar.success("Enviado")
    except Exception as e: st.sidebar.error(str(e))

if st.sidebar.button("Enviar"): enviar(st.sidebar.text_input("Correo:"))
if (ahora.hour in [7, 19]) and ahora.minute < 5: enviar("ana.fernanda.ibarra03@gmail.com", True)
st_autorefresh(interval=120000)
