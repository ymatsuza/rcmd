from __future__ import annotations

import re

from rcmd.errors import RcmdError

_TOKEN = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def find_placeholders(command: str) -> list[str]:
    seen: list[str] = []
    for m in _TOKEN.finditer(command):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def substitute(command: str, values: dict[str, str]) -> str:
    missing = [n for n in find_placeholders(command) if n not in values]
    if missing:
        raise RcmdError(
            f"missing value(s) for placeholder(s): {', '.join(missing)}"
        )
    return _TOKEN.sub(lambda m: values[m.group(1)], command)
