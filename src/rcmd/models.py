from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    id: str
    command: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created: str = ""
    source: str = "manual"
