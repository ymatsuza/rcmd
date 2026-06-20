from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import typer

from rcmd import __version__
from rcmd import history as historymod
from rcmd import placeholders
from rcmd import search as searchmod
from rcmd import store
from rcmd.errors import RcmdError
from rcmd.models import Entry

app = typer.Typer(
    help="rcmd: 個人コマンド・ナレッジベース（履歴取込→注釈・タグ→検索→呼び出し）",
    add_completion=False,
)


def _die(msg: str, code: int = 2) -> None:
    typer.echo(f"rcmd: {msg}", err=True)
    raise typer.Exit(code)


def _load() -> list[Entry]:
    try:
        return store.load(store.store_path())
    except RcmdError as exc:
        _die(str(exc))
        return []  # unreachable


def _persist(entries: list[Entry]) -> None:
    store.save(store.store_path(), entries)


def _resolve(entries: list[Entry], id_: str) -> Entry:
    try:
        e = store.find(entries, id_)
    except RcmdError as exc:
        _die(str(exc))  # ambiguous -> exit 2
    if e is None:
        typer.echo(f"rcmd: no entry with id '{id_}'", err=True)
        raise typer.Exit(1)
    return e


def _line(e: Entry) -> str:
    tags = f"[{','.join(e.tags)}]" if e.tags else ""
    return "\t".join([e.id, e.command, e.description, tags])


def _emit(entries: list[Entry], json_out: bool) -> None:
    if json_out:
        typer.echo(json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2))
    else:
        for e in entries:
            typer.echo(_line(e))


def _parse_set(pairs: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for p in pairs:
        if "=" not in p:
            _die(f"invalid --set '{p}' (expected NAME=VALUE)")
        k, v = p.split("=", 1)
        values[k] = v
    return values


@app.command()
def save(
    command: Optional[str] = typer.Argument(None, help="保存するコマンド（省略時は stdin）"),
    desc: str = typer.Option("", "--desc", "-d", help="説明"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="タグ（複数可）"),
) -> None:
    """コマンドを保存し、採番した id を出力する。"""
    if command is None:
        import sys

        command = sys.stdin.read()
    command = command.strip()
    if not command:
        _die("cannot save an empty command")
    entries = _load()
    try:
        e = store.add(entries, command, desc, tag or [], "manual")
    except RcmdError as exc:
        _die(str(exc))
    _persist(entries)
    typer.echo(e.id)


@app.command()
def history(
    shell: str = typer.Option("auto", "--shell", help="auto|bash|zsh|fish|powershell"),
    file: Optional[str] = typer.Option(None, "--file", help="任意の履歴ファイルパス"),
    limit: int = typer.Option(0, "--limit", help="出力件数の上限（0=無制限）"),
    unique: bool = typer.Option(False, "--unique", help="重複除去（出現順保持）"),
    reverse: bool = typer.Option(False, "--reverse", help="新しい順"),
) -> None:
    """シェル履歴を行出力（取込の橋渡し。保存はしない）。"""
    sh = historymod.detect_shell() if shell == "auto" else shell
    path = Path(file) if file else historymod.default_history_path(sh)
    if path is None or not path.exists():
        typer.echo(f"rcmd: history file not found: {path}", err=True)
        raise typer.Exit(1)
    text = path.read_text(encoding="utf-8", errors="replace")
    cmds = historymod.parse_history(text, sh)
    cmds = historymod.postprocess(cmds, limit=limit, unique=unique, reverse=reverse)
    for c in cmds:
        typer.echo(c)


@app.command()
def search(
    query: str = typer.Argument("", help="部分一致クエリ"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """command と description を部分一致検索（fzf 向け行出力 / --json）。"""
    hits = searchmod.filter_entries(_load(), query, tag or [])
    _emit(hits, json_out)
    if not hits:
        raise typer.Exit(1)


@app.command("list")
def list_(
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """全件（または --tag）一覧。"""
    hits = searchmod.filter_entries(_load(), "", tag or [])
    _emit(hits, json_out)


@app.command()
def show(id: str) -> None:
    """1 エントリの詳細（man page ビュー）。"""
    e = _resolve(_load(), id)
    typer.echo(f"id:          {e.id}")
    typer.echo(f"command:     {e.command}")
    typer.echo(f"description: {e.description}")
    typer.echo(f"tags:        {', '.join(e.tags)}")
    typer.echo(f"created:     {e.created}")
    typer.echo(f"source:      {e.source}")
    ph = placeholders.find_placeholders(e.command)
    if ph:
        typer.echo(f"placeholders: {', '.join(ph)}")


@app.command()
def get(
    id: str,
    set_: Optional[list[str]] = typer.Option(None, "--set", help="NAME=VALUE（複数可）"),
) -> None:
    """解決後のコマンド文字列だけを出力（$(rcmd get ID) / クリップボード連携用）。"""
    e = _resolve(_load(), id)
    values = _parse_set(set_ or [])
    try:
        typer.echo(placeholders.substitute(e.command, values))
    except RcmdError as exc:
        _die(str(exc))


@app.command()
def run(
    id: str,
    set_: Optional[list[str]] = typer.Option(None, "--set", help="NAME=VALUE（複数可）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="実行せず確定コマンドを表示"),
) -> None:
    """プレースホルダ差込後に実行（--dry-run は表示のみ）。"""
    e = _resolve(_load(), id)
    values = _parse_set(set_ or [])
    try:
        cmd = placeholders.substitute(e.command, values)
    except RcmdError as exc:
        _die(str(exc))
    if dry_run:
        typer.echo(cmd)
        return
    # shell=True is intentional and required: `cmd` is a shell command the user
    # saved themselves (may contain pipes/redirects/globs). This is the user's own
    # curated store, not untrusted input — `--dry-run`/`get` provide print-only paths.
    proc = subprocess.run(cmd, shell=True)  # noqa: S602
    raise typer.Exit(proc.returncode)


@app.command()
def edit(
    id: str,
    desc: Optional[str] = typer.Option(None, "--desc", "-d"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="指定するとタグを置換"),
    command: Optional[str] = typer.Option(None, "--command"),
) -> None:
    """指定フィールドのみ更新（タグは指定時に置換）。"""
    entries = _load()
    e = _resolve(entries, id)
    if desc is not None:
        e.description = desc
    if tag:
        e.tags = list(tag)
    if command is not None:
        if not command.strip():
            _die("command cannot be empty")
        e.command = command.strip()
    _persist(entries)
    typer.echo(e.id)


@app.command()
def rm(id: str) -> None:
    """エントリを削除。"""
    entries = _load()
    e = _resolve(entries, id)
    entries.remove(e)
    _persist(entries)
    typer.echo(f"removed {e.id}")


@app.command()
def version() -> None:
    """バージョンを表示。"""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
