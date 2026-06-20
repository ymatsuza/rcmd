import pytest

from rcmd import placeholders
from rcmd.errors import RcmdError


def test_find_placeholders_order_and_dedup():
    cmd = "ssh {{user}}@{{host}} -p {{port}} # {{host}} again"
    assert placeholders.find_placeholders(cmd) == ["user", "host", "port"]


def test_find_placeholders_none():
    assert placeholders.find_placeholders("ls -la") == []


def test_substitute_replaces_all():
    cmd = "docker run {{image}} {{image}}"
    assert placeholders.substitute(cmd, {"image": "alpine"}) == "docker run alpine alpine"


def test_substitute_missing_raises_with_names():
    with pytest.raises(RcmdError) as exc:
        placeholders.substitute("scp {{src}} {{dst}}", {"src": "a"})
    assert "dst" in str(exc.value)


def test_substitute_no_placeholders_is_identity():
    assert placeholders.substitute("echo hi", {}) == "echo hi"
