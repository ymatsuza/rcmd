from rcmd.models import Entry
from rcmd import store


def test_roundtrip_preserves_special_chars():
    entries = [
        Entry(
            id="k3f9",
            command='git commit -m "msg with \\"quotes\\" and \\\\ backslash"\nsecond line\ttab',
            description="日本語の説明 with {{ph}}",
            tags=["git", "commit"],
            created="2026-06-20T10:30:00",
            source="history:zsh",
        ),
        Entry(id="a1b2", command="ls -la", tags=[], created="2026-06-20T10:31:00"),
    ]
    text = store.dumps(entries)
    out = store.loads(text)
    assert out == entries


def test_loads_empty_is_empty_list():
    assert store.loads("") == []


def test_loads_corrupt_raises():
    import pytest
    from rcmd.errors import RcmdError

    with pytest.raises(RcmdError):
        store.loads("[[entry]]\nid = \"oops")  # unterminated string
