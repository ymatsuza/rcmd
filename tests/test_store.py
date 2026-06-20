import pytest

from rcmd.models import Entry
from rcmd import store
from rcmd.errors import RcmdError


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
    with pytest.raises(RcmdError):
        store.loads("[[entry]]\nid = \"oops")  # unterminated string


def test_store_path_respects_env(monkeypatch, tmp_path):
    target = tmp_path / "custom.toml"
    monkeypatch.setenv("RCMD_STORE", str(target))
    assert store.store_path() == target


def test_store_path_windows(monkeypatch):
    monkeypatch.delenv("RCMD_STORE", raising=False)
    monkeypatch.setattr(store.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\x\AppData\Roaming")
    p = store.store_path()
    assert p.name == "store.toml"
    assert "rcmd" in p.parts


def test_store_path_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("RCMD_STORE", raising=False)
    monkeypatch.setattr(store.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert store.store_path() == tmp_path / "rcmd" / "store.toml"


def test_gen_id_unique_and_format():
    ids = {store.gen_id() for _ in range(50)}
    assert all(len(i) == 4 and i.isalnum() for i in ids)
    existing = ["aaaa", "bbbb"]
    new = store.gen_id(existing)
    assert new not in existing


def test_add_strips_and_rejects_empty():
    entries: list = []
    e = store.add(entries, "  ls -la  ", description="list", tags=["fs"])
    assert e.command == "ls -la"
    assert e.tags == ["fs"]
    assert e.created  # non-empty ISO timestamp
    assert entries == [e]
    with pytest.raises(RcmdError):
        store.add(entries, "   ")


def test_find_exact_prefix_ambiguous_missing():
    entries = [
        Entry(id="abcd", command="one"),
        Entry(id="abef", command="two"),
        Entry(id="zzzz", command="three"),
    ]
    assert store.find(entries, "abcd").command == "one"   # exact
    assert store.find(entries, "zz").command == "three"   # unique prefix
    with pytest.raises(RcmdError):
        store.find(entries, "ab")                          # ambiguous prefix
    assert store.find(entries, "nope") is None             # missing


def test_load_missing_file_returns_empty(tmp_path):
    assert store.load(tmp_path / "absent.toml") == []


def test_save_then_load_atomic(tmp_path):
    path = tmp_path / "deep" / "store.toml"
    entries = [store.Entry(id="k1", command="echo hi", tags=["t"])]
    store.save(path, entries)
    assert path.exists()
    assert store.load(path) == entries
