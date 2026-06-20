from __future__ import annotations

from collections.abc import Iterable

from rcmd.models import Entry


def filter_entries(
    entries: list[Entry],
    query: str = "",
    tags: Iterable[str] = (),
) -> list[Entry]:
    q = query.lower()
    tagset = set(tags)
    out: list[Entry] = []
    for e in entries:
        if q and q not in e.command.lower() and q not in e.description.lower():
            continue
        if tagset and not tagset.issubset(set(e.tags)):
            continue
        out.append(e)
    return out
