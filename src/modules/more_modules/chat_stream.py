from typing import Generator
import time
import os
import logging
import json

import src.modules.configurations as cfg
import src.modules.memory as memory
from src.modules.sandbox_file_operations import (
    read_sandbox,
    load_identity,
)
import src.modules.target_path as target_path
from src.modules.model_inference import chat_completion_stream
from src.modules.profiles import get_profile
import src.modules.document_parser as document_parser
from src.modules.backend.protocol_openai import LLMEvent
from src.modules.backend.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger("sulfur.chat_stream")
MAX_TOOL_ROUNDS = 5


def _load_tools_instruction() -> str:
    path = (
        cfg.TOOLS_JSON_FILE
        if getattr(cfg, "JSON_TOOLS", False)
        else cfg.TOOLS_LEGACY_FILE
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _build_system_prompt(
    attached_files, allow_read, allow_write, think_mode, vision_images
):
    identity_context = load_identity()
    tools_instruction = _load_tools_instruction()
    context_wrapper = (
        f"{identity_context}\n\n{tools_instruction}\n\n"
    )

    if attached_files:
        if getattr(cfg, "DEBUG", False):
            logger.debug("processing attached files")

        if allow_read:
            all_files_content = ""
            for file_path in attached_files:
                if getattr(cfg, "DEBUG", False):
                    logger.debug(
                        "processing file: %s", file_path
                    )
                ext = os.path.splitext(file_path)[1].lower()

                if ext in cfg.SUPPORTED_LANGUAGES.values():
                    file_data = read_sandbox(file_path)
                    all_files_content += (
                        f'\n<file path="{file_path}">\n'
                        f"{file_data}\n</file>\n"
                    )
                else:
                    parsed_data = (
                        document_parser.process_file_for_ai(
                            file_path
                        )
                    )
                    if parsed_data["type"] == "text":
                        file_data = parsed_data["content"]
                        all_files_content += (
                            f'\n<file path="{file_path}">\n'
                            f"{file_data}\n</file>\n"
                        )
                    elif parsed_data["type"] == "image":
                        vision_images.append(parsed_data)
                    elif parsed_data["type"] == "error":
                        error_msg = parsed_data.get(
                            "content", "Unknown error"
                        )
                        all_files_content += (
                            f'\n<file path="{file_path}">\n'
                            f"[ERROR]: {error_msg}\n</file>\n"
                        )

            if all_files_content:
                context_wrapper += (
                    "ATTACHED DOCUMENTS/FILES:\n"
                    f"{all_files_content}\n\n"
                )
        else:
            file_names = "\n".join(
                f"  - {os.path.basename(f)}"
                for f in attached_files
            )
            context_wrapper += (
                "Workspace contains the following files "
                f"(contents hidden):\n{file_names}\n\n"
            )

        if allow_write:
            if getattr(cfg, "DEBUG", False):
                logger.debug(
                    "allow_write=ON; "
                    "adding editing instructions"
                )
            context_wrapper += (
                "CRITICAL EDITING INSTRUCTIONS:\n"
                "To ensure proper file editing, "
                "please read your identity.md file, "
                "and FOLLOW it!\n\n"
            )
        else:
            if getattr(cfg, "DEBUG", False):
                logger.debug("allow_write=OFF")
            context_wrapper += (
                "You are currently in read-only mode. "
                "Do not attempt to write code edits "
                "back to files.\n\n"
            )
    else:
        if getattr(cfg, "DEBUG", False):
            logger.debug(
                "no files attached; conversational mode"
            )
        context_wrapper += (
            "You are Sulfur, a highly intelligent "
            "conversational AI assistant. Provide clear, "
            "helpful, and concise answers.\n\n"
        )

    if think_mode:
        context_wrapper += cfg.THINKING_TRUE

    return context_wrapper


def _stream_llm_events(
    messages,
    temperature,
    max_tokens,
    top_p,
    top_k,
    chat_template_kwargs,
    tools=None,
):
    stream = chat_completion_stream(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
        chat_template_kwargs=chat_template_kwargs,
        tools=tools,
    )
    for event in stream:
        if isinstance(event, LLMEvent):
            yield event
        elif isinstance(event, dict) and "timings" in event:
            yield LLMEvent(
                kind="done", timings=event["timings"]
            )
        elif isinstance(event, str):
            yield LLMEvent(kind="content", content=event)


def _process_stream(
    event_source,
    profile,
    think_mode: bool,
    OPEN_TAG,
    CLOSE_TAG,
) -> Generator[dict, None, tuple]:
    full_response = ""
    tps = 0.0
    state = "before_think"
    pending = ""
    start_ts = time.time()
    tokens_generated = 0
    server_tps = None
    tool_calls = []

    for event in event_source:
        if event.kind == "tool_call" and event.tool_call:
            tool_calls.append(event.tool_call)
            continue

        if event.kind == "done" and event.timings:
            server_tps = event.timings.get(
                "predicted_per_second"
            )
            continue

        if event.kind == "done":
            continue

        content = event.content or ""
        if content:
            tokens_generated += 1
            full_response += content
            pending += content

            while True:
                if OPEN_TAG is None:
                    if pending:
                        yield {
                            "type": "answer",
                            "content": pending,
                        }
                        pending = ""
                    break

                if state == "before_think":
                    idx = pending.find(OPEN_TAG)
                    if idx == -1:
                        safe = max(
                            0,
                            len(pending)
                            - len(OPEN_TAG)
                            + 1,
                        )
                        if safe > 0:
                            yield {
                                "type": "answer",
                                "content": pending[:safe],
                            }
                            pending = pending[safe:]
                        break
                    else:
                        if idx > 0:
                            yield {
                                "type": "answer",
                                "content": pending[:idx],
                            }
                        if not think_mode:
                            yield {
                                "type": "answer",
                                "content": OPEN_TAG,
                            }
                        pending = pending[
                            idx + len(OPEN_TAG):
                        ]
                        state = "in_think"

                elif state == "in_think":
                    idx = pending.find(CLOSE_TAG)
                    if idx == -1:
                        safe = max(
                            0,
                            len(pending)
                            - len(CLOSE_TAG)
                            + 1,
                        )
                        if safe > 0:
                            yield {
                                "type": (
                                    "think"
                                    if think_mode
                                    else "answer"
                                ),
                                "content": pending[:safe],
                            }
                            pending = pending[safe:]
                        break
                    else:
                        if idx > 0:
                            yield {
                                "type": (
                                    "think"
                                    if think_mode
                                    else "answer"
                                ),
                                "content": pending[:idx],
                            }
                        if not think_mode:
                            yield {
                                "type": "answer",
                                "content": CLOSE_TAG,
                            }
                        pending = pending[
                            idx + len(CLOSE_TAG):
                        ]
                        state = "in_answer"

                elif state == "in_answer":
                    if pending:
                        yield {
                            "type": "answer",
                            "content": pending,
                        }
                        pending = ""
                    break

    if server_tps is not None:
        tps = server_tps
    else:
        duration = time.time() - start_ts
        tps = (
            tokens_generated / duration
            if duration > 0
            else 0
        )

    if pending:
        etype = "think" if state == "in_think" else "answer"
        yield {"type": etype, "content": pending}

    return full_response, tps, tool_calls


def chat_stream(
    user_input: str, think_mode: bool = False
) -> Generator[dict, None, None]:
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("Empty message")
    vision_images: list = []

    attached_files = target_path.get_workspace_files()
    allow_read = getattr(cfg, "ALLOW_READ", True)
    allow_write = getattr(cfg, "ALLOW_WRITE", True)

    if getattr(cfg, "DEBUG", False):
        logger.setLevel(logging.DEBUG)
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)s "
                "%(name)s: %(message)s",
            )
        logger.debug(
            "chat_stream triggered (think_mode=%s)",
            think_mode,
        )

    system_prompt = _build_system_prompt(
        attached_files,
        allow_read,
        allow_write,
        think_mode,
        vision_images,
    )

    chat_history = memory.load_memory()

    user_content = user_input
    if vision_images:
        user_content += (
            "\n\n[System Note: The user attached "
            f"{len(vision_images)} image(s), "
            "but you are currently loaded as a "
            "text-only model. Politely inform them "
            "you cannot see images.]"
        )

    final_user_message = {
        "role": "user",
        "content": user_content,
    }

    llm_messages: list = [
        {"role": "system", "content": system_prompt}
    ]
    llm_messages.extend(chat_history)
    llm_messages.append(final_user_message)

    if think_mode:
        current_temp = min(
            getattr(cfg, "TEMPERATURE", 0.6) + 0.2, 1.0
        )
        current_top_p = None
        current_top_k = None
    else:
        current_temp = 0.7
        current_top_p = 0.8
        current_top_k = 20

    def _generate():
        profile = get_profile(cfg.MODEL_TYPE)

        if profile.supports_think_mode and think_mode:
            OPEN_TAG = profile.think_open
            CLOSE_TAG = profile.think_close
        else:
            OPEN_TAG = None
            CLOSE_TAG = None

        chat_template_kwargs = profile.get_thinking_kwargs(
            cfg.BACKEND_TYPE, think_mode
        )
        max_tok = getattr(cfg, "MAX_TOKENS", 8192)
        tools = (
            TOOL_DEFINITIONS
            if (
                allow_write
                and getattr(cfg, "JSON_TOOLS", False)
            )
            else None
        )

        full_response = ""
        tps = 0.0
        all_tool_blocks = []

        try:
            result = yield from _process_stream(
                _stream_llm_events(
                    llm_messages,
                    current_temp,
                    max_tok,
                    current_top_p,
                    current_top_k,
                    chat_template_kwargs,
                    tools,
                ),
                profile,
                think_mode,
                OPEN_TAG,
                CLOSE_TAG,
            )
            full_response, tps, tool_calls = result

            round_count = 0
            while (
                tool_calls
                and round_count < MAX_TOOL_ROUNDS
                and allow_write
            ):
                round_count += 1
                if getattr(cfg, "DEBUG", False):
                    logger.debug(
                        "Tool call round %d: %d tool calls",
                        round_count,
                        len(tool_calls),
                    )

                tool_results = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    try:
                        args = json.loads(
                            fn.get("arguments", "{}")
                        )
                    except json.JSONDecodeError:
                        args = {}
                    result_text = execute_tool(name, args)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.get(
                            "id",
                            f"call_{round_count}",
                        ),
                        "content": result_text,
                    })

                    if name in (
                        "write_file",
                        "edit_file",
                        "read_file",
                    ):
                        path = args.get("path", "")
                        block = {
                            "file": (
                                os.path.basename(path)
                                if path
                                else "untitled"
                            ),
                            "path": path,
                            "content": result_text,
                            "add_lines": 0,
                            "remove_lines": 0,
                            "complete": True,
                        }
                        if name == "write_file":
                            block["add_lines"] = len(
                                args.get("content", "")
                                .split("\n")
                            )
                        elif name == "edit_file":
                            block["remove_lines"] = len(
                                args.get(
                                    "old_string", ""
                                ).split("\n")
                            )
                            block["add_lines"] = len(
                                args.get(
                                    "new_string", ""
                                ).split("\n")
                            )
                        all_tool_blocks.append(block)
                        yield {
                            "type": "tool_result",
                            "content": block,
                        }

                llm_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                })
                llm_messages.extend(tool_results)

                result = yield from _process_stream(
                    _stream_llm_events(
                        llm_messages,
                        current_temp,
                        max_tok,
                        current_top_p,
                        current_top_k,
                        chat_template_kwargs,
                        tools,
                    ),
                    profile,
                    think_mode,
                    OPEN_TAG,
                    CLOSE_TAG,
                )
                follow_up_text, follow_up_tps, tool_calls = (
                    result
                )
                full_response += follow_up_text
                tps = follow_up_tps or tps

        except Exception as exc:
            yield {"type": "error", "content": str(exc)}

        finally:
            try:
                hist = memory.load_memory()
                hist.append({
                    "role": "user",
                    "content": user_input,
                })
                hist.append({
                    "role": "assistant",
                    "content": full_response,
                })
                memory.save_memory(
                    hist, target_path.get_current_target()
                )
            except Exception:
                pass
            yield {
                "type": "done",
                "tps": round(tps, 2),
                "tool_blocks": all_tool_blocks,
            }

    return _generate()
