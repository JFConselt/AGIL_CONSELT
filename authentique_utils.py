import requests
import json
import difflib
from datetime import datetime, timedelta
import streamlit as st
import pytz
import holidays
import config

def calculate_deadline():
    """Calcula data de bloqueio (deadline) considerando feriados e fds."""
    try:
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
    except:
        now = datetime.now() # Fallback se timezone falhar
    
    # Tenta carregar feriados
    try:
        br_holidays = holidays.Brazil(state=config.ESTADO_FERIADOS)
    except:
        br_holidays = {}

    days_added = 0
    current_date = now
    
    while days_added < 2:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5 and current_date not in br_holidays:
            days_added += 1
            
    deadline = current_date.replace(hour=23, minute=59, second=59)
    return deadline.strftime('%Y-%m-%dT%H:%M:%S%z')

def get_signers_emails(names_text, emails_db_path='email.json'):
    try:
        with open(emails_db_path, 'r', encoding='utf-8') as f:
            db_emails = json.load(f)
    except FileNotFoundError:
        return [], ["Erro: Arquivo email.json não encontrado"], []

    raw_names = [n.strip().rstrip('.') for n in names_text.split('\n') if n.strip()]
    signers = []
    missing = []
    display_map = []
    
    known_names = list(db_emails.keys())

    for name in raw_names:
        if name in db_emails:
            email = db_emails[name]
            signers.append({"email": email, "action": "SIGN"})
            display_map.append((name, email, "Exato"))
            continue
            
        matches = difflib.get_close_matches(name, known_names, n=1, cutoff=0.6)
        if matches:
            matched_name = matches[0]
            email = db_emails[matched_name]
            signers.append({"email": email, "action": "SIGN"})
            display_map.append((name, email, f"Aproximado de '{matched_name}'"))
        else:
            missing.append(name)
            display_map.append((name, "❌ NÃO ENCONTRADO", "Erro"))

    return signers, missing, display_map

def send_to_authentique(file_obj, signers, doc_name="ATA de Reunião"):
    """Envia para API Authentique com tratamento de erro de conexão."""
    
    url = "https://api.authentique.com.br/v2/graphql"
    
    # Verifica se o token existe
    if "AUTHENTIQUE_TOKEN" not in st.secrets:
        raise Exception("Token da Authentique não configurado no secrets (.streamlit/secrets.toml).")
        
    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()
    
    query = """
    mutation CreateDocument($attributes: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!) {
        createDocument(attributes: $attributes, signers: $signers, file: $file) {
            id
            name
        }
    }
    """
    
    variables = {
        "attributes": {"name": doc_name, "deadline_at": deadline},
        "signers": signers
    }
    
    operations = json.dumps({"query": query, "variables": variables})
    map_data = json.dumps({"0": ["variables.file"]})
    
    # Garante que o ponteiro do arquivo esteja no início
    file_obj.seek(0)
    
    files = {
        "operations": (None, operations, "application/json"),
        "map": (None, map_data, "application/json"),
        "0": (doc_name, file_obj, "application/pdf")
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Timeout aumentado para 60s devido a redes instáveis
        response = requests.post(url, headers=headers, files=files, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Erro API ({response.status_code}): {response.text}")
            
        data = response.json()
        if "errors" in data:
            raise Exception(f"Erro Retornado pela Authentique: {json.dumps(data['errors'])}")
            
        return data["data"]["createDocument"]["id"]
        
    except requests.exceptions.ConnectionError:
        raise Exception("Erro de Conexão: Não foi possível acessar o servidor da Authentique (DNS falhou). Verifique sua internet ou se há bloqueio de firewall.")
    except requests.exceptions.Timeout:
        raise Exception("Erro de Tempo: A conexão com a Authentique demorou muito. Tente novamente.")
    except Exception as e:
        raise Exception(f"Falha no envio: {str(e)}")