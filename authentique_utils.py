import requests
import json
import difflib
from datetime import datetime, timedelta
import streamlit as st
import pytz
import holidays
import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def calculate_deadline():
    """
    Calcula data de bloqueio (deadline) +2 dias úteis.
    Retorna em formato ISO 8601 com timezone UTC (+00:00).
    """
    # 1. Define Fuso Horário Local e UTC
    try:
        tz_local = pytz.timezone(config.TIMEZONE)
    except:
        tz_local = pytz.timezone('America/Sao_Paulo')
    
    tz_utc = pytz.utc
    
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
        # Verifica se é sábado(5) ou domingo(6)
        if current_date.weekday() >= 5:
            continue
            
        # Verifica feriado
        if current_date.date() in br_holidays:
            continue
            
        days_added += 1
            
    # 4. Define horário final do dia local (23:59:59)
    # Normalização segura para evitar problemas de timezone
    naive_deadline = current_date.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)
    deadline_local = tz_local.localize(naive_deadline)
    
    # 5. Converte para UTC
    deadline_utc = deadline_local.astimezone(tz_utc)
    
    # 6. Retorna formato ISO Padrão (Ex: 2026-02-11T02:59:59+00:00)
    return deadline_utc.isoformat()

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
    """
    Envia para API Authentique V2.
    """
    url = "https://api.autentique.com.br/v2/graphql"
    
    if "AUTHENTIQUE_TOKEN" not in st.secrets:
        raise Exception("Token da Authentique não configurado no secrets.")
        
    token = st.secrets["AUTHENTIQUE_TOKEN"]
    deadline = calculate_deadline()
    
    # --- DEBUGGER PARA VISUALIZAR A DATA ---
    # Isso vai aparecer no seu terminal (console)
    print(f"\n[DEBUG] Deadline Gerado: '{deadline}' (Tipo: {type(deadline)})")
    
    # Isso vai aparecer na tela do Streamlit em Amarelo para você ver na hora
    st.warning(f"🛠️ DEBUG - Data enviada para API: {deadline}")
    # ---------------------------------------
    
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

    # Execução sem tratamento para ver o erro cru
    response = session.post(url, headers=headers, files=files, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")
        
    data = response.json()
    
    if "errors" in data:
        # Retorna o JSON de erro cru da API
        raise Exception(json.dumps(data['errors'], indent=2))
        
    return data["data"]["createDocument"]["id"]