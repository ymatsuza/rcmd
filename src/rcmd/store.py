from __future__ import annotations

import os
import secrets
import string
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from rcmd.errors import RcmdError
from rcmd.models import Entry  # re-exported as store.Entry for callers/tests


# --- TOML serialize / parse -------------------------------------------------


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


# --- paths, ids, CRUD, file I/O ---------------------------------------------


def store_path() -> Path:
    env = os.environ.get("RCMD_STORE")
    if env:
        return Path(env)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "rcmd" / "store.toml"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "rcmd" / "store.toml"


_ALPHABET = string.ascii_lowercase + string.digits


def gen_id(existing: list[str] | set[str] = ()) -> str:
    existing = set(existing)
    while True:
        cand = "".join(secrets.choice(_ALPHABET) for _ in range(4))
        if cand not in existing:
            return cand


def add(
    entries: list[Entry],
    command: str,
    description: str = "",
    tags: list[str] | None = None,
    source: str = "manual",
) -> Entry:
    command = command.strip()
    if not command:
        raise RcmdError("cannot save an empty command")
    e = Entry(
        id=gen_id([x.id for x in entries]),
        command=command,
        description=description or "",
        tags=list(tags or []),
        created=datetime.now().isoformat(timespec="seconds"),
        source=source,
    )
    entries.append(e)
    return e


def find(entries: list[Entry], id_: str) -> Entry | None:
    for e in entries:
        if e.id == id_:
            return e
    prefix = [e for e in entries if e.id.startswith(id_)]
    if len(prefix) == 1:
        return prefix[0]
    if len(prefix) > 1:
        raise RcmdError(
            f"ambiguous id '{id_}': matches {', '.join(e.id for e in prefix)}"
        )
    return None


def load(path) -> list[Entry]:
    p = Path(path)
    if not p.exists():
        return []
    return loads(p.read_text(encoding="utf-8"))


def save(path, entries: list[Entry]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(dumps(entries), encoding="utf-8")
    os.replace(tmp, p)
