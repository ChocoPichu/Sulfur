import re
import os
import src.modules.configurations as configurations
import src.modules.target_path as target_path
from src.modules.sandbox_file_operations import (
    read_sandbox,
    write_sandbox,
)


def check_edits(response_text: str) -> dict:
    proposals = []

    file_pattern = (
        r'<file\b[^>]*?(?:path|url|name|file)\s*=\s*'
        r'["\']([^"\']+)["\'][^>]*?>(.*?)</file\s*>'
    )
    file_blocks = list(
        re.finditer(
            file_pattern, response_text, re.DOTALL | re.IGNORECASE
        )
    )

    if file_blocks:
        for file_match in file_blocks:
            file_path = file_match.group(1).strip()
            file_content = file_match.group(2)

            removes = re.findall(
                r"<remove>(.*?)</remove>",
                file_content,
                re.DOTALL | re.IGNORECASE,
            )
            for rm_txt in removes:
                proposals.append({
                    'type': 'remove',
                    'remove': rm_txt.strip('\r\n'),
                    'path': file_path,
                })

            add_matches = re.finditer(
                r"<add\b([^>]*)>(.*?)</add>",
                file_content,
                re.DOTALL | re.IGNORECASE,
            )
            for add_match in add_matches:
                attrs_str = add_match.group(1)
                add_content = add_match.group(2).strip('\r\n')
                before_m = re.search(
                    r'before\s*=\s*["\']([^"\']+)["\']',
                    attrs_str,
                    re.IGNORECASE,
                )
                after_m = re.search(
                    r'after\s*=\s*["\']([^"\']+)["\']',
                    attrs_str,
                    re.IGNORECASE,
                )
                proposals.append({
                    'type': 'add',
                    'before': (
                        before_m.group(1) if before_m else None
                    ),
                    'after': (
                        after_m.group(1) if after_m else None
                    ),
                    'add': add_content,
                    'path': file_path,
                })
    else:
        removes = re.findall(
            r"<remove>(.*?)</remove>",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        for rm_txt in removes:
            proposals.append({
                'type': 'remove',
                'remove': rm_txt.strip('\r\n'),
            })

        add_matches = re.finditer(
            r"<add\b([^>]*)>(.*?)</add>",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        for add_match in add_matches:
            attrs_str = add_match.group(1)
            add_content = add_match.group(2).strip('\r\n')
            before_m = re.search(
                r'before\s*=\s*["\']([^"\']+)["\']',
                attrs_str,
                re.IGNORECASE,
            )
            after_m = re.search(
                r'after\s*=\s*["\']([^"\']+)["\']',
                attrs_str,
                re.IGNORECASE,
            )
            proposals.append({
                'type': 'add',
                'before': (
                    before_m.group(1) if before_m else None
                ),
                'after': (
                    after_m.group(1) if after_m else None
                ),
                'add': add_content,
            })

    return {'has_edits': len(proposals) > 0, 'proposals': proposals}


def apply_edits(proposals: list[dict]) -> dict:
    if not proposals:
        return {'success': True, 'message': 'No changes made.'}

    workspace_files = target_path.get_workspace_files()

    files_to_edit = {}
    for p in proposals:
        path = p.get('path')

        if not path:
            if len(workspace_files) == 1:
                path = workspace_files[0]
            elif len(workspace_files) > 1:
                return {
                    'success': False,
                    'error': (
                        "Multiple files in workspace, but the AI "
                        "failed to specify which "
                        '<file path="..."> to edit!'
                    ),
                }
            else:
                return {
                    'success': False,
                    'error': (
                        "No files in workspace to edit."
                    ),
                }

        if path not in files_to_edit:
            files_to_edit[path] = []
        files_to_edit[path].append(p)

    results = []

    for path, file_proposals in files_to_edit.items():
        file_data = read_sandbox(path)
        if file_data.startswith("Error:"):
            return {'success': False, 'error': file_data}

        new_file_data = file_data

        for proposal in file_proposals:
            if proposal['type'] == 'remove':
                if proposal['remove'] in new_file_data:
                    new_file_data = new_file_data.replace(
                        proposal['remove'], "", 1
                    )
            elif proposal['type'] == 'add':
                add_text = proposal['add']
                before = proposal.get('before')
                after = proposal.get('after')

                if before:
                    idx = new_file_data.find(before)
                    if idx == -1:
                        return {
                            'success': False,
                            'error': (
                                "Anchor text not found "
                                "to insert before: "
                                f"{before[:80]}"
                            ),
                        }
                    new_file_data = (
                        new_file_data[:idx]
                        + add_text
                        + '\n'
                        + new_file_data[idx:]
                    )
                elif after:
                    idx = new_file_data.find(after)
                    if idx == -1:
                        return {
                            'success': False,
                            'error': (
                                "Anchor text not found "
                                "to insert after: "
                                f"{after[:80]}"
                            ),
                        }
                    insert_pos = idx + len(after)
                    new_file_data = (
                        new_file_data[:insert_pos]
                        + '\n'
                        + add_text
                        + new_file_data[insert_pos:]
                    )
                else:
                    suffix = (
                        '\n'
                        if not new_file_data.endswith('\n')
                        else ''
                    )
                    new_file_data += suffix + add_text

        if new_file_data != file_data:
            write_sandbox(new_file_data, path)
            results.append(os.path.basename(path))

    if results:
        return {
            'success': True,
            'message': f"Updated: {', '.join(results)}",
        }
    return {'success': True, 'message': 'No changes made.'}
