import json
import requests
from typing import Generator, Optional, Union
from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    messages: list
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    chat_template_kwargs: Optional[dict] = None
    model_name: str = ""
    tools: Optional[list] = None
    tool_choice: Optional[str] = None
    num_ctx: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class LLMEvent:
    kind: str
    content: Optional[str] = None
    tool_call: Optional[dict] = None
    timings: Optional[dict] = None

    DONE = None


LLMEvent.DONE = LLMEvent(kind="done")


@dataclass
class OpenAIProtocol:
    """Shared OpenAI-compatible /v1/chat/completions protocol.

    Handles:
      - Building request payloads from LLMRequest
      - Parsing SSE streams into LLMEvent generators
      - Extracting responses from non-streaming calls
      - Wrapping reasoning_content with thinking tags
    """

    base_url: str
    api_key: str = ""
    with_thinking: bool = True
    reasoning_field: str = "reasoning_content"

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def build_payload(self, request: LLMRequest, stream: bool) -> dict:
        payload: dict = {
            "model": request.model_name,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }
        if request.num_ctx > 0:
            payload["num_ctx"] = request.num_ctx
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.top_k is not None:
            payload["top_k"] = request.top_k
        if request.chat_template_kwargs:
            payload["chat_template_kwargs"] = request.chat_template_kwargs
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        return payload

    def _post_stream(
        self, payload: dict, timeout: int
    ) -> requests.Response:
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers=self._headers(),
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp

    def _post(self, payload: dict, timeout: int) -> dict:
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def stream(
        self, request: LLMRequest, timeout: int = 120
    ) -> Generator[LLMEvent, None, None]:
        payload = self.build_payload(request, stream=True)
        resp = self._post_stream(payload, timeout)

        in_reasoning = False
        pending_tool_calls: dict[int, dict] = {}

        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str == "[DONE]":
                    break
                data = json.loads(data_str)

                if "choices" in data and len(data["choices"]) > 0:
                    delta = data["choices"][0].get("delta", {})

                    reasoning = delta.get(self.reasoning_field)
                    if reasoning is not None:
                        if self.with_thinking and not in_reasoning:
                            in_reasoning = True
                            yield LLMEvent(
                                kind="content", content="<think>\n"
                            )
                        yield LLMEvent(
                            kind="reasoning", content=reasoning
                        )

                    content = delta.get("content")
                    if content is not None:
                        if self.with_thinking and in_reasoning:
                            in_reasoning = False
                            yield LLMEvent(
                                kind="content", content="\n</think>\n"
                            )
                        yield LLMEvent(
                            kind="content", content=content
                        )

                    tool_calls_delta = delta.get("tool_calls")
                    if tool_calls_delta:
                        for tc in tool_calls_delta:
                            idx = tc.get("index", 0)
                            if idx not in pending_tool_calls:
                                pending_tool_calls[idx] = {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": "", "arguments": ""
                                    },
                                }
                            acc = pending_tool_calls[idx]
                            if "id" in tc and tc["id"]:
                                acc["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if "name" in fn and fn["name"]:
                                acc["function"]["name"] = fn["name"]
                            if "arguments" in fn:
                                acc["function"]["arguments"] += (
                                    fn["arguments"]
                                )

                    finish_reason = data["choices"][0].get(
                        "finish_reason", ""
                    )
                    if finish_reason == "tool_calls":
                        for idx in sorted(pending_tool_calls):
                            yield LLMEvent(
                                kind="tool_call",
                                tool_call=pending_tool_calls[idx],
                            )
                        pending_tool_calls.clear()

                if "timings" in data:
                    yield LLMEvent(
                        kind="done", timings=data["timings"]
                    )

    def complete(
        self, request: LLMRequest, timeout: int = 120
    ) -> str:
        payload = self.build_payload(request, stream=False)
        data = self._post(payload, timeout)
        return data["choices"][0]["message"]["content"]

    def check_health(self, timeout: int = 5) -> bool:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=self._headers(),
                timeout=timeout,
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self, timeout: int = 5) -> list[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=self._headers(),
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    m.get("id", "") for m in data.get("data", [])
                ]
        except requests.exceptions.RequestException:
            pass
        return []
