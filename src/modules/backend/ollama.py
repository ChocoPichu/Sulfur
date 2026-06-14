import json
import requests
from typing import Generator, Optional

from .base import BaseBackend
from .protocol_openai import OpenAIProtocol, LLMRequest, LLMEvent
import src.modules.configurations as cfg
from src.modules.configurations import dbg_print

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaBackend(BaseBackend):
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        use_native_api: bool = False,
    ):
        super().__init__(base_url)
        self.use_native_api = use_native_api
        self._protocol = OpenAIProtocol(base_url=self.base_url)
        self._num_ctx = getattr(cfg, "NUM_CTX", 4096)
        self._logged_ctx = False

    def start(self) -> bool:
        dbg_print(f"\n[OLLAMA] Connecting to {self.base_url}...")
        healthy = self.is_healthy()
        if healthy:
            models = self.list_models()
            dbg_print(
                f"[OLLAMA] Connected -- "
                f"{len(models)} model(s) available"
            )
            for m in models[:5]:
                dbg_print(f"[OLLAMA]   . {m}")
            if len(models) > 5:
                dbg_print(
                    f"[OLLAMA]   ... and {len(models) - 5} more"
                )
        else:
            dbg_print(
                f"[OLLAMA] Connection failed -- is Ollama running?"
            )
        return healthy

    def stop(self) -> None:
        pass

    def is_healthy(self) -> bool:
        try:
            resp = requests.get(
                f"{self.base_url}/api/tags", timeout=5
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
            num_ctx=self._num_ctx,
        )

    def _log_request(self, model_name):
        if not self._logged_ctx:
            dbg_print(
                f"[OLLAMA] Request -- Model: {model_name} | "
                f"Context: {self._num_ctx} | "
                f"Temperature: {getattr(cfg, 'TEMPERATURE', 0.7)}"
            )
            self._logged_ctx = True

    def chat_completion(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
    ) -> Optional[str]:
        self._log_request(model_name)
        dbg_print(
            f"[OLLAMA] chat_completion "
            f"(native={self.use_native_api}) -> {model_name}"
        )
        if self.use_native_api:
            return self._native_completion(
                messages, temperature, max_tokens, top_p, top_k,
                chat_template_kwargs, model_name,
            )
        request = self._build_request(
            messages, temperature, max_tokens, top_p, top_k,
            chat_template_kwargs, model_name,
        )
        dbg_print(
            f"[OLLAMA] Posting to "
            f"{self.base_url}/v1/chat/completions..."
        )
        return self._protocol.complete(request, timeout=120)

    def chat_completion_stream(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
        tools=None,
    ) -> Generator:
        self._log_request(model_name)
        dbg_print(
            f"[OLLAMA] chat_completion_stream "
            f"(native={self.use_native_api}) -> {model_name}"
        )
        if self.use_native_api:
            yield from self._native_stream(
                messages, temperature, max_tokens, top_p, top_k,
                chat_template_kwargs, model_name,
            )
        else:
            request = self._build_request(
                messages, temperature, max_tokens, top_p, top_k,
                chat_template_kwargs, model_name, tools,
            )
            dbg_print(
                f"[OLLAMA] Posting to "
                f"{self.base_url}/v1/chat/completions (stream)..."
            )
            yield from self._protocol.stream(request, timeout=120)

    def _native_build_payload(
        self,
        messages,
        temperature,
        max_tokens,
        chat_template_kwargs,
        model_name,
        stream,
    ):
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self._num_ctx,
            },
        }
        if chat_template_kwargs:
            payload.update(chat_template_kwargs)
        return payload

    def _native_completion(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
    ):
        payload = self._native_build_payload(
            messages, temperature, max_tokens,
            chat_template_kwargs, model_name, stream=False,
        )
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload, timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    def _native_stream(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
    ):
        payload = self._native_build_payload(
            messages, temperature, max_tokens,
            chat_template_kwargs, model_name, stream=True,
        )
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload, stream=True, timeout=120,
        )
        resp.raise_for_status()

        in_reasoning = False
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            data = json.loads(line_str)
            if data.get("done"):
                if "metrics" in data:
                    eval_count = data.get("eval_count", 0)
                    eval_duration = (
                        data.get("eval_duration", 1) / 1e9
                    )
                    tps = eval_count / max(eval_duration, 1)
                    yield LLMEvent(
                        kind="done",
                        timings={
                            "predicted_per_second": tps
                        },
                    )
                break
            msg = data.get("message", {})
            thinking = msg.get("thinking")
            if thinking is not None:
                if not in_reasoning:
                    in_reasoning = True
                    yield LLMEvent(
                        kind="content", content="<think>\n"
                    )
                yield LLMEvent(
                    kind="reasoning", content=thinking
                )
            content = msg.get("content")
            if content is not None:
                if in_reasoning:
                    in_reasoning = False
                    yield LLMEvent(
                        kind="content", content="\n</think>\n"
                    )
                yield LLMEvent(
                    kind="content", content=content
                )

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    m.get("name", "")
                    for m in data.get("models", [])
                ]
        except requests.exceptions.RequestException:
            pass
        return []
