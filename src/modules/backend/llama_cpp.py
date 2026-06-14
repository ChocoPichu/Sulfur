import os
import time
import subprocess
import traceback
import requests
from typing import Generator, Optional

from .base import BaseBackend
from .protocol_openai import OpenAIProtocol, LLMRequest, LLMEvent
import src.modules.configurations as cfg
from src.modules.configurations import dbg_print
from src.modules.profiles import get_profile


class LlamaCppBackend(BaseBackend):
    def __init__(
        self,
        executable_path: str,
        model_path: str,
        ctx_size: int,
        gpu_layers: int,
        flash_attention: bool,
        prompt_caching: bool,
        mlock: bool,
        threads: int,
        kv_cache_quant: str,
        cpu_moe_layers: int,
    ):
        super().__init__("http://127.0.0.1:8080")
        self.executable_path = executable_path
        self.model_path = model_path
        self.ctx_size = ctx_size
        self.gpu_layers = gpu_layers
        self.flash_attention = flash_attention
        self.prompt_caching = prompt_caching
        self.mlock = mlock
        self.threads = threads
        self.kv_cache_quant = kv_cache_quant
        self.cpu_moe_layers = cpu_moe_layers

        profile = get_profile(cfg.MODEL_TYPE)
        self._protocol = OpenAIProtocol(
            base_url=self.base_url,
            reasoning_field=profile.reasoning_field
            or "reasoning_content",
        )

        self._server_process = None
        self._current_model_path = None
        self._current_ctx = None
        self._current_gpu_layers = None
        self._current_cpu_moe = None
        self._current_fa = None
        self._current_pc = None
        self._current_mlock = None
        self._current_threads = None
        self._current_kv = None

    def _config_changed(self) -> bool:
        return (
            self._server_process is None
            or self._current_model_path != self.model_path
            or self._current_ctx != self.ctx_size
            or self._current_gpu_layers != self.gpu_layers
            or self._current_cpu_moe != self.cpu_moe_layers
            or self._current_fa != self.flash_attention
            or self._current_pc != self.prompt_caching
            or self._current_mlock != self.mlock
            or self._current_threads != self.threads
            or self._current_kv != self.kv_cache_quant
        )

    def _snapshot_config(self):
        self._current_model_path = self.model_path
        self._current_ctx = self.ctx_size
        self._current_gpu_layers = self.gpu_layers
        self._current_cpu_moe = self.cpu_moe_layers
        self._current_fa = self.flash_attention
        self._current_pc = self.prompt_caching
        self._current_mlock = self.mlock
        self._current_threads = self.threads
        self._current_kv = self.kv_cache_quant

    def start(self) -> bool:
        if not self._config_changed():
            dbg_print(
                "[LLAMA_CPP] start() -- "
                "config unchanged, no restart needed"
            )
            return True

        model_name = os.path.basename(self.model_path)
        print(
            f"\n[SYSTEM] Starting llama-server for "
            f"{model_name}..."
        )
        print(
            f"[SYSTEM] Context: {self.ctx_size} | "
            f"GPU Layers: {self.gpu_layers}"
        )

        if self._server_process:
            print("[SYSTEM] Stopping previous server instance...")
            self._server_process.terminate()
            self._server_process.wait()
        else:
            print(
                "[SYSTEM] Cleaning up orphaned "
                "server instances..."
            )
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "llama-server.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

        try:
            exe = self.executable_path
            if not os.path.exists(exe):
                exe = "llama-server"

            gpu_str = (
                str(self.gpu_layers)
                if self.gpu_layers >= 0
                else "99"
            )
            cmd = [
                exe,
                "-m",
                self.model_path,
                "-c",
                str(self.ctx_size),
                "-ngl",
                gpu_str,
                "--n-cpu-moe",
                str(self.cpu_moe_layers),
                "--no-mmap",
                "--no-warmup",
            ]

            if self.mlock:
                cmd.append("--mlock")

            cmd.extend(["--port", "8080", "--host", "127.0.0.1"])

            if self.flash_attention:
                cmd.extend(["-fa", "on"])

            if not self.prompt_caching:
                cmd.append("--no-cache-prompt")

            if self.threads > 0:
                cmd.extend(["-t", str(self.threads)])

            if (
                self.kv_cache_quant
                and self.kv_cache_quant.lower() != "f16"
            ):
                cmd.extend(
                    [
                        "-ctk",
                        self.kv_cache_quant,
                        "-ctv",
                        self.kv_cache_quant,
                    ]
                )

            print(f"[SYSTEM] Command: {' '.join(cmd)}")

            log_file = open(
                os.path.join(cfg.BASE_DIR, "llama_server.log"),
                "w",
                encoding="utf-8",
            )

            self._server_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            print("[SYSTEM] Waiting for server to start...")
            max_retries = 60
            for i in range(max_retries):
                try:
                    response = requests.get(
                        f"{self.base_url}/health", timeout=1
                    )
                    if response.status_code == 200:
                        try:
                            health_data = response.json()
                            if health_data.get("status") in [
                                "ok",
                                "ready",
                            ]:
                                print(
                                    "[SUCCESS] "
                                    "llama-server is ready!"
                                )
                                break
                        except Exception:
                            print(
                                "[SUCCESS] "
                                "llama-server is ready!"
                            )
                            break
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    if i == max_retries - 1:
                        raise Exception(
                            "Server failed to start "
                            "within 60 seconds"
                        )

            self._snapshot_config()
            return True

        except Exception as e:
            print(
                "\n[CRITICAL ERROR] "
                "Failed to start llama-server!"
            )
            print(f"Details: {e}")
            traceback.print_exc()
            return False

    def stop(self) -> None:
        if self._server_process:
            print("[SYSTEM] Shutting down llama-server...")
            self._server_process.terminate()
            self._server_process.wait()
            self._server_process = None

    def is_healthy(self) -> bool:
        try:
            resp = requests.get(
                f"{self.base_url}/health", timeout=2
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _build_request(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
        tools=None,
    ) -> LLMRequest:
        return LLMRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            chat_template_kwargs=chat_template_kwargs,
            model_name=model_name,
            tools=tools,
            num_ctx=0,
        )

    def chat_completion(
        self,
        messages,
        temperature: float,
        max_tokens: int,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name: str,
    ) -> Optional[str]:
        if not self.start():
            return None

        request = self._build_request(
            messages, temperature, max_tokens, top_p, top_k,
            chat_template_kwargs, model_name,
        )

        for attempt in range(5):
            try:
                return self._protocol.complete(
                    request, timeout=60
                )
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503:
                    print(
                        "[SYSTEM] Server returned 503. "
                        f"Retrying ({attempt + 1}/5)..."
                    )
                    time.sleep(2)
                    continue
                raise

        return None

    def chat_completion_stream(
        self,
        messages,
        temperature: float,
        max_tokens: int,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name: str,
        tools=None,
    ) -> Generator:
        if not self.start():
            dbg_print(
                "[LLAMA_CPP] chat_completion_stream -- "
                "start() returned False, aborting"
            )
            return

        request = self._build_request(
            messages, temperature, max_tokens, top_p, top_k,
            chat_template_kwargs, model_name, tools,
        )
        dbg_print(
            "[LLAMA_CPP] Streaming request -> "
            f"{self.base_url}/v1/chat/completions "
            f"(model={model_name})"
        )

        for attempt in range(10):
            try:
                for event in self._protocol.stream(
                    request, timeout=60
                ):
                    yield event
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503:
                    print(
                        "[SYSTEM] Server returned 503. "
                        f"Retrying ({attempt + 1}/10)..."
                    )
                    time.sleep(20)
                    continue
                raise

    def list_models(self) -> list[str]:
        return list(cfg.AVAILABLE_MODELS.keys())
