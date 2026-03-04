import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st

def send_notification_email(file_obj, filename, receivers_list, subject, body_text):
    """
    Envia email dinâmico.
    """
    sender_email = st.secrets["EMAIL_SENDER"]
    password = st.secrets["EMAIL_PASSWORD"]
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    # Garante que receivers_list seja uma lista limpa
    if isinstance(receivers_list, str):
        receivers_list = [r.strip() for r in receivers_list.split(',')]
    
    msg['To'] = ", ".join(receivers_list)
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body_text, 'plain'))
    
    # Anexo (PDF ou DOCX)
    try:
        part = MIMEBase('application', 'octet-stream')
        file_obj.seek(0) # Garante leitura do início
        part.set_payload(file_obj.read()) 
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        
        # Conexão SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receivers_list, text)
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"Erro SMTP: {str(e)}")