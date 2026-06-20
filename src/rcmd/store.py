from __future__ import annotations

import tomllib

from rcmd.errors import RcmdError
from rcmd.models import Entry


def _esc(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return "".join(out)


def _q(s: str) -> str:
    return '"' + _esc(s) + '"'


def dumps(entries: list[Entry]) -> str:
    blocks: list[str] = []
    for e in entries:
        tags = "[" + ", ".join(_q(t) for t in e.tags) + "]"
        blocks.append(
            "[[entry]]\n"
            f"id = {_q(e.id)}\n"
            f"command = {_q(e.command)}\n"
            f"description = {_q(e.description)}\n"
            f"tags = {tags}\n"
            f"created = {_q(e.created)}\n"
            f"source = {_q(e.source)}\n"
        )
    return "\n".join(blocks)


def loads(text: str) -> list[Entry]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise RcmdError(f"store.toml is corrupt: {exc}") from exc
    entries: list[Entry] = []
    for row in data.get("entry", []):
        entries.append(
            Entry(
                id=str(row.get("id", "")),
                command=str(row.get("command", "")),
                description=str(row.get("description", "")),
                tags=[str(t) for t in row.get("tags", [])],
                created=str(row.get("created", "")),
                source=str(row.get("source", "manual")),
            )
        )
    return entries
