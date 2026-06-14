import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
PREFS_FILE = os.path.join(BASE_DIR, "preferences.json")

DEFAULT_PREFS = {
    "NUM_CTX": 16000,
    "MAX_TOKENS": 8192,
    "TEMPERATURE": 0.6,
    "NUM_THREAD": 8,
    "FLASH_ATTENTION": True,
    "PROMPT_CACHING": True,
    "MLOCK": False,
    "GPU_LAYERS": -1,
    "KV_CACHE_QUANT": "f16",
    "CPU_MOE_LAYERS": 0,
    "ALLOW_FILE_EDITS": True,
    "ALLOW_READ": True,
    "ALLOW_WRITE": True,
    "AUTO_APPLY_EDITS": False,
    "JSON_TOOLS": False,
    "BACKEND_TYPE": "llama_cpp",
    "BACKEND_URL": "http://127.0.0.1:8080",
    "BACKEND_API_KEY": "",
    "CUSTOM_MODELS": {},
    "provider": {
        "llama_cpp": {
            "url": "http://127.0.0.1:8080",
            "enabled": True,
        },
        "lm_studio": {
            "url": "http://127.0.0.1:1234",
            "enabled": True,
        },
        "ollama": {
            "url": "http://127.0.0.1:11434",
            "enabled": True,
        },
    },
    "MODEL_TYPE": "qwen",
    "MODEL_FOLDER": "",
    "PALETTE": "Amber Night",
    "THEME": 1,
    "DEBUG": False,
}


def load_prefs() -> dict:
    if not os.path.exists(PREFS_FILE):
        save_prefs(DEFAULT_PREFS)
        return DEFAULT_PREFS.copy()

    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged_prefs = DEFAULT_PREFS.copy()
            _deep_merge(merged_prefs, data)
            return merged_prefs
    except Exception as e:
        print(f"[PREFS] Error reading preferences: {e}")
        return DEFAULT_PREFS.copy()


def save_prefs(prefs_dict: dict) -> None:
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs_dict, f, indent=4)
    except Exception as e:
        print(f"[PREFS] Error writing preferences: {e}")


def update_pref(key: str, value) -> None:
    prefs = load_prefs()
    prefs[key] = value
    save_prefs(prefs)


def get_provider_url(provider_key: str) -> str:
    prefs = load_prefs()
    provider = prefs.get("provider", {}).get(provider_key, {})
    return provider.get("url", prefs.get("BACKEND_URL", ""))


def _deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
