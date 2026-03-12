import json
import os
import re
from typing import Dict, List

from modules.atas import config


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
    return normalized or "arquivo"


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
    return os.path.relpath(path, config.MODULE_DIR)


def _default_template_entry() -> Dict[str, object]:
    return {
        "id": "modelo_ata_padrao",
        "label": "Modelo de ATA padrão",
        "path": _to_registry_path(config.MODEL_DOCX_PATH),
        "managed": False,
    }


def ensure_runtime_files() -> None:
    _ensure_dir(config.ATA_TEMPLATES_DIR)
    _ensure_dir(config.EXAMPLES_DIR)

    if not os.path.exists(config.AI_PROMPTS_PATH):
        _write_json(
            config.AI_PROMPTS_PATH,
            {
                "transparencias": config.DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM,
                "pautas": config.DEFAULT_PROMPT_PAUTAS_SYSTEM,
            },
        )

    registry = _read_json(config.ATA_TEMPLATE_REGISTRY_PATH, {})
    templates = registry.get("templates", [])
    known_paths = {config._resolve_registry_path(entry.get("path")) for entry in templates}
    active_template = registry.get("active_template")

    if os.path.exists(config.MODEL_DOCX_PATH) and config.MODEL_DOCX_PATH not in known_paths:
        templates.insert(0, _default_template_entry())

    for file_name in sorted(os.listdir(config.ATA_TEMPLATES_DIR)):
        if not file_name.lower().endswith(".docx"):
            continue
        full_path = os.path.join(config.ATA_TEMPLATES_DIR, file_name)
        if full_path in known_paths:
            continue
        templates.append(
            {
                "id": _slugify(os.path.splitext(file_name)[0]),
                "label": os.path.splitext(file_name)[0],
                "path": _to_registry_path(full_path),
                "managed": True,
            }
        )

    if templates and not active_template:
        active_template = templates[0]["id"]

    _write_json(
        config.ATA_TEMPLATE_REGISTRY_PATH,
        {
            "active_template": active_template,
            "templates": templates,
        },
    )

    examples_registry = _read_json(config.EXAMPLES_REGISTRY_PATH, {})
    available_examples = [
        file_name
        for file_name in sorted(os.listdir(config.EXAMPLES_DIR), reverse=True)
        if file_name.lower().endswith(".docx") and not file_name.startswith("~$")
    ]
    active_examples = examples_registry.get("active_examples")
    if not active_examples:
        active_examples = available_examples[:3]

    _write_json(
        config.EXAMPLES_REGISTRY_PATH,
        {
            "active_examples": [file_name for file_name in active_examples if file_name in available_examples],
        },
    )


def load_prompts() -> Dict[str, str]:
    ensure_runtime_files()
    prompts = _read_json(config.AI_PROMPTS_PATH, {})
    return {
        "transparencias": prompts.get("transparencias", config.DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM),
        "pautas": prompts.get("pautas", config.DEFAULT_PROMPT_PAUTAS_SYSTEM),
    }


def save_prompts(prompts: Dict[str, str]) -> None:
    ensure_runtime_files()
    _write_json(
        config.AI_PROMPTS_PATH,
        {
            "transparencias": prompts.get("transparencias", config.DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM),
            "pautas": prompts.get("pautas", config.DEFAULT_PROMPT_PAUTAS_SYSTEM),
        },
    )


def restore_default_prompts() -> None:
    save_prompts(
        {
            "transparencias": config.DEFAULT_PROMPT_TRANSPARENCIAS_SYSTEM,
            "pautas": config.DEFAULT_PROMPT_PAUTAS_SYSTEM,
        }
    )


def load_members() -> Dict[str, str]:
    return _read_json(config.EMAIL_DB_PATH, {})


def save_members(members: Dict[str, str]) -> None:
    cleaned = {
        name.strip(): email.strip()
        for name, email in members.items()
        if name and name.strip() and email and email.strip()
    }
    _write_json(config.EMAIL_DB_PATH, dict(sorted(cleaned.items(), key=lambda item: item[0].lower())))


def get_template_registry() -> Dict[str, object]:
    ensure_runtime_files()
    return _read_json(config.ATA_TEMPLATE_REGISTRY_PATH, {"active_template": None, "templates": []})


def list_templates() -> List[Dict[str, object]]:
    return get_template_registry().get("templates", [])


def set_active_template(template_id: str) -> None:
    registry = get_template_registry()
    registry["active_template"] = template_id
    _write_json(config.ATA_TEMPLATE_REGISTRY_PATH, registry)


def save_uploaded_template(file_name: str, file_bytes: bytes, label: str) -> None:
    ensure_runtime_files()
    target_path = _unique_file_path(config.ATA_TEMPLATES_DIR, file_name)
    with open(target_path, "wb") as file_obj:
        file_obj.write(file_bytes)

    registry = get_template_registry()
    template_id = _slugify(os.path.splitext(os.path.basename(target_path))[0])
    registry["templates"].append(
        {
            "id": template_id,
            "label": label.strip() or os.path.splitext(os.path.basename(target_path))[0],
            "path": _to_registry_path(target_path),
            "managed": True,
        }
    )
    registry["active_template"] = template_id
    _write_json(config.ATA_TEMPLATE_REGISTRY_PATH, registry)


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

        entry_path = config._resolve_registry_path(entry.get("path", ""))
        if entry.get("managed") and entry_path and os.path.exists(entry_path):
            os.remove(entry_path)

    registry["templates"] = remaining
    if registry.get("active_template") == template_id:
        registry["active_template"] = fallback_active
    _write_json(config.ATA_TEMPLATE_REGISTRY_PATH, registry)


def list_examples() -> List[Dict[str, object]]:
    ensure_runtime_files()
    registry = _read_json(config.EXAMPLES_REGISTRY_PATH, {"active_examples": []})
    active_names = set(registry.get("active_examples", []))
    examples = []

    for file_name in sorted(os.listdir(config.EXAMPLES_DIR), reverse=True):
        if not file_name.lower().endswith(".docx") or file_name.startswith("~$"):
            continue
        file_path = os.path.join(config.EXAMPLES_DIR, file_name)
        examples.append(
            {
                "file_name": file_name,
                "path": file_path,
                "active": file_name in active_names,
                "size_kb": round(os.path.getsize(file_path) / 1024, 1),
            }
        )

    return examples


def save_examples_selection(active_names: List[str]) -> None:
    ensure_runtime_files()
    valid_names = {entry["file_name"] for entry in list_examples()}
    _write_json(
        config.EXAMPLES_REGISTRY_PATH,
        {"active_examples": [file_name for file_name in active_names if file_name in valid_names]},
    )


def save_uploaded_example(file_name: str, file_bytes: bytes) -> None:
    ensure_runtime_files()
    target_path = _unique_file_path(config.EXAMPLES_DIR, file_name)
    with open(target_path, "wb") as file_obj:
        file_obj.write(file_bytes)

    registry = _read_json(config.EXAMPLES_REGISTRY_PATH, {"active_examples": []})
    active_examples = registry.get("active_examples", [])
    active_examples.append(os.path.basename(target_path))
    registry["active_examples"] = active_examples
    _write_json(config.EXAMPLES_REGISTRY_PATH, registry)


def delete_example(file_name: str) -> None:
    file_path = os.path.join(config.EXAMPLES_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    registry = _read_json(config.EXAMPLES_REGISTRY_PATH, {"active_examples": []})
    registry["active_examples"] = [entry for entry in registry.get("active_examples", []) if entry != file_name]
    _write_json(config.EXAMPLES_REGISTRY_PATH, registry)
