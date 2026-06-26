import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from io import BytesIO
import time
import pytz
import numpy as np
from streamlit_autorefresh import st_autorefresh
from utils import enviar_correo

st.set_page_config(layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    /* Ajustes generales */
    .block-container { padding-top: 2rem !important; }
    h1 { margin-top: -10px !important; }
            
    /* Esto elimina el margen superior de los widgets (selectbox) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.20rem !important; /* Ajusta este valor si quieres más o menos espacio */
    }
    
    /* Forzar al sidebar a no tener altura fija y ignorar el scroll */
    section[data-testid="stSidebar"] {
        height: auto !important;
        overflow: hidden !important;
    }
            
    /* Esta es la clave: esto elimina el contenedor que obliga a que el sidebar sea alto */
    [data-testid="stSidebarContent"] {
        height: auto !important;
    }
            
    /* El botón se adaptará automáticamente al tema*/
    div.stDownloadButton > button {
        width: 200%;
        height: 50px;
        font-weight: bold;
        border: 2px solid #60A5FA;
        /* Quitamos el fondo fijo para que respete el tema de Streamlit */
        background-color: transparent; 
        transition: 0.3s;
    }
    
    /* Efecto al pasar el mouse por encima */
    div.stDownloadButton > button:hover {
        background-color: #60A5FA;
        color: white;
    }
            
    footer {visibility: hidden;}

    /* Eliminar el bloque de margen inferior del bloque principal */
    .block-container {
        padding-bottom: 0rem !important;
        margin-bottom: 0rem !important;
    }

    /* Eliminar el espacio extra del último elemento en la página */
    div[data-testid="stVerticalBlock"] > div:last-child {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
            
    </script>
    """, unsafe_allow_html=True)

def obtener_hora_local():
    return datetime.now(pytz.timezone('America/Mexico_City'))

@st.cache_data(ttl=60)
def cargar_datos(url):
    return pd.read_csv(f"{url}&nocache={time.time()}").fillna("")

def asignar_rondines_por_puntos(df):
    if df.empty: return df
    df = df.sort_values(by="Fecha_Hora").reset_index(drop=True)
    
    # Función auxiliar: obtiene el bloque de tiempo de una hora fraccionaria
    def get_block(hora_frac):
        if   7.5 <= hora_frac < 9.5:   return "Rondin 1"
        elif 9.5 <= hora_frac < 11.5:  return "Rondin 2"
        elif 11.5 <= hora_frac < 13.5: return "Rondin 3"
        elif 13.5 <= hora_frac < 15.5: return "Rondin 4"
        elif 15.5 <= hora_frac < 17.5: return "Rondin 5"
        elif 17.5 <= hora_frac < 19.5: return "Rondin 6"
        elif 19.5 <= hora_frac < 21.5: return "Rondin 1"
        elif 21.5 <= hora_frac < 23.5: return "Rondin 2"
        elif hora_frac >= 23.5 or hora_frac < 1.5: return "Rondin 3"
        elif 1.5 <= hora_frac < 3.5:   return "Rondin 4"
        elif 3.5 <= hora_frac < 5.5:   return "Rondin 5"
        elif 5.5 <= hora_frac < 7.5:   return "Rondin 6"
        else: return "Sin Asignar"
    
    # Paso 1: Agrupar escaneos en recorridos completos.
    # Si hay un silencio de más de 30 minutos entre escaneos, se considera un recorrido nuevo.
    GAP_MINUTOS = 30
    group_id = 0
    groups = [0]
    for i in range(1, len(df)):
        delta_min = (df.loc[i, "Fecha_Hora"] - df.loc[i-1, "Fecha_Hora"]).total_seconds() / 60
        if delta_min > GAP_MINUTOS:
            group_id += 1
        groups.append(group_id)
    df["_group"] = groups
    
    # Paso 2: Para cada grupo, asignar el rondín donde cayó la MAYORÍA de los puntos.
    group_assignments = {}
    for gid, gdf in df.groupby("_group"):
        hora_fracs = gdf["Fecha_Hora"].apply(lambda x: x.hour + x.minute / 60.0)
        blocks = hora_fracs.apply(get_block)
        group_assignments[gid] = blocks.value_counts().idxmax()
    
    # Paso 3: Asignar el rondín a todos los escaneos del grupo
    df["Rondin_Asignado"] = df["_group"].map(group_assignments)
    df = df.drop(columns=["_group"])
    
    return df

# --- CARGA DATOS ---
sheet_id = "1PjB61hZhT1SXO7eRgRgnxo39W2o5AaFdhFTjPz2eb7k"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
try:
    df_raw = cargar_datos(url)
    
    # 1. Limpiamos espacios y quitamos ".0" del Punto QR
    df_raw["Punto_QR"] = df_raw["Punto_QR"].astype(str).str.replace(".0", "", regex=False).str.strip()
    
    # 2. CONVERSIÓN DE FECHA FORZADA
    # Le decimos explícitamente: dayfirst=True y el formato %d/%m/%Y %H:%M:%S
    df_raw["Fecha_Hora"] = pd.to_datetime(
        df_raw["Fecha_Hora"].str.strip(), 
        format="%d/%m/%Y %H:%M:%S", 
        errors="coerce"
    )
    
    # Eliminamos filas donde la fecha no se pudo convertir
    df_raw = df_raw.dropna(subset=["Fecha_Hora"])
    
    # 3. Ahora extraemos los componentes
    df_raw["Dia_Num"] = df_raw["Fecha_Hora"].dt.day
    df_raw["Mes_Num"] = df_raw["Fecha_Hora"].dt.month
    df_raw["Anio_Num"] = df_raw["Fecha_Hora"].dt.year
    
    # 4. Asignación de rondines
    df_raw = asignar_rondines_por_puntos(df_raw)

except Exception as e:
    st.error(f"Error crítico en la fecha: {e}")
    st.stop()



# --- SIDEBAR Y FILTROS ---
ahora = obtener_hora_local()

with st.sidebar:
    with st.expander("📋 Instrucciones de uso"):
        st.markdown("""
    **☀️ TURNO DÍA**  
    07:30 AM → 07:30 PM  
    *(del día seleccionado)*
    
    **🌙 TURNO NOCHE**  
    07:30 PM → 07:30 AM  
    *(inicia el día seleccionado y termina el día siguiente)*
    
    > Selecciona el día en que **inició** el turno.  
    > Ejemplo: la noche del 25 al 26, selecciona el día **25**.
        """)
    anio_sel = st.selectbox("AÑO", [2026, 2027, 2028], index=0)
    mes_sel = st.selectbox("MES", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=ahora.month-1)
    mes_num = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(mes_sel) + 1
    dia_sel = st.selectbox("DÍA (inicio de turno)", list(range(1, 32)), index=ahora.day-1)
    turno_sel = st.selectbox("TURNO", ["DIA", "NOCHE"])
    
    # Información visual del rango del turno
    fecha_sel = datetime(anio_sel, mes_num, dia_sel)
    if turno_sel == "DIA":
        inicio_turno = fecha_sel + timedelta(hours=7, minutes=30)
        fin_turno    = fecha_sel + timedelta(hours=19, minutes=30)
    else:
        inicio_turno = fecha_sel + timedelta(hours=19, minutes=30)
        fin_turno    = fecha_sel + timedelta(days=1, hours=7, minutes=30)
    st.caption(f"🕒 {inicio_turno.strftime('%d/%m %H:%M')} → {fin_turno.strftime('%d/%m %H:%M')}")
    st.markdown("---")

# --- FILTRADO ---
# Filtramos por el rango exacto del turno (no por día del calendario).
# DIA:   dd/mm 07:30 → dd/mm 19:30
# NOCHE: dd/mm 19:30 → (dd+1)/mm 07:30
df_filt = df_raw[
    (df_raw["Fecha_Hora"] >= inicio_turno) &
    (df_raw["Fecha_Hora"] <  fin_turno)
].copy()

# --- MATRIZ ---
cols_rond = ["Rondin 1", "Rondin 2", "Rondin 3", "Rondin 4", "Rondin 5", "Rondin 6"]
matriz = pd.DataFrame({"Punto_QR": [f"Punto {i}" for i in range(1, 45)]})
for col in cols_rond:
    rondin_data = df_filt[df_filt["Rondin_Asignado"] == col]
    if rondin_data.empty:
        matriz[col] = "—"
    else:
        # Aseguramos el formato "Punto X" para el mapeo
        pts = "Punto " + rondin_data["Punto_QR"].astype(str).str.replace("Punto ", "", regex=False)
        horas = pd.to_datetime(rondin_data["Fecha_Hora"]).dt.strftime("%H:%M")
        hora_map = dict(zip(pts, horas))
        matriz[col] = matriz["Punto_QR"].map(lambda x: f"SI ({hora_map[x]})" if x in hora_map else "—")

# ----- CONTEO DE PUNTOS  -----
conteo = matriz[cols_rond].apply(lambda c: c.str.startswith('SI', na=False)).sum(axis=1)
matriz["Puntos_Visitados"] = conteo.astype(str) + "/6"

# --- FUNCIÓN DE COLORES  ---
def color_semaforo_suave(val):
    v = str(val).strip()
    if v.startswith("SI"):
        return 'background-color: #D4EDDA; color: #155724; font-weight: bold; text-align: center;'
    elif v == "—":
        return 'background-color: #F8D7DA; color: #721C24; text-align: center;'
    return 'text-align: center;'

matriz_estilizada = matriz.style.map(
    color_semaforo_suave, 
    subset=cols_rond
).map(
    lambda x: 'text-align: center; font-weight: bold; background-color: transparent;', 
    subset=["Puntos_Visitados"]
)

# ---- TABLA SEPARADA -----
columnas_rondines = ["Rondin 1", "Rondin 2", "Rondin 3", "Rondin 4", "Rondin 5", "Rondin 6"]
columnas_ordenadas = ["Punto_QR"] + columnas_rondines + ["TOTAL"]

porcentajes_columnas = []
for col in columnas_rondines:
    pct = matriz[col].str.startswith('SI', na=False).mean() * 100
    porcentajes_columnas.append(f"{pct:.1f}%")

porcentaje_cumplimiento_general = matriz[columnas_rondines].apply(lambda c: c.str.startswith('SI', na=False)).sum().sum() / (44 * 6) * 100

df_recuadro_separado = pd.DataFrame([{
    "Punto_QR": "TOTAL PUNTOS",
    columnas_rondines[0]: porcentajes_columnas[0],
    columnas_rondines[1]: porcentajes_columnas[1],
    columnas_rondines[2]: porcentajes_columnas[2],
    columnas_rondines[3]: porcentajes_columnas[3],
    columnas_rondines[4]: porcentajes_columnas[4],
    columnas_rondines[5]: porcentajes_columnas[5],
    "TOTAL": f"{porcentaje_cumplimiento_general:.1f}%"
}])

# --- INTERFAZ PRINCIPAL ---
col_logo, col_titulo = st.columns([0.06, 0.74], vertical_alignment="center")
with col_logo: st.image("https://lh3.googleusercontent.com/d/1YuA-V3W27vrLeDszpzRYNJnwMKGvpHpA", width=55)
with col_titulo: st.title("PANEL DE SUPERVISIÓN")

# --- 6. VISUALIZACIÓN (GRÁFICAS Y MÉTRICAS) ---
puntos_totales_visitados = matriz[cols_rond].apply(lambda c: c.str.startswith('SI', na=False)).sum().sum()
cumplimiento_gral = puntos_totales_visitados / (44 * 6) * 100

with st.container(border=True):
    col_pie, col_metrics, col_progreso = st.columns([1.2, 1, 1.2])

    with col_pie:
        st.markdown("### 📊 Cumplimiento General")
        fig = px.pie(
            values=[cumplimiento_gral, 100-cumplimiento_gral], 
            names=["Completado", "Pendiente"], 
            hole=0.7, 
            color_discrete_map={"Completado": "#60A5FA", "Pendiente": "#262730"}
        )
        fig.update_layout(
            height=180, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
            annotations=[dict(text=f"{cumplimiento_gral:.1f}%", showarrow=False, font_size=25, font_color="white")]
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_metrics:
        st.markdown("### 📈 Estadísticas")
        st.metric("Puntos Totales (Turno)", f"{puntos_totales_visitados} / {44 * 6}")
        
        rondin_act = df_filt["Rondin_Asignado"].iloc[-1] if not df_filt.empty else None
        estado_rondin = rondin_act if rondin_act else "Sin registros"
        st.metric("Rondín en Curso", estado_rondin)
        
        st.markdown(f"<h3 style='text-align: center; color: #60A5FA;'>Turno: {turno_sel}</h3>", unsafe_allow_html=True)

    with col_progreso:
        st.markdown("### 📍 Progreso Actual")
        puntos_contados = 0
        if rondin_act and rondin_act in cols_rond:
            puntos_contados = matriz[rondin_act].str.startswith("SI", na=False).sum()
        
        st.metric("Puntos del Rondín", f"{puntos_contados} / 44")
        st.progress(min(float(puntos_contados/44), 1.0))

# -----------------------------------------------------------------------------------------------------------------------

st.dataframe(
    matriz_estilizada, 
    use_container_width=True, 
    hide_index=True,
    height=500
)

st.table(df_recuadro_separado)

# --- SIDEBAR (DESCARGA Y CORREO) ---
with st.sidebar:
    # 1. Lógica del nombre del archivo dinámico
    fecha_hoy = obtener_hora_local().strftime("%d-%m-%Y")
    # Usamos turno_sel que ya tienes definido en tu sidebar
    nombre_archivo = f"RONDINES_{fecha_hoy}_{turno_sel}.xlsx"
    
    # 2. Generación del archivo en memoria
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        matriz.to_excel(w, index=False)
        
    # 3. Botón de descarga
    st.download_button(
        label="⭳ Descargar Excel", 
        data=buf.getvalue(), 
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # ENTREGA DE REPORTES AUTOMATICO
    st.divider()
    st.subheader("ENTREGA DE REPORTES")
    email_destino = st.text_input("Correo del Destinatario:")
    
    if st.button("Enviar Correo"):
        if email_destino:
            # Reutilizamos el 'buf' que generamos arriba para la descarga
            if enviar_correo(email_destino, buf):
                st.toast("Correo enviado correctamente.", icon="✅")
        else:
            st.toast("Por favor ingresa un correo primero.", icon="⚠️")

# --- LÓGICA AUTOMÁTICA ---
ahora = obtener_hora_local()

if (ahora.hour == 7 or ahora.hour == 19) and (30 <= ahora.minute < 35):
    clave_sesion = f"envio_{ahora.strftime('%Y%m%d%H')}"
    
    if st.session_state.get(clave_sesion) != True:
        buf_auto = BytesIO()
        with pd.ExcelWriter(buf_auto, engine="xlsxwriter") as w:
            matriz.to_excel(w, index=False)
            
        enviar_correo("ana.fernanda.ibarra03@gmail.com", buf_auto, asunto="REPORTE AUTOMATICO DE TURNO_SEGURIDAD - CHGW")
        st.session_state[clave_sesion] = True # Marcamos como enviado

# --- REFRESH AUTOMATICO ---
st_autorefresh(interval=60000)
