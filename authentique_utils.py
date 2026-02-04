import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import difflib
from datetime import datetime, timedelta
import streamlit as st
import pytz
import holidays
import config

def calculate_deadline():
    """Calcula data de bloqueio (deadline) considerando feriados e fds."""
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    
    # Tenta carregar feriados, fallback para vazio se der erro
    try:
        br_holidays = holidays.Brazil(state=config.ESTADO_FERIADOS)
    except:
        br_holidays = {}

    days_added = 0
    current_date = now
    
    # Regra: +2 dias úteis
    while days_added < 2:
        current_date += timedelta(days=1)
        # Se for dia útil (0-4 segunda-sexta) e não for feriado
        if current_date.weekday() < 5 and current_date not in br_holidays:
            days_added += 1
            
    deadline = current_date.replace(hour=23, minute=59, second=59)
    # Formato ISO 8601 compatível com Authentique
    return deadline.strftime('%Y-%m-%dT%H:%M:%S%z')

def get_signers_emails(names_text, emails_db_path='email.json'):
    """
    Retorna:
    - signers: Lista pronta para API
    - missing: Nomes que não foram achados no JSON
    - display_map: Lista de tuplas (Nome Detectado, Email Encontrado) para validação visual
    """
    try:
        with open(emails_db_path, 'r', encoding='utf-8') as f:
            db_emails = json.load(f)
    except FileNotFoundError:
        return [], ["Erro: Arquivo email.json não encontrado"], []

    # Limpeza básica dos nomes
    raw_names = [n.strip().rstrip('.') for n in names_text.split('\n') if n.strip()]
    
    signers = []
    missing = []
    display_map = [] # Para mostrar na UI antes de enviar
    
    known_names = list(db_emails.keys())

    for name in raw_names:
        # 1. Tentativa Exata
        if name in db_emails:
            email = db_emails[name]
            signers.append({"email": email, "action": "SIGN"})
            display_map.append((name, email, "Exato"))
            continue
            
        # 2. Tentativa Aproximada (Fuzzy)
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
    """Envia para API Authentique com sessão resiliente."""
    
    url = "https://api.authentique.com.br/v2/graphql"
    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()
    
    # Configuração da Sessão com Retry
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
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
    
    files = {
        "operations": (None, operations, "application/json"),
        "map": (None, map_data, "application/json"),
        "0": (doc_name, file_obj, "application/pdf")
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = session.post(url, headers=headers, files=files, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Erro API ({response.status_code}): {response.text}")
            
        data = response.json()
        if "errors" in data:
            raise Exception(f"Erro GraphQL: {json.dumps(data['errors'])}")
            
        return data["data"]["createDocument"]["id"]
        
    except Exception as e:
        raise Exception(f"Falha no envio: {str(e)}")