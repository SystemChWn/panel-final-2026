import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import time
import pytz
import numpy as np
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.message import EmailMessage

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
    
    [data-testid="stSidebar"] {
    display: none !important;}
    button[kind="header"] {
    display: none !important;}
    header {
    visibility: hidden !important;}
    
    </script>
    """, unsafe_allow_html=True)

def obtener_hora_local():
    return datetime.now(pytz.timezone('America/Mexico_City'))

@st.cache_data(ttl=60)
def cargar_datos(url):
    return pd.read_csv(f"{url}&nocache={time.time()}").fillna("")

def asignar_rondines_por_puntos(df):
    if df.empty: return df
    df = df.sort_values(by="Fecha_Hora")
    
    rondines = []
    # Diccionario para rastrear cuántos puntos lleva cada rondín en este turno
    # Estructura: {'DIA': {'Rondin 1': 0, 'Rondin 2': 0...}, 'NOCHE': {...}}
    progreso = {
        'DIA': {f'Rondin {i}': 0 for i in range(1, 7)},
        'NOCHE': {f'Rondin {i}': 0 for i in range(1, 7)}
    }
    
    ultimo_turno = None
    
    for _, fila in df.iterrows():
        hora = fila["Fecha_Hora"].hour
        turno_actual = "DIA" if (7 <= hora < 19) else "NOCHE"
        
        # Si cambia el turno, reseteamos el progreso (o mantenemos si prefieres)
        if ultimo_turno is not None and turno_actual != ultimo_turno:
            # Aquí podrías resetear si quieres que el turno nuevo empiece de cero
            pass 
        
        # Lógica de asignación:
        # Buscamos el primer rondín que tenga menos de 44 puntos (o el límite que definas)
        # En este caso, el Rondín 1 debe llenarse antes de pasar al 2.
        rondin_asignado = "Rondin 1"
        for i in range(1, 7):
            r_nombre = f"Rondin {i}"
            if progreso[turno_actual][r_nombre] < 44: # 44 es el total de puntos
                rondin_asignado = r_nombre
                progreso[turno_actual][r_nombre] += 1
                break
            else:
                rondin_asignado = f"Rondin {i}" # Si ya se llenaron todos, se queda en el último
        
        rondines.append(rondin_asignado)
        ultimo_turno = turno_actual
        
    df["Rondin_Asignado"] = rondines
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

# --- FUNCION DE ENVIO DE CORREO ---
def enviar_correo(destinatario, archivo_bytes, asunto="REPORTE DE RONDINES_SEGURIDAD - CHGW"):
    try:
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = "tu_sistemaschgw@gmail.com" # Tu correo
        msg['To'] = destinatario
        msg.set_content("Se adjunta el reporte de rondines solicitado para su revisión.")
        
        msg.add_attachment(
            archivo_bytes.getvalue(),
            maintype='application',
            subtype='xlsx',
            filename=f"Reporte_Rondines_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        
        # Configuración SMTP (Ejemplo Gmail)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("sistemaschgw@gmail.com", "mlzppevcdubhsart")
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Error al enviar correo")
        return False

# --- SIDEBAR Y FILTROS ---
ahora = obtener_hora_local()

with st.sidebar:
    anio_sel = st.selectbox("AÑO", [2026, 2027, 2028], index=0)
    mes_sel = st.selectbox("MES", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=ahora.month-1)
    mes_num = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(mes_sel) + 1
    dia_sel = st.selectbox("DÍA", list(range(1, 32)), index=ahora.day-1)
    turno_sel = st.selectbox("TURNO", ["DIA", "NOCHE"])
    st.markdown("---")

# --- FILTRADO ---
df_filt = df_raw[(df_raw["Anio_Num"]==anio_sel) & (df_raw["Mes_Num"]==mes_num) & (df_raw["Dia_Num"]==dia_sel)].copy()
if turno_sel == "DIA":
    df_filt = df_filt[(pd.to_datetime(df_filt["Fecha_Hora"]).dt.hour >= 7) & (pd.to_datetime(df_filt["Fecha_Hora"]).dt.hour < 19)]
else:
    df_filt = df_filt[(pd.to_datetime(df_filt["Fecha_Hora"]).dt.hour >= 19) | (pd.to_datetime(df_filt["Fecha_Hora"]).dt.hour < 7)]

# --- MATRIZ ---
cols_rond = ["Rondin 1", "Rondin 2", "Rondin 3", "Rondin 4", "Rondin 5", "Rondin 6"]
matriz = pd.DataFrame({"Punto_QR": [f"Punto {i}" for i in range(1, 45)]})
for col in cols_rond:
    matriz[col] = "—"
    for _, f in df_filt[df_filt["Rondin_Asignado"] == col].iterrows():
        pt = f["Punto_QR"]
        matriz.loc[(matriz["Punto_QR"] == pt) | (matriz["Punto_QR"] == f"Punto {pt}"), col] = "SI"

# ----- CONTEO DE PUNTOS  -----
conteo = (matriz[cols_rond] == 'SI').sum(axis=1)
matriz["Puntos_Visitados"] = conteo.astype(str) + "/6"

# --- FUNCIÓN DE COLORES  ---
def color_semaforo_suave(val):
    v = str(val).strip()
    if v == "SI":
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
    pct = (matriz[col] == 'SI').mean() * 100
    porcentajes_columnas.append(f"{pct:.1f}%")

porcentaje_cumplimiento_general = (matriz[columnas_rondines] == 'SI').sum().sum() / (44 * 6) * 100

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

# --- 6. VISUALIZACIÓN (GRÁFICAS) ---
cumplimiento_gral = (matriz[cols_rond] == 'SI').sum().sum() / (44 * 6) * 100

# Usamos st.container para el efecto decorativo
with st.container(border=True):
    dash1, dash2 = st.columns(2)

    with dash1:
        st.markdown("### Cumplimiento General")
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

    with dash2:
        st.markdown("### Rondín Actual")
        if not df_filt.empty:
            rondin_act = df_filt["Rondin_Asignado"].iloc[-1]
            st.markdown(f"**Rondín en curso:** {rondin_act}")
        else:
            st.markdown("**Rondín en curso:** Sin registros")
            rondin_act = None 
        
        # 2. Conteo de puntos (solo si tenemos un rondín válido)
        puntos_contados = 0
        if rondin_act and rondin_act in cols_rond:
            puntos_contados = (matriz[rondin_act] == "SI").sum()
        
        st.markdown(f"Progreso: {puntos_contados} de 44 puntos escaneados")
        
        # 3. Barra de progreso
        st.progress(min(float(puntos_contados/44), 1.0))
        
        # 4. Nota decorativa con tamaño H2
        st.markdown(
            f"<h2 style='text-align: center; color: #60A5FA;'>TURNO: {turno_sel}</h2>", 
            unsafe_allow_html=True
        )

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
                st.success(f"Correo enviado correctamente.")
        else:
            st.warning("Por favor ingresa un correo primero.")

# --- LÓGICA AUTOMÁTICA ---
ahora = obtener_hora_local()

if (ahora.hour == 7 or ahora.hour == 19) and ahora.minute < 5:
    clave_sesion = f"envio_{ahora.strftime('%Y%m%d%H')}"
    
    if st.session_state.get(clave_sesion) != True:
        buf_auto = BytesIO()
        with pd.ExcelWriter(buf_auto, engine="xlsxwriter") as w:
            matriz.to_excel(w, index=False)
            
        enviar_correo("ana.fernanda,ibarra03@gmail", buf_auto, asunto="REPORTE AUTOMATICO DE TURNO_SEGURIDAD - CHGW")
        st.session_state[clave_sesion] = True # Marcamos como enviado

# --- REFRESH AUTOMATICO ---
st_autorefresh(interval=60000)
