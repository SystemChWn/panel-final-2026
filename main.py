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
import re
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

def obtener_hora_local():
    tz = pytz.timezone('America/Mexico_City')
    return datetime.now(tz)
    
# CONFIGURACIÓN DE PÁGINA
st.markdown(
    """
    <style>
    /* Reduce el margen superior de toda la aplicación */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 0rem !important;
        padding-right: 1rem !important;
        padding-left: 1rem !important;
        max-width: 95% !important;
    }

    /* Estilo para los encabezados de las tablas (th) */
    div[data-testid="stDataFrame"] thead tr th {
        background-color: transparent !important;
        color: #555555 !important;
        border-bottom: 2px solid #DDDDDD !important;
        font-weight: bold !important;
    }
    
    /* Si prefieres que el texto del encabezado sea blanco si el fondo fuera oscuro */
    [data-theme="dark"] div[data-testid="stDataFrame"] thead tr th {
        color: #CCCCCC !important;
    }

    /* Elimina el espacio extra arriba del título */
    h1 {
        margin-top: 0px !important;
    }

    /* Esto sube los filtros al máximo posible en la barra lateral */
    [data-testid="stSidebar"] section {
        padding-top: -10rem !important;
    }
    
    /* Esto elimina el margen superior de los widgets (selectbox) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.20rem !important; /* Ajusta este valor si quieres más o menos espacio */
    }
    
/* Forzar al sidebar a no tener altura fija y ignorar el scroll */
    section[data-testid="stSidebar"] {
        height: auto !important;
        overflow: hidden !important;
    }
    
    [data-testid="stSidebarContent"] {
        height: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col_logo, col_titulo = st.columns([0.06, 0.94], gap="small")

with col_logo:
    st.image("https://lh3.googleusercontent.com/d/1YuA-V3W27vrLeDszpzRYNJnwMKGvpHpA", width=55)

with col_titulo:
    st.title("PANEL DE SUPERVISIÓN")

# GOOGLE SHEETS
sheet_id = "1PjB61hZhT1SXO7eRgRgnxo39W2o5AaFdhFTjPz2eb7k"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

# CARGAR DATOS
try:
    df_raw = pd.read_csv(f"{url}&nocache={time.time()}")
except Exception as e:
    st.error(f"Error al cargar datos desde Google Sheets: {e}")
    st.stop()

# LIMPIEZA Y CONVERSIÓN DE FECHAS/HORAS
df_raw = df_raw.fillna("")
st.write(df_raw.columns.tolist())
df_raw["Punto_QR"] = df_raw["Punto_QR"].astype(str).str.replace(".0", "", regex=False).str.strip()

fecha_convertida = pd.to_datetime(df_raw["Fecha_Hora"], errors="coerce", dayfirst=True)
df_raw["Dia_Num"] = fecha_convertida.dt.day.fillna(0).astype(int)
df_raw["Mes_Num"] = fecha_convertida.dt.month.fillna(0).astype(int)
df_raw["Anio_Num"] = fecha_convertida.dt.year.fillna(0).astype(int)
df_raw["Hora_Str"] = fecha_convertida.dt.strftime("%H:%M:%S")
df_raw["Hora_Corta"] = fecha_convertida.dt.strftime("%H:%M")

# =========================================================
# ASIGNACIÓN DE RONDINES
# =========================================================
def determinar_bloque_rondin(hora_texto):
    try:
        h = int(hora_texto[:2])
        if 7 <= h < 9: return "Rondin 1 (07:00-09:00)"
        elif 9 <= h < 11: return "Rondin 2 (09:00-11:00)"
        elif 11 <= h < 13: return "Rondin 3 (11:00-13:00)"
        elif 13 <= h < 15: return "Rondin 4 (13:00-15:00)"
        elif 15 <= h < 17: return "Rondin 5 (15:00-17:00)"
        elif 17 <= h < 19: return "Rondin 6 (17:00-19:00)"
        elif 19 <= h < 21: return "Rondin 1 (19:00-21:00)"
        elif 21 <= h < 23: return "Rondin 2 (21:00-23:00)"
        elif h == 23 or h == 0: return "Rondin 3 (23:00-01:00)"
        elif 1 <= h < 3: return "Rondin 4 (01:00-03:00)"
        elif 3 <= h < 5: return "Rondin 5 (03:00-05:00)"
        elif 5 <= h < 7: return "Rondin 6 (05:00-07:00)"
        return "Fuera de Tiempo"
    except:
        return "Sin Horario"

df_raw["Rondin_Asignado"] = df_raw["Hora_Str"].apply(determinar_bloque_rondin)

ahora = obtener_hora_local() 
hoy_dia = ahora.day
hoy_mes = ahora.month
hoy_anio = ahora.year
hoy_hora = ahora.hour


rondin_actual_en_vivo = determinar_bloque_rondin(ahora.strftime("%H:%M:%S"))

turno_sugerido_idx = 0 if 7 <= hoy_hora < 19 else 1
st_autorefresh(interval=120000)

# =========================================================
# BARRA LATERAL (FILTROS DE BUSQUEDA)
# =========================================================
anios_opciones = [2026, 2027, 2028, 2029, 2030]
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
dias_opciones = list(range(1, 32))

idx_anio = anios_opciones.index(hoy_anio) if hoy_anio in anios_opciones else 0
idx_mes = hoy_mes - 1
idx_dia = hoy_dia - 1

anio_seleccionado = st.sidebar.selectbox("AÑO", anios_opciones, index=idx_anio)
mes_seleccionado = st.sidebar.selectbox("MES", meses_nombres, index=idx_mes)

meses_mapeo = {n: i+1 for i, n in enumerate(meses_nombres)}
numero_mes = meses_mapeo[mes_seleccionado]

dia_seleccionado = st.sidebar.selectbox("DÍA", dias_opciones, index=idx_dia)
turno_seleccionado = st.sidebar.selectbox("TURNO", ["DIA", "NOCHE"], index=turno_sugerido_idx)

df_filtrado_base = df_raw[
    (df_raw["Anio_Num"] == anio_seleccionado) & 
    (df_raw["Mes_Num"] == numero_mes) & 
    (df_raw["Dia_Num"] == dia_seleccionado)
].copy()

# =========================================================
# CONSTRUCCIÓN DE LA MATRIZ DE 44 PUNTOS
# =========================================================
puntos_estaticos = [f"Punto {i}" for i in range(1, 45)]
matriz_construida = pd.DataFrame({"Punto_QR": puntos_estaticos})
matriz_comentarios = pd.DataFrame({"Punto_QR": puntos_estaticos})

if turno_seleccionado == "DIA":
    columnas_rondines = [
        "Rondin 1 (07:00-09:00)", "Rondin 2 (09:00-11:00)", "Rondin 3 (11:00-13:00)", 
        "Rondin 4 (13:00-15:00)", "Rondin 5 (15:00-17:00)", "Rondin 6 (17:00-19:00)"
    ]
else:
    columnas_rondines = [
        "Rondin 1 (19:00-21:00)", "Rondin 2 (21:00-23:00)", "Rondin 3 (23:00-01:00)", 
        "Rondin 4 (01:00-03:00)", "Rondin 5 (03:00-05:00)", "Rondin 6 (05:00-07:00)"
    ]

# Inicializar columnas de la matriz principal
for col in columnas_rondines:
    matriz_construida[col] = "—"

# Inicializar matriz de comentarios
for col in columnas_rondines:
    matriz_comentarios[col] = ""

# Llenar matrices
for col in columnas_rondines:
    registros_rondin = df_filtrado_base[
        df_filtrado_base["Rondin_Asignado"] == col
    ]

    for _, fila_reg in registros_rondin.iterrows():
        pt = fila_reg["Punto_QR"]
        comentario = str(fila_reg.get("Comentarios", "")).strip()

        if pt in puntos_estaticos:
            matriz_construida.loc[
                matriz_construida["Punto_QR"] == pt,
                col
            ] = "SI"

            matriz_comentarios.loc[
                matriz_comentarios["Punto_QR"] == pt,
                col
            ] = comentario

        elif f"Punto {pt}" in puntos_estaticos:
            matriz_construida.loc[
                matriz_construida["Punto_QR"] == f"Punto {pt}",
                col
            ] = "SI"

            matriz_comentarios.loc[
                matriz_comentarios["Punto_QR"] == f"Punto {pt}",
                col
            ] = comentario
            
porcentajes_columnas = []
for col in columnas_rondines:
    conteo_si = (matriz_construida[col] == "SI").sum()
    porcentajes_columnas.append(f"{(conteo_si / 44) * 100:.1f}%")

total_celdas_tabla = matriz_construida[columnas_rondines].size
celdas_con_si = (matriz_construida[columnas_rondines] == "SI").sum().sum()
porcentaje_cumplimiento_general = (celdas_con_si / total_celdas_tabla) * 100 if total_celdas_tabla > 0 else 0

# Calcular columna TOTAL (X/6) para cada renglón
def calcular_acumulado_fila(fila):
    completados = (fila[columnas_rondines] == "SI").sum()
    return f"{completados}/6"

matriz_construida["TOTAL"] = matriz_construida.apply(calcular_acumulado_fila, axis=1)

columnas_ordenadas = ["Punto_QR"] + columnas_rondines + ["TOTAL"]
matriz_construida = matriz_construida[columnas_ordenadas]

# BOTÓN DE DESCARGA EN EL SIDEBAR
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    matriz_construida.to_excel(writer, index=False, sheet_name="Matriz_Rondines")
buffer.seek(0)
fecha_archivo_str = f"{dia_seleccionado:02d}_{numero_mes:02d}_{anio_seleccionado}"
st.sidebar.markdown("---")

# Se agregó un contenedor para asegurar el estilo del botón
st.sidebar.markdown(
    """
    <style>
    div[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
        background-color: #000000 !important; 
        color: #000000 !important;           
        border: 1px solid #000000 !important;
        transition: 0.3s !important;         
    }
    div[data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover {
        background-color: #000000 !important; 
        color: #000000 !important;           
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.download_button(
    label="⭳   Descargar Excel",
    data=buffer,
    file_name=f"Archivo_{fecha_archivo_str}_{turno_seleccionado}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    type="secondary"
)

# =========================================================
# DISTRIBUCIÓN SIMÉTRICA (GRÁFICAS SUPERIORES)
# =========================================================
dash_col1, dash_col2 = st.columns(2, gap="large")

# --- GRÁFICO 1: GRÁFICA DE ARO ---
with dash_col1:
    st.markdown('<p class="graph-title">CUMPLIMIENTO GENERAL DEL TURNO</p>', unsafe_allow_html=True)
    porcentaje_faltante = 100 - porcentaje_cumplimiento_general
    
    df_aro = pd.DataFrame({
        "Estatus": ["Completado", "Pendiente"],
        "Porcentaje": [porcentaje_cumplimiento_general, porcentaje_faltante]
    })
    
    fig_donut = px.pie(
        df_aro,
        values="Porcentaje",
        names="Estatus",
        hole=0.65,
        color="Estatus",
        color_discrete_map={"Completado": "#60A5FA", "Pendiente": "#E9ECEF"}
    )
    fig_donut.update_traces(textinfo="none", hoverinfo="label+percent", hole=0.65)
    fig_donut.update_layout(
        annotations=[dict(text=f"{porcentaje_cumplimiento_general:.1f}%", x=0.5, y=0.5, font_size=24, font_weight="bold", showarrow=False)],
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=190,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

# --- GRÁFICO 2: BARRA DE PROGRESO DE PUNTOS EN VERDE ---
with dash_col2:
    st.markdown('<p class="graph-title">ESTATUS DEL RONDÍN ACTUAL</p>', unsafe_allow_html=True)
    
    # Usamos la variable que calculamos globalmente al inicio (rondin_actual_en_vivo)
    # Si el rondín actual calculado no está en las columnas (ej: fuera de horario), 
    # usamos el primero de la lista de columnas_rondines para evitar errores.
    if rondin_actual_en_vivo in columnas_rondines:
        rondin_a_mostrar = rondin_actual_en_vivo
    else:
        rondin_a_mostrar = columnas_rondines[0]
        
    puntos_completados_ahora = (matriz_construida[rondin_a_mostrar] == "SI").sum()
    porcentaje_barra = puntos_completados_ahora / 44

    st.markdown(f'<p style="font-size: 20px; font-weight: bold; margin-top: 15px;">TURNO: {turno_seleccionado}</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size: 18px; font-weight: bold;">{rondin_a_mostrar}</p>', unsafe_allow_html=True)
    st.markdown(f'<p>Progreso: {puntos_completados_ahora} de 44 puntos escaneados</p>', unsafe_allow_html=True)
    st.progress(float(porcentaje_barra))

# =========================================================
# 1. MATRIZ VISUAL PRINCIPAL (TABLA SUPERIOR)
# =========================================================
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
fecha_pantalla_str = f"{dia_seleccionado:02d}/{numero_mes:02d}/{anio_seleccionado}"
st.subheader(f"MATRIZ DE CONTROL DE RONDINES ({turno_seleccionado}) — FECHA: {fecha_pantalla_str}")

def color_semaforo_suave(val):
    v = str(val).strip()
    if v == "SI":
        return 'background-color: #D4EDDA; color: #155724; font-weight: bold; text-align: center;'
    elif v == "—":
        return 'background-color: #F8D7DA; color: #721C24; text-align: center;'
    return 'text-align: center;'

df_estilizado = (
    matriz_construida.style
    .map(color_semaforo_suave, subset=columnas_rondines)
    .map(
        lambda x: 'text-align: center; font-weight: bold; background-color: transparent;',
        subset=["TOTAL"]
    )
)

st.dataframe(
    df_estilizado,
    use_container_width=True,
    hide_index=True,
    height=600
)

st.subheader("PRUEBA AGGRID")

gb = GridOptionsBuilder.from_dataframe(matriz_construida)

grid_options = gb.build()

AgGrid(
    matriz_construida,
    gridOptions=grid_options,
    height=600,
    fit_columns_on_grid_load=True
)

# =========================================================
# 2. RECUADRO SEPARADO DE ESTADO
# =========================================================
st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

df_recuadro_separado = pd.DataFrame([{
    "Punto_QR": "Total. Puntos",
    columnas_rondines[0]: porcentajes_columnas[0],
    columnas_rondines[1]: porcentajes_columnas[1],
    columnas_rondines[2]: porcentajes_columnas[2],
    columnas_rondines[3]: porcentajes_columnas[3],
    columnas_rondines[4]: porcentajes_columnas[4],
    columnas_rondines[5]: porcentajes_columnas[5],
    "TOTAL": f"{porcentaje_cumplimiento_general:.1f}%"
}])

df_recuadro_separado = df_recuadro_separado[columnas_ordenadas]

def estilar_barra_totales(df):
    estilos = pd.DataFrame('', index=df.index, columns=df.columns)
    estilos["Punto_QR"] = 'background-color: #E9ECEF; color: #212529; font-weight: bold; text-align: center;'
    estilos["TOTAL"] = 'background-color: #155724; color: white; font-weight: bold; text-align: center;'
    for col in columnas_rondines:
        estilos[col] = 'background-color: #C3E6CB; color: #155724; font-weight: bold; text-align: center;'
    return estilos

df_recuadro_estilizado = df_recuadro_separado.style.apply(estilar_barra_totales, axis=None)

configuracion_nombres_cortos = {
    "Punto_QR": st.column_config.Column(label="Col.Compl"),
    columnas_rondines[0]: st.column_config.Column(label="Rondin 1"),
    columnas_rondines[1]: st.column_config.Column(label="Rondin 2"),
    columnas_rondines[2]: st.column_config.Column(label="Rondin 3"),
    columnas_rondines[3]: st.column_config.Column(label="Rondin 4"),
    columnas_rondines[4]: st.column_config.Column(label="Rondin 5"),
    columnas_rondines[5]: st.column_config.Column(label="Rondin 6"),
    "TOTAL": st.column_config.Column(label="Tab.Total")
}

st.dataframe(
    df_recuadro_estilizado,
    use_container_width=True,
    hide_index=True,
    column_config=configuracion_nombres_cortos  # <--- Aplicamos los nuevos nombres aquí
)

# FIRMA PROFESIONAL
st.markdown("---")
st.markdown(
    '<p style="font-size: 8px; color: #aaaaaa; text-align: left; margin-top: 0px;"> Desarrollado y diseñado por: Fernanda Ibarra | Auxiliar de Sistemas Computacionales • Gestión 2026</p>', 
    unsafe_allow_html=True
)

# =========================================================
# ENVIO DE REPORTE AUTOMATICO
# =========================================================
if 'correo_enviado' not in st.session_state:
    st.session_state.correo_enviado = None

# --- FUNCIÓN DE ENVÍO ---
def enviar_email(destino, es_automatico=False):
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Reporte de Rondines - {fecha_archivo_str}"
        msg["From"] = st.secrets["EMAIL_USUARIO"]
        msg["To"] = destino
        msg.set_content("Adjunto encontrarás el reporte solicitado.")
        
        buffer.seek(0)
        msg.add_attachment(
            buffer.read(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"Reporte_{fecha_archivo_str}_{turno_seleccionado}.xlsx"
        )
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(st.secrets["EMAIL_USUARIO"], st.secrets["EMAIL_PASSWORD"])
            smtp.send_message(msg)
        
        # Mensajes personalizados
        if es_automatico:
            st.sidebar.success("Reporte enviado automáticamente")
        else:
            st.sidebar.success("Enviado correctamente")
            
    except Exception as e:
        st.sidebar.error(f"Error al enviar: {e}")

# --- LÓGICA AUTOMÁTICA (CHECKPOINT) ---
ahora = obtener_hora_local() 

if (ahora.hour == 7 or ahora.hour == 19) and ahora.minute < 5:
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    id_envio = f"{fecha_hoy}-{ahora.hour}"
    
    if st.session_state.correo_enviado != id_envio:
        enviar_email(destino="ana.fernanda.ibarra03@gmail.com", es_automatico=True)
        st.session_state.correo_enviado = id_envio

# --- INTERFAZ (SIDEBAR) ---
with st.sidebar:
    st.divider()
    st.subheader("ENTREGA DE REPORTES")
    email_destino = st.text_input("Correo del Destinatario:")
    
    if st.button("Enviar"):
        if not email_destino:
            st.error("Ingresa una dirección válida para continuar.")
        else:
            enviar_email(email_destino, es_automatico=False)
