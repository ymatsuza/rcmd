from rcmd import history


def test_parse_bash_plain():
    text = "ls -la\n\ngit status\n"
    assert history.parse_history(text, "bash") == ["ls -la", "git status"]


def test_parse_zsh_extended_and_plain():
    text = ": 1700000000:0;git push\nls\n: 1700000001:0;docker ps\n"
    assert history.parse_history(text, "zsh") == ["git push", "ls", "docker ps"]


def test_parse_fish_yaml():
    text = "- cmd: git commit\n  when: 1700000000\n- cmd: ls -la\n  when: 1700000001\n"
    assert history.parse_history(text, "fish") == ["git commit", "ls -la"]


def test_parse_powershell_plain():
    text = "Get-ChildItem\r\nGet-Process\r\n"
    assert history.parse_history(text, "powershell") == ["Get-ChildItem", "Get-Process"]


def test_postprocess_reverse_unique_limit():
    cmds = ["a", "b", "a", "c", "b"]
    # reverse -> [b, c, a, b, a]; unique keep-first -> [b, c, a]; limit 2 -> [b, c]
    assert history.postprocess(cmds, limit=2, unique=True, reverse=True) == ["b", "c"]
    # no options = identity
    assert history.postprocess(cmds) == cmds


def test_detect_shell_from_env(monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert history.detect_shell() == "zsh"


def test_detect_shell_windows_default(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr(history.sys, "platform", "win32")
    assert history.detect_shell() == "powershell"


def test_default_history_path_known_shells():
    assert history.default_history_path("bash").name == ".bash_history"
    assert history.default_history_path("zsh").name == ".zsh_history"
    assert history.default_history_path("fish").name == "fish_history"
    assert history.default_history_path("powershell").name == "ConsoleHost_history.txt"
    assert history.default_history_path("unknown") is None
