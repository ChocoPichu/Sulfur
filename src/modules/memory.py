import json
import os

import src.modules.configurations as configurations
import src.modules.session_manager as session_manager
import src.modules.target_path as target_path


def load_memory() -> list:
    session = session_manager.get_active_session()
    if session is not None:
        return session.get("messages", [])

    if os.path.exists(configurations.MEMORY_FILE):
        try:
            with open(configurations.MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("messages", [])
        except Exception:
            pass
    return []


def save_memory(
    history: list, workspace_files: list | None = None
) -> None:
    sid = session_manager.get_active_session_id()

    if workspace_files is None:
        workspace_files = target_path.get_workspace_files()

    if sid:
        session_manager.update_active_session(
            messages=history,
            workspace_files=workspace_files,
            model_name=configurations.MODEL_NAME,
        )
        return

    try:
        existing_files = []
        if os.path.exists(configurations.MEMORY_FILE):
            try:
                with open(
                    configurations.MEMORY_FILE, "r", encoding="utf-8"
                ) as f:
                    existing = json.load(f)
                    if isinstance(existing, dict):
                        if "workspace_files" in existing:
                            existing_files = existing["workspace_files"]
                        elif (
                            "target_path" in existing
                            and existing["target_path"]
                        ):
                            existing_files = [existing["target_path"]]
            except Exception:
                pass

        data = {
            "messages": history[-20:],
            "workspace_files": (
                workspace_files if workspace_files else existing_files
            ),
            "model_name": configurations.MODEL_NAME,
        }
        with open(
            configurations.MEMORY_FILE, "w", encoding="utf-8"
        ) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
