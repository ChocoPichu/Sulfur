import os
import src.modules.preferences_manager as prefs_mgr

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..")
)

SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
IDENTITY_FILE = os.path.join(BASE_DIR, "identity.md")

INSTRUCTIONS_DIR = os.path.join(BASE_DIR, "instructions")
TOOLS_LEGACY_FILE = os.path.join(
    INSTRUCTIONS_DIR, "tools_legacy.md"
)
TOOLS_JSON_FILE = os.path.join(
    INSTRUCTIONS_DIR, "tools_json.md"
)

CUSTOM_FONT_PATH = [
    "ui/custom_fonts/Delius/Delius-Regular.ttf",
    "ui/custom_fonts/Griffy/Griffy-Regular.ttf",
]

_env_debug = (
    os.environ.get("SULFUR_DEBUG", "0")
    .strip()
    .lower()
    in ("1", "true", "yes", "on")
)

AVAILABLE_MODELS: dict = {}
MODEL_NAME: str = "None"
CURRENT_TARGET_PATH = None

BACKEND_TYPE = "llama_cpp"
BACKEND_URL = "http://127.0.0.1:8080"
BACKEND_API_KEY = ""
CUSTOM_MODELS = {}

MODEL_TYPE = "qwen"
MODEL_FOLDER = ""

ACTIVE_WORKSPACE_FILES = []

TARGET_LANGUAGE = "Python"

SUPPORTED_LANGUAGES = {
    "Python": ".py",
    "JavaScript": ".js",
    "TypeScript": ".ts",
    "C++": ".cpp",
    "C": ".c",
    "HTML": ".html",
    "CSS": ".css",
    "JSON": ".json",
    "Markdown": ".md",
    "Text": ".txt",
}


def get_model_path():
    entry = AVAILABLE_MODELS.get(MODEL_NAME, {})
    if isinstance(entry, dict):
        return entry.get("path")
    return entry


def get_effective_model_id() -> str:
    entry = AVAILABLE_MODELS.get(MODEL_NAME, {})
    if isinstance(entry, dict) and "model_id" in entry:
        return entry["model_id"]
    if MODEL_NAME in CUSTOM_MODELS:
        return CUSTOM_MODELS[MODEL_NAME].get(
            "model_id", MODEL_NAME
        )
    return MODEL_NAME


def set_backend_type(backend_type: str):
    global BACKEND_TYPE
    BACKEND_TYPE = backend_type
    prefs_mgr.update_pref("BACKEND_TYPE", backend_type)


def set_backend_url(url: str):
    global BACKEND_URL
    BACKEND_URL = url
    prefs_mgr.update_pref("BACKEND_URL", url)


def set_backend_api_key(key: str):
    global BACKEND_API_KEY
    BACKEND_API_KEY = key
    prefs_mgr.update_pref("BACKEND_API_KEY", key)


def set_json_tools(enabled: bool):
    global JSON_TOOLS
    JSON_TOOLS = enabled
    prefs_mgr.update_pref("JSON_TOOLS", enabled)


def set_allow_read(enabled: bool):
    global ALLOW_READ
    ALLOW_READ = enabled
    prefs_mgr.update_pref("ALLOW_READ", enabled)


def set_allow_write(enabled: bool):
    global ALLOW_WRITE
    ALLOW_WRITE = enabled
    prefs_mgr.update_pref("ALLOW_WRITE", enabled)


def set_auto_apply_edits(enabled: bool):
    global AUTO_APPLY_EDITS
    AUTO_APPLY_EDITS = enabled
    prefs_mgr.update_pref("AUTO_APPLY_EDITS", enabled)


def set_debug(enabled: bool):
    global DEBUG
    DEBUG = enabled
    prefs_mgr.update_pref("DEBUG", enabled)


def dbg_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def set_model_type(model_type: str):
    global MODEL_TYPE
    MODEL_TYPE = model_type
    prefs_mgr.update_pref("MODEL_TYPE", model_type)


def set_model_folder(folder: str):
    global MODEL_FOLDER
    MODEL_FOLDER = folder
    prefs_mgr.update_pref("MODEL_FOLDER", folder)
    scan_gguf_folder()


def scan_gguf_folder():
    global AVAILABLE_MODELS
    AVAILABLE_MODELS = {}
    if MODEL_FOLDER and os.path.isdir(MODEL_FOLDER):
        for fname in os.listdir(MODEL_FOLDER):
            if fname.lower().endswith(".gguf"):
                display = os.path.splitext(fname)[0]
                AVAILABLE_MODELS[display] = {
                    "path": os.path.join(
                        MODEL_FOLDER, fname
                    ),
                }
    prefs_mgr.update_pref("MODEL_FOLDER", MODEL_FOLDER)


def discover_models_folder(folder: str):
    set_model_folder(folder)


def refresh_models_from_backend():
    global AVAILABLE_MODELS
    try:
        from src.modules.backend import (
            get_active_backend,
        )

        backend = get_active_backend()
        if backend and backend.is_healthy():
            models = backend.list_models()
            AVAILABLE_MODELS = {}
            for m in models:
                AVAILABLE_MODELS[m] = {"model_id": m}
            return True
    except Exception:
        pass
    return False


_PREFS = prefs_mgr.load_prefs()

FLASH_ATTENTION = _PREFS["FLASH_ATTENTION"]
PROMPT_CACHING = _PREFS["PROMPT_CACHING"]
MLOCK = _PREFS["MLOCK"]

NUM_CTX = _PREFS["NUM_CTX"]
MAX_TOKENS = _PREFS["MAX_TOKENS"]
TEMPERATURE = _PREFS["TEMPERATURE"]
NUM_THREAD = _PREFS["NUM_THREAD"]
CPU_MOE_LAYERS = _PREFS["CPU_MOE_LAYERS"]

GPU_LAYERS = _PREFS.get("GPU_LAYERS", -1)
KV_CACHE_QUANT = _PREFS.get("KV_CACHE_QUANT", "f16")

_legacy_allow_edits = _PREFS.get("ALLOW_FILE_EDITS")
if (
    _legacy_allow_edits is not None
    and "ALLOW_WRITE" not in _PREFS
):
    _PREFS["ALLOW_WRITE"] = _legacy_allow_edits
    prefs_mgr.save_prefs(_PREFS)

ALLOW_READ = _PREFS.get("ALLOW_READ", True)
ALLOW_WRITE = _PREFS.get("ALLOW_WRITE", True)
AUTO_APPLY_EDITS = _PREFS.get(
    "AUTO_APPLY_EDITS", False
)

BACKEND_TYPE = _PREFS.get(
    "BACKEND_TYPE", "llama_cpp"
)
BACKEND_URL = _PREFS.get(
    "BACKEND_URL", "http://127.0.0.1:8080"
)
BACKEND_API_KEY = _PREFS.get(
    "BACKEND_API_KEY", ""
)
CUSTOM_MODELS = _PREFS.get("CUSTOM_MODELS", {})
JSON_TOOLS = _PREFS.get("JSON_TOOLS", False)
DEBUG = _env_debug or _PREFS.get("DEBUG", False)

MODEL_TYPE = _PREFS.get("MODEL_TYPE", "qwen")
MODEL_FOLDER = _PREFS.get("MODEL_FOLDER", "")

if MODEL_FOLDER:
    scan_gguf_folder()

PALETTES = {
    "Sulfur": {
        "BG_BASE": "#14110f",
        "BG_SURFACE": "#1c1815",
        "BG_CARD": "#26211d",
        "BG_ACTIVE": "#332c27",
        "ACCENT": "#c49a78",
        "ACCENT_DARK": "#947051",
        "ACCENT_TINT": "#241e1a",
        "BORDER_REST": "#3d342e",
        "BORDER_ACTIVE": "#947051",
        "TEXT_PRIMARY": "#e6e0da",
        "TEXT_SECONDARY": "#b8aea5",
        "TEXT_MUTED": "#7a726b",
        "TAG_EDIT": "#bd9368",
        "TAG_REMOVE": "#b86363",
        "TAG_ADD": "#7da688",
        "SYSTEM_MSG": "#c49a78",
        "SCROLLBAR_BTN": "#3d342e",
        "SCROLLBAR_BTN_HOVER": "#947051",
        "SWATCH": "#c49a78",
    },
    "Daylight": {
        "BG_BASE": "#f4f5f6",
        "BG_SURFACE": "#eaecef",
        "BG_CARD": "#ffffff",
        "BG_ACTIVE": "#dfe2e6",
        "ACCENT": "#a07830",
        "ACCENT_DARK": "#7a5a20",
        "ACCENT_TINT": "#f5ebd6",
        "BORDER_REST": "#ced4da",
        "BORDER_ACTIVE": "#a07830",
        "TEXT_PRIMARY": "#2d3139",
        "TEXT_SECONDARY": "#5c6370",
        "TEXT_MUTED": "#969faf",
        "TAG_EDIT": "#a07830",
        "TAG_REMOVE": "#b85c5c",
        "TAG_ADD": "#5c945c",
        "SYSTEM_MSG": "#a07830",
        "SCROLLBAR_BTN": "#ced4da",
        "SCROLLBAR_BTN_HOVER": "#a07830",
        "SWATCH": "#a07830",
    },
    "Void": {
        "BG_BASE": "#121214",
        "BG_SURFACE": "#1a1a1c",
        "BG_CARD": "#222225",
        "BG_ACTIVE": "#2d2d30",
        "ACCENT": "#c5c5ca",
        "ACCENT_DARK": "#909095",
        "ACCENT_TINT": "#222225",
        "BORDER_REST": "#333338",
        "BORDER_ACTIVE": "#606066",
        "TEXT_PRIMARY": "#e6e6eb",
        "TEXT_SECONDARY": "#a0a0a5",
        "TEXT_MUTED": "#606066",
        "TAG_EDIT": "#b59555",
        "TAG_REMOVE": "#b56565",
        "TAG_ADD": "#75a075",
        "SYSTEM_MSG": "#85858a",
        "SCROLLBAR_BTN": "#333338",
        "SCROLLBAR_BTN_HOVER": "#606066",
        "SWATCH": "#c5c5ca",
    },
    "Aqua": {
        "BG_BASE": "#14191f",
        "BG_SURFACE": "#1b222b",
        "BG_CARD": "#222a36",
        "BG_ACTIVE": "#2d3745",
        "ACCENT": "#5fa9b1",
        "ACCENT_DARK": "#437b82",
        "ACCENT_TINT": "#1b252b",
        "BORDER_REST": "#384454",
        "BORDER_ACTIVE": "#5fa9b1",
        "TEXT_PRIMARY": "#e2e8f0",
        "TEXT_SECONDARY": "#94a3b8",
        "TEXT_MUTED": "#64748b",
        "TAG_EDIT": "#bfa063",
        "TAG_REMOVE": "#bf6b6b",
        "TAG_ADD": "#6bbf84",
        "SYSTEM_MSG": "#63a0bf",
        "SCROLLBAR_BTN": "#384454",
        "SCROLLBAR_BTN_HOVER": "#5fa9b1",
        "SWATCH": "#5fa9b1",
    },
    "Cherry": {
        "BG_BASE": "#191416",
        "BG_SURFACE": "#221b1e",
        "BG_CARD": "#2b2226",
        "BG_ACTIVE": "#382d32",
        "ACCENT": "#b8788a",
        "ACCENT_DARK": "#8c5866",
        "ACCENT_TINT": "#261b1f",
        "BORDER_REST": "#42353b",
        "BORDER_ACTIVE": "#b8788a",
        "TEXT_PRIMARY": "#e6dee1",
        "TEXT_SECONDARY": "#b8a6ab",
        "TEXT_MUTED": "#807074",
        "TAG_EDIT": "#b89063",
        "TAG_REMOVE": "#b86363",
        "TAG_ADD": "#73b885",
        "SYSTEM_MSG": "#b87898",
        "SCROLLBAR_BTN": "#42353b",
        "SCROLLBAR_BTN_HOVER": "#b8788a",
        "SWATCH": "#b8788a",
    },
    "Forest": {
        "BG_BASE": "#141715",
        "BG_SURFACE": "#1b201d",
        "BG_CARD": "#232a26",
        "BG_ACTIVE": "#2f3833",
        "ACCENT": "#729c7a",
        "ACCENT_DARK": "#537359",
        "ACCENT_TINT": "#1b211d",
        "BORDER_REST": "#38423c",
        "BORDER_ACTIVE": "#729c7a",
        "TEXT_PRIMARY": "#e1e6e3",
        "TEXT_SECONDARY": "#aab3ae",
        "TEXT_MUTED": "#737d78",
        "TAG_EDIT": "#b39862",
        "TAG_REMOVE": "#b36262",
        "TAG_ADD": "#729c7a",
        "SYSTEM_MSG": "#85ab8c",
        "SCROLLBAR_BTN": "#38423c",
        "SCROLLBAR_BTN_HOVER": "#729c7a",
        "SWATCH": "#729c7a",
    },
    "Fire": {
        "BG_BASE": "#1a1414",
        "BG_SURFACE": "#241b1b",
        "BG_CARD": "#2e2222",
        "BG_ACTIVE": "#3d2d2d",
        "ACCENT": "#b56b6b",
        "ACCENT_DARK": "#8a4f4f",
        "ACCENT_TINT": "#291a1a",
        "BORDER_REST": "#473636",
        "BORDER_ACTIVE": "#b56b6b",
        "TEXT_PRIMARY": "#e8e1e1",
        "TEXT_SECONDARY": "#b8a6a6",
        "TEXT_MUTED": "#827171",
        "TAG_EDIT": "#b59065",
        "TAG_REMOVE": "#b56b6b",
        "TAG_ADD": "#6eb57d",
        "SYSTEM_MSG": "#b56b6b",
        "SCROLLBAR_BTN": "#473636",
        "SCROLLBAR_BTN_HOVER": "#b56b6b",
        "SWATCH": "#b56b6b",
    },
    "Nebula": {
        "BG_BASE": "#16141c",
        "BG_SURFACE": "#1e1b26",
        "BG_CARD": "#272333",
        "BG_ACTIVE": "#342f45",
        "ACCENT": "#8e82b3",
        "ACCENT_DARK": "#696087",
        "ACCENT_TINT": "#211d2b",
        "BORDER_REST": "#3e384f",
        "BORDER_ACTIVE": "#8e82b3",
        "TEXT_PRIMARY": "#e3e1e8",
        "TEXT_SECONDARY": "#b2adb8",
        "TEXT_MUTED": "#7b7782",
        "TAG_EDIT": "#a283b3",
        "TAG_REMOVE": "#b38399",
        "TAG_ADD": "#7cb39b",
        "SYSTEM_MSG": "#9b8fbf",
        "SCROLLBAR_BTN": "#3e384f",
        "SCROLLBAR_BTN_HOVER": "#8e82b3",
        "SWATCH": "#8e82b3",
    },
    "Slate": {
        "BG_BASE": "#181b20",
        "BG_SURFACE": "#20242b",
        "BG_CARD": "#292e37",
        "BG_ACTIVE": "#373e4a",
        "ACCENT": "#7091af",
        "ACCENT_DARK": "#536c82",
        "ACCENT_TINT": "#1d2229",
        "BORDER_REST": "#414957",
        "BORDER_ACTIVE": "#7091af",
        "TEXT_PRIMARY": "#e2e5e8",
        "TEXT_SECONDARY": "#a3acb5",
        "TEXT_MUTED": "#737b85",
        "TAG_EDIT": "#b59e6c",
        "TAG_REMOVE": "#b57070",
        "TAG_ADD": "#70b592",
        "SYSTEM_MSG": "#809eb8",
        "SCROLLBAR_BTN": "#414957",
        "SCROLLBAR_BTN_HOVER": "#7091af",
        "SWATCH": "#7091af",
    },
    "Amber": {
        "BG_BASE": "#1a1612",
        "BG_SURFACE": "#241e19",
        "BG_CARD": "#2e2720",
        "BG_ACTIVE": "#3d332b",
        "ACCENT": "#b88a68",
        "ACCENT_DARK": "#8c674e",
        "ACCENT_TINT": "#261f1a",
        "BORDER_REST": "#473c33",
        "BORDER_ACTIVE": "#b88a68",
        "TEXT_PRIMARY": "#e8e3df",
        "TEXT_SECONDARY": "#b8ad9e",
        "TEXT_MUTED": "#82796e",
        "TAG_EDIT": "#b8935c",
        "TAG_REMOVE": "#b86363",
        "TAG_ADD": "#77b886",
        "SYSTEM_MSG": "#b88e63",
        "SCROLLBAR_BTN": "#473633",
        "SCROLLBAR_BTN_HOVER": "#b88a68",
        "SWATCH": "#b88a68",
    },
    "Emerald": {
        "BG_BASE": "#131816",
        "BG_SURFACE": "#1a211e",
        "BG_CARD": "#222b27",
        "BG_ACTIVE": "#2d3a35",
        "ACCENT": "#669985",
        "ACCENT_DARK": "#4b7363",
        "ACCENT_TINT": "#1a2420",
        "BORDER_REST": "#36453f",
        "BORDER_ACTIVE": "#669985",
        "TEXT_PRIMARY": "#e1e6e4",
        "TEXT_SECONDARY": "#aab5b0",
        "TEXT_MUTED": "#737f7a",
        "TAG_EDIT": "#b5a469",
        "TAG_REMOVE": "#b56969",
        "TAG_ADD": "#669985",
        "SYSTEM_MSG": "#70a68d",
        "SCROLLBAR_BTN": "#36453f",
        "SCROLLBAR_BTN_HOVER": "#669985",
        "SWATCH": "#669985",
    },
    "Azure": {
        "BG_BASE": "#141820",
        "BG_SURFACE": "#1b202b",
        "BG_CARD": "#232a38",
        "BG_ACTIVE": "#2f384a",
        "ACCENT": "#6b8cb0",
        "ACCENT_DARK": "#4e6882",
        "ACCENT_TINT": "#1b202b",
        "BORDER_REST": "#384357",
        "BORDER_ACTIVE": "#6b8cb0",
        "TEXT_PRIMARY": "#e1e4e8",
        "TEXT_SECONDARY": "#aaaeb5",
        "TEXT_MUTED": "#737780",
        "TAG_EDIT": "#b09564",
        "TAG_REMOVE": "#b06464",
        "TAG_ADD": "#6cb082",
        "SYSTEM_MSG": "#829cb0",
        "SCROLLBAR_BTN": "#384357",
        "SCROLLBAR_BTN_HOVER": "#6b8cb0",
        "SWATCH": "#6b8cb0",
    },
}


def _load_palette(name: str) -> dict:
    return PALETTES.get(name, PALETTES["Sulfur"])


_ACTIVE_PALETTE_NAME = _PREFS.get("PALETTE", "Sulfur")
_P = _load_palette(_ACTIVE_PALETTE_NAME)

BG_BASE = _P["BG_BASE"]
BG_SURFACE = _P["BG_SURFACE"]
BG_CARD = _P["BG_CARD"]
BG_ACTIVE = _P["BG_ACTIVE"]

ACCENT = _P["ACCENT"]
ACCENT_DARK = _P["ACCENT_DARK"]
ACCENT_TINT = _P["ACCENT_TINT"]
BORDER_REST = _P["BORDER_REST"]
BORDER_ACTIVE = _P["BORDER_ACTIVE"]

TEXT_PRIMARY = _P["TEXT_PRIMARY"]
TEXT_SECONDARY = _P["TEXT_SECONDARY"]
TEXT_MUTED = _P["TEXT_MUTED"]

TAG_EDIT = _P["TAG_EDIT"]
TAG_REMOVE = _P["TAG_REMOVE"]
TAG_ADD = _P["TAG_ADD"]

SYSTEM_MSG = _P["SYSTEM_MSG"]

SCROLLBAR_BTN = _P["SCROLLBAR_BTN"]
SCROLLBAR_BTN_HOVER = _P["SCROLLBAR_BTN_HOVER"]

FONT_STARTING_TITLE = ("Delius", 60)
FONT_MAIN = ("Delius", 13)
FONT_TITLE = ("Delius", 18)
FONT_SUBTITLE = ("Delius", 11)
FONT_SMALL = ("Delius", 11)
FONT_CODE = ("Delius", 12)
FONT_MONO = ("Delius", 11)

RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12

PAD_XS = 2
PAD_SM = 6
PAD_MD = 10
PAD_LG = 18

THINKING_TRUE = (
    "Before answering, you MUST think about "
    "the user's request step by step. Enclose "
    "your thinking process within <think> and "
    "</think> tags. Try to not enter thinking "
    "loops."
)


def set_model_name(name: str):
    global MODEL_NAME
    MODEL_NAME = name
