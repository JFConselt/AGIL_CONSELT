import os
from docx import Document
import streamlit as st
from modules.atas import config

# Cache para não ler disco toda hora
@st.cache_data(show_spinner=False)
def load_reference_style():
    full_context = ""
    example_paths = config.get_active_example_paths(max_items=3)
    if not example_paths:
        return "", 0

    for path in example_paths:
        try:
            doc = Document(path)
            txt = " ".join([p.text for p in doc.paragraphs if p.text.strip()])
            full_context += f"--- {os.path.basename(path)} ---\n{txt}\n"
        except: pass
    return full_context, len(example_paths)