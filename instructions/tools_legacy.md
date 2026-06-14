# ⚠️ CRITICAL SYSTEM PROTOCOL - DO NOT IGNORE ⚠️
1. **NO RAW CODE IN FILE TAGS**: You are FORBIDDEN from putting raw code directly inside a `<file>` tag.
2. **ACTION TAG REQUIREMENT**: Every `<file>` block MUST contain at least one inner action tag: `<add>` or `<remove>`.
3. **SYNTAX**: Always use `<file path="filename.ext">`. Never use `<file="filename">`.

━━━ TOOL SPECIFICATIONS ━━━━━━━

1. INSERT OR APPEND CODE (<add>)
Use this to add new code to a file.
- **Append (Default)**: If you use `<add>` without attributes, the code is appended to the very bottom of the file.
- **Insert Before Anchor**: To insert code before a specific code fragment, use `before` attribute (e.g., `<add before="def foo():">`).
- **Insert After Anchor**: To insert code after a specific code fragment, use `after` attribute (e.g., `<add after="import os">`).

Example - Inserting before an anchor:
<file path="example.py">
<add before="def main():">
def helper():
    print("Runs before main!")
</add>
</file>

Example - Inserting after an anchor:
<file path="example.py">
<add after="import os">
import sys
</add>
</file>

Example - Appending to the bottom:
<file path="example.py">
<add>
print("Appended to the end of the file.")
</add>
</file>

2. DELETE CODE (<remove>)
Use this to delete existing code.
<file path="example.py">
<remove>
Exact lines to delete
</remove>
</file>

━━━ PROHIBITED BEHAVIOR ━━━━━━━
❌ BAD (Will break the system):
<file path="index.html">
<html>...</html>
</file>

✅ GOOD (Required format):
<file path="index.html">
<add>
<html>...</html>
</add>
</file>

CRITICAL: The text inside <remove> tags must match the target file's indentation and spacing exactly.
