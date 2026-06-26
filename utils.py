import smtplib
from email.message import EmailMessage
from datetime import datetime
import streamlit as st

def enviar_correo(destinatario, archivo_bytes, asunto="REPORTE DE RONDINES_SEGURIDAD - CHGW"):
    try:
        # Recuperar credenciales desde los secrets de Streamlit
        email_user = st.secrets["email"]["user"]
        email_pass = st.secrets["email"]["password"]

        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = email_user
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
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Error al enviar correo: {e}")
        return False
