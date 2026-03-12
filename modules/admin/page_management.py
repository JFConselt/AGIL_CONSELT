import json
import os

import streamlit as st

from modules.atas import admin_utils as atas_admin_utils
from modules.contratos import admin_utils as contratos_admin_utils
from modules.ui.sidebar import render_sidebar


def _reset_runtime_caches() -> None:
    st.cache_data.clear()


def _render_atas_prompts_tab() -> None:
    st.subheader("Prompts de IA")
    prompts = atas_admin_utils.load_prompts()

    with st.form("atas_prompts_form"):
        transparencias_prompt = st.text_area(
            "Prompt de Transparências",
            value=prompts["transparencias"],
            height=320,
        )
        pautas_prompt = st.text_area(
            "Prompt de Pautas",
            value=prompts["pautas"],
            height=320,
        )
        save = st.form_submit_button("Salvar prompts", type="primary")
        restore = st.form_submit_button("Restaurar padrão")

    if save:
        atas_admin_utils.save_prompts(
            {
                "transparencias": transparencias_prompt,
                "pautas": pautas_prompt,
            }
        )
        _reset_runtime_caches()
        st.success("Prompts atualizados.")
        st.rerun()

    if restore:
        atas_admin_utils.restore_default_prompts()
        _reset_runtime_caches()
        st.success("Prompts restaurados para o padrão atual.")
        st.rerun()


def _render_atas_members_tab() -> None:
    st.subheader("Membros e e-mails")
    members = atas_admin_utils.load_members()
    rows = [{"Nome": name, "Email": email} for name, email in members.items()]
    edited_rows = st.data_editor(rows, num_rows="dynamic", use_container_width=True, key="atas_members_editor")

    col_save, col_download = st.columns([1, 1])
    if col_save.button("Salvar lista de membros", type="primary"):
        updated_members = {
            str(row.get("Nome", "")).strip(): str(row.get("Email", "")).strip()
            for row in edited_rows
            if str(row.get("Nome", "")).strip() and str(row.get("Email", "")).strip()
        }
        atas_admin_utils.save_members(updated_members)
        _reset_runtime_caches()
        st.success("Lista de membros atualizada.")
        st.rerun()

    col_download.download_button(
        "Baixar JSON atual",
        data=json.dumps(members, ensure_ascii=False, indent=4),
        file_name="email.json",
        mime="application/json",
    )

    uploaded_json = st.file_uploader("Importar lista de membros (.json)", type=["json"], key="atas_members_upload")
    if uploaded_json and st.button("Aplicar JSON importado"):
        imported = uploaded_json.getvalue().decode("utf-8")
        try:
            atas_admin_utils.save_members(json.loads(imported))
        except json.JSONDecodeError as error:
            st.error(f"JSON inválido: {error}")
        else:
            _reset_runtime_caches()
            st.success("Lista importada com sucesso.")
            st.rerun()


def _render_atas_templates_tab() -> None:
    st.subheader("Template de ATA")
    templates = atas_admin_utils.list_templates()
    registry = atas_admin_utils.get_template_registry()
    active_template_id = registry.get("active_template")

    if templates:
        selected_template_id = st.selectbox(
            "Template ativo",
            options=[entry["id"] for entry in templates],
            index=max(0, next((index for index, entry in enumerate(templates) if entry["id"] == active_template_id), 0)),
            format_func=lambda template_id: next(entry["label"] for entry in templates if entry["id"] == template_id),
            key="atas_active_template",
        )

        if st.button("Definir como ativo", key="atas_set_active_template"):
            atas_admin_utils.set_active_template(selected_template_id)
            _reset_runtime_caches()
            st.success("Template ativo atualizado.")
            st.rerun()

        selected_entry = next(entry for entry in templates if entry["id"] == selected_template_id)
        st.write(f"Arquivo: {selected_entry['path']}")
        st.write(f"Gerenciado pela central: {'Sim' if selected_entry.get('managed') else 'Não'}")
        if selected_entry.get("managed") and st.button("Excluir template selecionado", key="atas_delete_template"):
            atas_admin_utils.delete_template(selected_template_id)
            _reset_runtime_caches()
            st.success("Template removido.")
            st.rerun()

    upload_template = st.file_uploader("Adicionar novo template (.docx)", type=["docx"], key="atas_template_upload")
    template_label = st.text_input("Nome de exibição do template", key="atas_template_label")
    if upload_template and st.button("Salvar novo template", key="atas_save_template"):
        atas_admin_utils.save_uploaded_template(upload_template.name, upload_template.getvalue(), template_label)
        _reset_runtime_caches()
        st.success("Novo template salvo e ativado.")
        st.rerun()


def _render_atas_examples_tab() -> None:
    st.subheader("Acervo de conhecimento")
    examples = atas_admin_utils.list_examples()
    current_active = [entry["file_name"] for entry in examples if entry["active"]]
    active_names = st.multiselect(
        "Atas ativas para few-shot",
        options=[entry["file_name"] for entry in examples],
        default=current_active,
        key="atas_examples_active",
    )
    if st.button("Salvar seleção do acervo", key="atas_save_examples"):
        atas_admin_utils.save_examples_selection(active_names)
        _reset_runtime_caches()
        st.success("Acervo ativo atualizado.")
        st.rerun()

    if examples:
        st.dataframe(
            [
                {
                    "Arquivo": entry["file_name"],
                    "Ativo": entry["active"],
                    "Tamanho (KB)": entry["size_kb"],
                }
                for entry in examples
            ],
            use_container_width=True,
            hide_index=True,
        )
        delete_name = st.selectbox(
            "Excluir item do acervo",
            options=[""] + [entry["file_name"] for entry in examples],
            key="atas_delete_example_select",
        )
        if delete_name and st.button("Excluir item selecionado", key="atas_delete_example"):
            atas_admin_utils.delete_example(delete_name)
            _reset_runtime_caches()
            st.success("Arquivo removido do acervo.")
            st.rerun()

    upload_examples = st.file_uploader(
        "Adicionar documentos ao acervo (.docx)",
        type=["docx"],
        accept_multiple_files=True,
        key="atas_examples_upload",
    )
    if upload_examples and st.button("Salvar documentos no acervo", key="atas_save_examples_upload"):
        for uploaded in upload_examples:
            atas_admin_utils.save_uploaded_example(uploaded.name, uploaded.getvalue())
        _reset_runtime_caches()
        st.success("Documentos adicionados ao acervo.")
        st.rerun()


def _render_contratos_templates_tab() -> None:
    st.subheader("Modelos de contrato")
    templates = contratos_admin_utils.list_templates()
    registry = contratos_admin_utils.get_template_registry()
    active_template_id = registry.get("active_template")

    if templates:
        selected_template_id = st.selectbox(
            "Modelo ativo",
            options=[entry["id"] for entry in templates],
            index=max(0, next((index for index, entry in enumerate(templates) if entry["id"] == active_template_id), 0)),
            format_func=lambda template_id: next(entry["label"] for entry in templates if entry["id"] == template_id),
            key="contratos_active_template",
        )

        if st.button("Definir modelo ativo", key="contratos_set_active_template"):
            contratos_admin_utils.set_active_template(selected_template_id)
            _reset_runtime_caches()
            st.success("Modelo ativo atualizado.")
            st.rerun()

        selected_entry = next(entry for entry in templates if entry["id"] == selected_template_id)
        st.write(f"Arquivo: {selected_entry['template_path']}")
        st.write(f"Tipo de formulário: {selected_entry['form_type']}")
        if selected_entry.get("managed") and st.button("Excluir modelo selecionado", key="contratos_delete_template"):
            contratos_admin_utils.delete_template(selected_template_id)
            _reset_runtime_caches()
            st.success("Modelo removido.")
            st.rerun()

    upload_template = st.file_uploader("Adicionar novo modelo (.docx)", type=["docx"], key="contratos_template_upload")
    template_label = st.text_input("Nome de exibição do modelo", key="contratos_template_label")
    form_type = st.selectbox(
        "Tipo de formulário",
        options=["prestacao_servicos", "parcerias"],
        key="contratos_form_type",
    )
    if upload_template and st.button("Salvar novo modelo", key="contratos_save_template"):
        contratos_admin_utils.save_uploaded_template(
            upload_template.name,
            upload_template.getvalue(),
            template_label,
            form_type,
        )
        _reset_runtime_caches()
        st.success("Novo modelo salvo e ativado.")
        st.rerun()


atas_admin_utils.ensure_runtime_files()
contratos_admin_utils.ensure_runtime_files()

st.set_page_config(page_title="AGIL | Gerenciamento", page_icon="🛠️", layout="wide")

render_sidebar(active_page="gerenciamento")

st.title("🛠️ AGIL | Gerenciamento")
st.caption("Central administrativa do sistema para gestão operacional de ATAs e Contratos.")

tab_atas, tab_contratos = st.tabs(["ATAs", "Contratos"])

with tab_atas:
    subtab_prompts, subtab_membros, subtab_templates, subtab_acervo = st.tabs(
        ["Prompts IA", "Membros", "Template", "Acervo"]
    )
    with subtab_prompts:
        _render_atas_prompts_tab()
    with subtab_membros:
        _render_atas_members_tab()
    with subtab_templates:
        _render_atas_templates_tab()
    with subtab_acervo:
        _render_atas_examples_tab()

with tab_contratos:
    _render_contratos_templates_tab()
