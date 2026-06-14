import os
import json
import uuid
from datetime import datetime

import src.modules.configurations as configurations

_ACTIVE_SESSION_ID: str | None = None


def _sessions_dir() -> str:
    d = configurations.SESSIONS_DIR
    os.makedirs(d, exist_ok=True)
    return d


def _session_path(session_id: str) -> str:
    return os.path.join(_sessions_dir(), f"{session_id}.json")


def _write(session_id: str, data: dict) -> None:
    with open(
        _session_path(session_id), "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_session(name: str | None = None) -> dict:
    session_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    if not name:
        name = f"Session {datetime.now().strftime('%b %d %H:%M')}"
    data = {
        "id": session_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "workspace_files": [],
        "model_name": configurations.MODEL_NAME,
        "messages": [],
    }
    _write(session_id, data)
    return data


def list_sessions() -> list[dict]:
    d = _sessions_dir()
    sessions = []
    for fname in os.listdir(d):
        if not fname.endswith(".json"):
            continue
        session_data = load_session(fname.replace(".json", ""))
        if session_data:
            sessions.append(session_data)

    sessions.sort(
        key=lambda x: x.get("updated_at", ""), reverse=True
    )
    return sessions


def load_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

            if "target_path" in data:
                old_path = data.pop("target_path")
                data["workspace_files"] = [old_path] if old_path else []
                save_session(session_id, data)

            return data
    except Exception:
        return None


def save_session(session_id: str, data: dict) -> None:
    data["updated_at"] = datetime.now().isoformat()
    _write(session_id, data)


def delete_session(session_id: str) -> None:
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)


def rename_session(session_id: str, new_name: str) -> None:
    data = load_session(session_id)
    if data:
        data["name"] = new_name.strip() or data["name"]
        save_session(session_id, data)


def get_active_session_id() -> str | None:
    return _ACTIVE_SESSION_ID


def set_active_session_id(session_id: str | None) -> None:
    global _ACTIVE_SESSION_ID
    _ACTIVE_SESSION_ID = session_id


def get_active_session() -> dict | None:
    sid = _ACTIVE_SESSION_ID
    return load_session(sid) if sid else None


def update_active_session(
    messages: list | None = None,
    workspace_files: list | None = None,
    model_name: str | None = None,
) -> None:
    sid = _ACTIVE_SESSION_ID
    if not sid:
        return
    data = load_session(sid)
    if not data:
        return

    if messages is not None:
        data["messages"] = messages[-20:]
    if workspace_files is not None:
        data["workspace_files"] = workspace_files
    if model_name is not None:
        data["model_name"] = model_name

    save_session(sid, data)
