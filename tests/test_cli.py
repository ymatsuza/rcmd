import pytest
from typer.testing import CliRunner

from rcmd.cli import app

runner = CliRunner()


def _text(res):
    """Combined stdout+stderr, robust across click versions (mixed vs split)."""
    parts = [res.output or ""]
    try:
        if res.stderr:
            parts.append(res.stderr)
    except ValueError:
        pass  # stderr was mixed into output already
    return "".join(parts)


@pytest.fixture(autouse=True)
def _isolate_store(monkeypatch, tmp_path):
    monkeypatch.setenv("RCMD_STORE", str(tmp_path / "store.toml"))


def _save(command, *args):
    res = runner.invoke(app, ["save", command, *args])
    assert res.exit_code == 0, _text(res)
    return res.output.strip()  # the new id


# --- save / version ---------------------------------------------------------


def test_version():
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert res.output.strip()


def test_save_returns_id_and_persists():
    new_id = _save("docker ps", "-d", "list containers", "-t", "docker")
    assert len(new_id) == 4
    res = runner.invoke(app, ["show", new_id])
    assert res.exit_code == 0
    assert "docker ps" in res.output
    assert "list containers" in res.output
    assert "docker" in res.output


def test_save_from_stdin():
    res = runner.invoke(app, ["save"], input="git status\n")
    assert res.exit_code == 0
    new_id = res.output.strip()
    res2 = runner.invoke(app, ["show", new_id])
    assert "git status" in res2.output


def test_save_empty_is_usage_error():
    res = runner.invoke(app, ["save", "   "])
    assert res.exit_code == 2
    assert "empty" in _text(res)


# --- list / search / show ---------------------------------------------------


def test_list_and_search_lines_and_json():
    id1 = _save("docker ps", "-t", "docker")
    id2 = _save("git log", "-t", "git")
    res = runner.invoke(app, ["list"])
    assert res.exit_code == 0
    assert id1 in res.output and id2 in res.output
    res = runner.invoke(app, ["search", "docker"])
    assert res.exit_code == 0
    assert id1 in res.output and id2 not in res.output
    res = runner.invoke(app, ["list", "-t", "git"])
    assert id2 in res.output and id1 not in res.output
    res = runner.invoke(app, ["search", "git", "--json"])
    assert '"command": "git log"' in res.output


def test_search_no_hits_exit_1():
    _save("ls")
    res = runner.invoke(app, ["search", "zzz"])
    assert res.exit_code == 1


def test_show_missing_exit_1():
    res = runner.invoke(app, ["show", "nope"])
    assert res.exit_code == 1
    assert "no entry" in _text(res)


# --- get / run (placeholders) ----------------------------------------------


def test_get_substitutes_placeholders():
    new_id = _save("ssh {{user}}@{{host}}")
    res = runner.invoke(app, ["get", new_id, "--set", "user=root", "--set", "host=h1"])
    assert res.exit_code == 0
    assert res.output.strip() == "ssh root@h1"


def test_get_missing_placeholder_exit_2():
    new_id = _save("ssh {{user}}@{{host}}")
    res = runner.invoke(app, ["get", new_id, "--set", "user=root"])
    assert res.exit_code == 2
    assert "host" in _text(res)


def test_get_bad_set_exit_2():
    new_id = _save("echo hi")
    res = runner.invoke(app, ["get", new_id, "--set", "noequals"])
    assert res.exit_code == 2


def test_run_dry_run_prints_without_executing():
    new_id = _save("echo {{msg}}")
    res = runner.invoke(app, ["run", new_id, "--set", "msg=hello", "--dry-run"])
    assert res.exit_code == 0
    assert res.output.strip() == "echo hello"


# --- edit / rm --------------------------------------------------------------


def test_edit_updates_fields():
    new_id = _save("ls", "-d", "old")
    res = runner.invoke(app, ["edit", new_id, "-d", "new desc", "-t", "fs", "--command", "ls -la"])
    assert res.exit_code == 0
    res2 = runner.invoke(app, ["show", new_id])
    assert "new desc" in res2.output
    assert "ls -la" in res2.output
    assert "fs" in res2.output


def test_edit_empty_command_exit_2():
    new_id = _save("ls")
    res = runner.invoke(app, ["edit", new_id, "--command", "   "])
    assert res.exit_code == 2


def test_rm_removes_and_missing_exit_1():
    new_id = _save("ls")
    res = runner.invoke(app, ["rm", new_id])
    assert res.exit_code == 0
    assert runner.invoke(app, ["show", new_id]).exit_code == 1
    assert runner.invoke(app, ["rm", new_id]).exit_code == 1


# --- history ----------------------------------------------------------------


def test_history_reads_file_and_postprocesses(tmp_path):
    hist = tmp_path / "h.txt"
    hist.write_text("ls\ngit status\nls\n", encoding="utf-8")
    res = runner.invoke(app, ["history", "--shell", "bash", "--file", str(hist), "--unique"])
    assert res.exit_code == 0
    assert res.output.splitlines() == ["ls", "git status"]


def test_history_missing_file_exit_1(tmp_path):
    res = runner.invoke(app, ["history", "--shell", "bash", "--file", str(tmp_path / "absent")])
    assert res.exit_code == 1
    assert "not found" in _text(res)
