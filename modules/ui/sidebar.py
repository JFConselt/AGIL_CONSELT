import streamlit as st


def render_sidebar(active_page: str):
    st.markdown(
        """
        <style>
        div[data-testid="stSidebarNav"] {
            display: none;
        }
        div[data-testid="stSidebarNavSeparator"] {
            display: none;
        }
        section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
            color: inherit !important;
            border-color: rgba(250, 250, 250, 0.2) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navegação")
    st.sidebar.caption("Acesse os módulos do sistema")

    items = [
        ("inicio", "🏠 Início", "app.py"),
        ("atas", "📄 ATAs", "pages/01_ATAs.py"),
        ("contratos", "📝 Contratos", "pages/02_Contratos.py"),
    ]

    for key, label, target in items:
        if st.sidebar.button(label, use_container_width=True, disabled=(key == active_page)):
            st.switch_page(target)
