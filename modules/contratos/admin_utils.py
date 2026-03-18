import json
import os
import re
from typing import Dict, List

from modules.contratos import config


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=4)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    normalized = normalized.strip("_")
    return normalized or "modelo"


def _unique_file_path(folder: str, file_name: str) -> str:
    base_name, extension = os.path.splitext(file_name)
    safe_base = _slugify(base_name)
    candidate = os.path.join(folder, f"{safe_base}{extension.lower()}")
    index = 1

    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{safe_base}_{index}{extension.lower()}")
        index += 1

    return candidate


def _to_registry_path(path: str) -> str:
    # Salva no formato POSIX para manter compatibilidade entre Windows/Linux.
    return os.path.relpath(path, config.MODULE_DIR).replace("\\", "/")


def ensure_runtime_files() -> None:
    _ensure_dir(config.MANAGED_TEMPLATES_DIR)

    registry = _read_json(config.TEMPLATE_REGISTRY_PATH, {})
    templates = registry.get("templates", [])
    active_template = registry.get("active_template")
    
    # Rastrear paths resolvidos e IDs existentes para evitar duplicatas
    known_paths = {config._resolve_registry_path(entry.get("template_path")) for entry in templates}
    known_ids = {entry.get("id") for entry in templates}

    # Adicionar modelos padrão se não estiverem presentes
    for model_id, model_data in config.DEFAULT_CONTRACT_MODELS.items():
        if model_id in known_ids or model_data["template_path"] in known_paths:
            continue
        templates.append(
            {
                "id": model_id,
                "label": model_data["label"],
                "template_path": _to_registry_path(model_data["template_path"]),
                "form_type": model_data["form_type"],
                "managed": False,
            }
        )
        known_ids.add(model_id)

    # Adicionar templates gerenciados da pasta
    for file_name in sorted(os.listdir(config.MANAGED_TEMPLATES_DIR)):
        if not file_name.lower().endswith(".docx"):
            continue
        full_path = os.path.join(config.MANAGED_TEMPLATES_DIR, file_name)
        if full_path in known_paths:
            continue
        
        template_id = _slugify(os.path.splitext(file_name)[0])
        # Evitar duplicatas de ID
        if template_id in known_ids:
            continue
            
        templates.append(
            {
                "id": template_id,
                "label": os.path.splitext(file_name)[0],
                "template_path": _to_registry_path(full_path),
                "form_type": "prestacao_servicos",
                "managed": True,
            }
        )
        known_ids.add(template_id)

    if templates and not active_template:
        active_template = templates[0]["id"]

    _write_json(
        config.TEMPLATE_REGISTRY_PATH,
        {
            "active_template": active_template,
            "templates": templates,
        },
    )


def get_template_registry() -> Dict[str, object]:
    ensure_runtime_files()
    return _read_json(config.TEMPLATE_REGISTRY_PATH, {"active_template": None, "templates": []})


def list_templates() -> List[Dict[str, object]]:
    return get_template_registry().get("templates", [])


def set_active_template(template_id: str) -> None:
    registry = get_template_registry()
    registry["active_template"] = template_id
    _write_json(config.TEMPLATE_REGISTRY_PATH, registry)


def save_uploaded_template(file_name: str, file_bytes: bytes, label: str, form_type: str) -> None:
    ensure_runtime_files()
    target_path = _unique_file_path(config.MANAGED_TEMPLATES_DIR, file_name)
    with open(target_path, "wb") as file_obj:
        file_obj.write(file_bytes)

    registry = get_template_registry()
    template_id = _slugify(os.path.splitext(os.path.basename(target_path))[0])
    registry["templates"].append(
        {
            "id": template_id,
            "label": label.strip() or os.path.splitext(os.path.basename(target_path))[0],
            "template_path": _to_registry_path(target_path),
            "form_type": form_type,
            "managed": True,
        }
    )
    registry["active_template"] = template_id
    _write_json(config.TEMPLATE_REGISTRY_PATH, registry)


def delete_template(template_id: str) -> None:
    registry = get_template_registry()
    templates = registry.get("templates", [])
    remaining = []
    fallback_active = None

    for entry in templates:
        if entry.get("id") != template_id:
            if fallback_active is None:
                fallback_active = entry.get("id")
            remaining.append(entry)
            continue

        entry_path = config._resolve_registry_path(entry.get("template_path", ""))
        if entry.get("managed") and entry_path and os.path.exists(entry_path):
            os.remove(entry_path)

    registry["templates"] = remaining
    if registry.get("active_template") == template_id:
        registry["active_template"] = fallback_active
    _write_json(config.TEMPLATE_REGISTRY_PATH, registry)
