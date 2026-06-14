import re
import os


class StreamFormatter:
    def __init__(self, think_regex=None):
        self._tool_blocks: list[dict] = []

        self._tag_start = re.compile(
            (
                r'<file\b[^>]*path\s*=\s*'
                r'["\']([^"\']+)["\']'
            ),
            re.IGNORECASE,
        )
        self._tag_end = re.compile(
            r'</file\s*>', re.IGNORECASE
        )
        self._add_re = re.compile(
            r'<add\b[^>]*>(.*?)</add>',
            re.DOTALL | re.IGNORECASE,
        )
        self._remove_re = re.compile(
            r'<remove>(.*?)</remove>',
            re.DOTALL | re.IGNORECASE,
        )
        self._think_block = think_regex

    def process(
        self, full_text: str, strip_think: bool = True
    ) -> dict:
        tool_blocks: list[dict] = []
        display_parts: list[str] = []
        remaining = full_text

        while True:
            start = self._tag_start.search(remaining)
            if not start:
                display_parts.append(remaining)
                break

            display_parts.append(remaining[: start.start()])
            after_open = remaining[start.start():]
            filepath = start.group(1)
            end = self._tag_end.search(after_open)

            if end:
                tool_content = after_open[: end.end()]
                remaining = after_open[end.end():]
                complete = True
            else:
                tool_content = after_open
                remaining = ""
                complete = False

            add_lines = 0
            for add_text in self._add_re.findall(tool_content):
                stripped = add_text.strip()
                if stripped:
                    add_lines += len(stripped.split("\n"))

            remove_lines = 0
            for remove_text in self._remove_re.findall(
                tool_content
            ):
                stripped = remove_text.strip()
                if stripped:
                    remove_lines += len(
                        stripped.split("\n")
                    )

            tool_blocks.append({
                "file": os.path.basename(filepath),
                "path": filepath,
                "content": tool_content,
                "add_lines": add_lines,
                "remove_lines": remove_lines,
                "complete": complete,
            })

        self._tool_blocks = tool_blocks

        display = "".join(display_parts)
        if self._think_block is not None:
            display = self._think_block.sub("", display)

        return {
            "display": display,
            "tool_blocks": tool_blocks,
        }

    @property
    def has_tools(self) -> bool:
        return bool(self._tool_blocks)
