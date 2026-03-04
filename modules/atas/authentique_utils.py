import requests
import json
import difflib
from datetime import datetime, timedelta
import streamlit as st
import pytz
import holidays
from modules.atas import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def calculate_deadline():
    """
    Calcula data de bloqueio (deadline) +2 dias úteis.
    Retorna no formato ISO 8601 exigido: YYYY-MM-DDTHH:MM:SS.SSSZ
    """
    # 1. Define Fuso Horário Local (Brasília)
    try:
        tz_local = pytz.timezone(config.TIMEZONE)
    except:
        tz_local = pytz.timezone('America/Sao_Paulo')
    
    # Usa data atual no fuso local
    now = datetime.now(tz_local)
    
    # 2. Carrega feriados
    try:
        br_holidays = holidays.Brazil(state=config.ESTADO_FERIADOS)
    except:
        br_holidays = {}

    days_added = 0
    current_date = now
    
    # 3. Lógica de Dias Úteis
    while days_added < 2:
        current_date += timedelta(days=1)
        if current_date.weekday() >= 5: # Sábado/Domingo
            continue
        if current_date.date() in br_holidays:
            continue
            
        days_added += 1
            
    # 4. Formatação ISO 8601 (Conforme Documentação Autentique)
    # A API espera: "2023-11-24T02:59:59.999Z"
    # Ajustamos para o final do dia (23:59:59) e garantimos o sufixo Z
    deadline_iso = current_date.replace(hour=23, minute=59, second=59, microsecond=999000)
    return deadline_iso.strftime('%Y-%m-%dT%H:%M:%S.999Z')

def get_signers_emails(names_text, emails_db_path=config.EMAIL_DB_PATH):
    try:
        with open(emails_db_path, 'r', encoding='utf-8') as f:
            db_emails = json.load(f)
    except FileNotFoundError:
        return [], [f"Erro: Arquivo email.json não encontrado em {emails_db_path}"], []

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
    """
    Envia para API Authentique V2.
    """
    url = "https://api.autentique.com.br/v2/graphql"
    
    if "AUTHENTIQUE_TOKEN" not in st.secrets:
        raise Exception("Token da Authentique não configurado no secrets.")
        
    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()
    
    # Query GraphQL
    query = """
    mutation CreateDocumentMutation($document: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!) {
        createDocument(document: $document, signers: $signers, file: $file) {
            id
            name
            deadline_at
        }
    }
    """
    
    variables = {
        "document": {
            "name": doc_name,
            "deadline_at": deadline
        },
        "signers": signers,
        "file": None
    }
    
    operations = json.dumps({"query": query, "variables": variables})
    map_data = json.dumps({"0": ["variables.file"]})
    
    file_obj.seek(0)
    
    files = {
        "operations": (None, operations, "application/json"),
        "map": (None, map_data, "application/json"),
        "0": (doc_name, file_obj, "application/pdf")
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    response = session.post(url, headers=headers, files=files, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")
        
    data = response.json()
    
    if "errors" in data:
        # Retorna o erro original para diagnóstico
        raise Exception(json.dumps(data['errors'], indent=2))
        
    return data["data"]["createDocument"]["id"]