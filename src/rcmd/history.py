from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_FISH_CMD = re.compile(r"^\s*-\s*cmd:\s*(.*)$")


def detect_shell() -> str:
    shell = os.environ.get("SHELL")
    if shell:
        name = Path(shell).name.lower()
        for s in ("zsh", "bash", "fish"):
            if s in name:
                return s
    if sys.platform == "win32":
        return "powershell"
    return "bash"


def default_history_path(shell: str) -> Path | None:
    home = Path.home()
    if shell == "bash":
        return home / ".bash_history"
    if shell == "zsh":
        return home / ".zsh_history"
    if shell == "fish":
        return home / ".local" / "share" / "fish" / "fish_history"
    if shell == "powershell":
        appdata = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        return (
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "PowerShell"
            / "PSReadLine"
            / "ConsoleHost_history.txt"
        )
    return None


def parse_history(text: str, shell: str) -> list[str]:
    cmds: list[str] = []
    if shell == "zsh":
        for ln in text.splitlines():
            if ln.startswith(":"):
                idx = ln.find(";")
                cmds.append(ln[idx + 1 :] if idx != -1 else ln)
            elif ln.strip():
                cmds.append(ln)
    elif shell == "fish":
        for ln in text.splitlines():
            m = _FISH_CMD.match(ln)
            if m:
                cmds.append(m.group(1))
    else:  # bash, powershell, default
        cmds = [ln for ln in text.splitlines() if ln.strip()]
    return [c for c in cmds if c.strip()]


def postprocess(
    cmds: list[str],
    limit: int = 0,
    unique: bool = False,
    reverse: bool = False,
) -> list[str]:
    if reverse:
        cmds = list(reversed(cmds))
    if unique:
        seen: set[str] = set()
        deduped: list[str] = []
        for c in cmds:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        cmds = deduped
    if limit and limit > 0:
        cmds = cmds[:limit]
    return cmds
