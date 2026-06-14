import src.modules.memory as memory
import src.modules.target_path as target_path


def get_target() -> dict:
    try:
        return {'target': target_path.get_workspace_files()}
    except Exception as exc:
        return {'error': str(exc)}


def set_target(path: str | None) -> dict:
    if not path:
        target_path.clear_workspace_files()
        return {'success': True, 'target': None}

    ok = target_path.add_workspace_file(path)
    if ok:
        return {'success': True, 'target': path}
    return {'success': False, 'error': 'Invalid path or file not found'}
