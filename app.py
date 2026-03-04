import streamlit as st
from modules.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="AGIL | Início",
    page_icon="⚙️",
    layout="wide",
)

render_sidebar(active_page="inicio")

st.title("⚙️ AGIL | Início")
st.caption("Plataforma modular para centralizar processos automatizados da CONSELT.")

st.subheader("Interface inicial")

module_options = {
    "ATAs": {
        "description": "Automação de geração e gestão de ATAs da CONSELT.",
        "page": "pages/01_ATAs.py",
        "status": "Disponível",
    },
    "Contratos": {
        "description": "Preenchimento automático de contratos e envio para assinatura via Authentique.",
        "page": "pages/02_Contratos.py",
        "status": "Disponível",
    }
}

selected_module = st.selectbox(
    "Escolha o módulo que deseja acessar:",
    options=list(module_options.keys()),
    index=0,
)

selected_info = module_options[selected_module]
st.write(f"**Status:** {selected_info['status']}")
st.write(selected_info["description"])

if selected_info["page"]:
    if st.button("Acessar módulo", type="primary"):
        st.switch_page(selected_info["page"])
else:
    st.info("Este módulo ainda não está disponível.")
