import os
import sys
import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )


@dataclass
class ProviderConfig:
    backend_type: str = "llama_cpp"
    backend_url: str = "http://127.0.0.1:8080"
    backend_api_key: str = ""
    custom_models: dict = field(default_factory=dict)


@dataclass
class ModelConfig:
    model_type: str = "qwen"
    model_name: str = "None"
    model_folder: str = ""
    available_models: dict = field(default_factory=dict)


@dataclass
class InferenceConfig:
    num_ctx: int = 16000
    max_tokens: int = 8192
    temperature: float = 0.6
    num_thread: int = 8
    flash_attention: bool = True
    prompt_caching: bool = True
    mlock: bool = False
    gpu_layers: int = -1
    kv_cache_quant: str = "f16"
    cpu_moe_layers: int = 0
    allow_file_edits: bool = True


@dataclass
class UIConfig:
    palette: str = "Amber Night"
    theme: int = 1


@dataclass
class AppConfig:
    provider: ProviderConfig = field(
        default_factory=ProviderConfig
    )
    model: ModelConfig = field(default_factory=ModelConfig)
    inference: InferenceConfig = field(
        default_factory=InferenceConfig
    )
    ui: UIConfig = field(default_factory=UIConfig)

    _prefs_path: str = field(default="")

    def __post_init__(self):
        if not self._prefs_path:
            self._prefs_path = os.path.join(
                BASE_DIR, "preferences.json"
            )

    @classmethod
    def load(cls) -> "AppConfig":
        config = cls()
        prefs = cls._read_prefs(config._prefs_path)

        config.inference.num_ctx = prefs.get(
            "NUM_CTX", 16000
        )
        config.inference.max_tokens = prefs.get(
            "MAX_TOKENS", 8192
        )
        config.inference.temperature = prefs.get(
            "TEMPERATURE", 0.6
        )
        config.inference.num_thread = prefs.get(
            "NUM_THREAD", 8
        )
        config.inference.flash_attention = prefs.get(
            "FLASH_ATTENTION", True
        )
        config.inference.prompt_caching = prefs.get(
            "PROMPT_CACHING", True
        )
        config.inference.mlock = prefs.get("MLOCK", False)
        config.inference.gpu_layers = prefs.get(
            "GPU_LAYERS", -1
        )
        config.inference.kv_cache_quant = prefs.get(
            "KV_CACHE_QUANT", "f16"
        )
        config.inference.cpu_moe_layers = prefs.get(
            "CPU_MOE_LAYERS", 0
        )
        config.inference.allow_file_edits = prefs.get(
            "ALLOW_FILE_EDITS", True
        )

        config.provider.backend_type = prefs.get(
            "BACKEND_TYPE", "llama_cpp"
        )
        config.provider.backend_url = prefs.get(
            "BACKEND_URL",
            "http://127.0.0.1:8080",
        )
        config.provider.backend_api_key = prefs.get(
            "BACKEND_API_KEY", ""
        )
        config.provider.custom_models = prefs.get(
            "CUSTOM_MODELS", {}
        )

        config.model.model_type = prefs.get(
            "MODEL_TYPE", "qwen"
        )
        config.model.model_folder = prefs.get(
            "MODEL_FOLDER", ""
        )
        if config.model.model_folder:
            config._scan_gguf_folder()

        config.ui.palette = prefs.get(
            "PALETTE", "Amber Night"
        )
        config.ui.theme = prefs.get("THEME", 1)

        return config

    def save(self):
        prefs = self._read_prefs(self._prefs_path)
        prefs["NUM_CTX"] = self.inference.num_ctx
        prefs["MAX_TOKENS"] = self.inference.max_tokens
        prefs["TEMPERATURE"] = self.inference.temperature
        prefs["NUM_THREAD"] = self.inference.num_thread
        prefs["FLASH_ATTENTION"] = (
            self.inference.flash_attention
        )
        prefs["PROMPT_CACHING"] = (
            self.inference.prompt_caching
        )
        prefs["MLOCK"] = self.inference.mlock
        prefs["GPU_LAYERS"] = self.inference.gpu_layers
        prefs["KV_CACHE_QUANT"] = (
            self.inference.kv_cache_quant
        )
        prefs["CPU_MOE_LAYERS"] = (
            self.inference.cpu_moe_layers
        )
        prefs["ALLOW_FILE_EDITS"] = (
            self.inference.allow_file_edits
        )
        prefs["BACKEND_TYPE"] = self.provider.backend_type
        prefs["BACKEND_URL"] = self.provider.backend_url
        prefs["BACKEND_API_KEY"] = (
            self.provider.backend_api_key
        )
        prefs["CUSTOM_MODELS"] = self.provider.custom_models
        prefs["MODEL_TYPE"] = self.model.model_type
        prefs["MODEL_FOLDER"] = self.model.model_folder
        prefs["PALETTE"] = self.ui.palette
        prefs["THEME"] = self.ui.theme
        self._write_prefs(self._prefs_path, prefs)

    def update_pref(self, key: str, value):
        mapping = {
            "NUM_CTX": ("inference", "num_ctx"),
            "MAX_TOKENS": ("inference", "max_tokens"),
            "TEMPERATURE": ("inference", "temperature"),
            "NUM_THREAD": ("inference", "num_thread"),
            "FLASH_ATTENTION": (
                "inference",
                "flash_attention",
            ),
            "PROMPT_CACHING": (
                "inference",
                "prompt_caching",
            ),
            "MLOCK": ("inference", "mlock"),
            "GPU_LAYERS": ("inference", "gpu_layers"),
            "KV_CACHE_QUANT": (
                "inference",
                "kv_cache_quant",
            ),
            "CPU_MOE_LAYERS": (
                "inference",
                "cpu_moe_layers",
            ),
            "ALLOW_FILE_EDITS": (
                "inference",
                "allow_file_edits",
            ),
            "BACKEND_TYPE": ("provider", "backend_type"),
            "BACKEND_URL": ("provider", "backend_url"),
            "BACKEND_API_KEY": (
                "provider",
                "backend_api_key",
            ),
            "CUSTOM_MODELS": ("provider", "custom_models"),
            "MODEL_TYPE": ("model", "model_type"),
            "MODEL_FOLDER": ("model", "model_folder"),
            "PALETTE": ("ui", "palette"),
            "THEME": ("ui", "theme"),
        }
        if key in mapping:
            section, attr = mapping[key]
            setattr(getattr(self, section), attr, value)
        self.save()

    def get_effective_model_id(self) -> str:
        entry = self.model.available_models.get(
            self.model.model_name, {}
        )
        if isinstance(entry, dict) and "model_id" in entry:
            return entry["model_id"]
        if (
            self.model.model_name
            in self.provider.custom_models
        ):
            return self.provider.custom_models[
                self.model.model_name
            ].get(
                "model_id", self.model.model_name
            )
        return self.model.model_name

    def _scan_gguf_folder(self):
        folder = self.model.model_folder
        if folder and os.path.isdir(folder):
            self.model.available_models = {}
            for fname in os.listdir(folder):
                if fname.lower().endswith(".gguf"):
                    display = os.path.splitext(fname)[0]
                    self.model.available_models[display] = {
                        "path": os.path.join(folder, fname)
                    }

    @staticmethod
    def _read_prefs(path: str) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _write_prefs(path: str, prefs: dict):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prefs, f, indent=4)
        except Exception as e:
            print(
                "[CONFIG] Error saving "
                f"preferences: {e}"
            )


_app_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.load()
    return _app_config


def reset_config():
    global _app_config
    _app_config = None
