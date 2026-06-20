# rcmd 設計書（解決アプリ第3号：個人コマンド・ナレッジベース）

- 日付: 2026-06-20
- ステータス: 承認済み（brainstorming にてスコープ・名前・保存形式・機能境界を確定）
- 種別: アプリ設計仕様

> プロジェクト名 `rcmd`（= recall / recorded command。rsed・rcaudit と同じ r- ファミリー）。コマンド名も `rcmd`。

## 0. 背景（なぜこれを作るか）

サブプロジェクト (A) `kadai-radar` が r/commandline から収集・採点した最有力・未着手課題（スコア84）。実スレッドを精読し、需要の内訳を検証した：

| スレッド | OP の要望 | コメントの推奨ツール | 状況 |
|---|---|---|---|
| Tame Your Linux Command History | 履歴を日付で絞る・整理・検索 | ctrl+r, fzf, hstr, atuin | **飽和** |
| Choosing a command from history | 履歴ファイルを開かず選んで実行 | ctrl+r, fzf, hstr | **飽和** |
| Personal man pages for commands/config | コマンド/設定変更を自分用 man page に記録 | （DIY 多数） | **手薄** |
| Looking for a snippet tool | 自作スニペットを追加・オフライン・検索・引数付き | navi, pet, espanso | **惜しい** |
| Stores reference info / DSLs | 自作コマンドを説明付きで保存・検索・実行 | navi, keep | **惜しい** |

結論：**履歴の"検索/選択"は atuin/fzf/hstr で飽和**。求められて未充足なのは**「個人コマンド・ナレッジベース」層**。象徴は reference-store の OP が「Tool / Command / Notes の3列スプレッドシートで手管理している、これをインタラクティブにしたい」と述べた点。既存ツールの「惜しい」＝ navi はコミュニティ cheatsheet 寄りで自由メモ／タグが弱い・TUI 重い、pet は検索/タグ/説明が薄い、keep はほぼ非メンテ、いずれも **Windows/PowerShell 対応が弱く**、かつ**「生の履歴 → 注釈を付けて自分の知識に昇華」という橋渡しを誰もやっていない**（atuin は履歴に注釈を付けられない）。

→ **「生のシェル履歴を取り込み → 説明・タグを付けて curate → 検索 → 呼び出し（出力/実行）を、Windows/PowerShell 含めクロスプラットフォームで成立させる軽量 CLI」** を作る。atuin/fzf と競合せず補完する（彼らは"探す"、本ツールは"残して育てる"）。ローカル完結・依存最小。

## 1. ゴールと非ゴール

**ゴール（v1）**
- 残す価値のあるコマンドを、説明・タグ付きで**保存**できる（`save`）。引数は stdin からも受け、`history | fzf | rcmd save` のパイプで履歴から拾える。
- 自分のシェル**履歴を取り込みの橋渡し**として行出力できる（`history`）。bash/zsh/fish/PowerShell をクロスプラットフォームに解決。
- 保存済みを **検索 / 一覧 / 詳細表示**できる（`search` / `list` / `show`）。検索は fzf にパイプできる行出力。
- 保存済みコマンドを **呼び出す**：文字列だけ出力（`get`）または実行（`run`）。`{{name}}` プレースホルダを `--set` で差し込める。
- **編集 / 削除**（`edit` / `rm`）。
- データは**単一プレーンテキスト（TOML）**でローカル完結。人間が手編集でき、git/dotfiles で同期できる。純関数コアでテスト完全検証。

**非ゴール（v1、後段）**
- 組込み対話 TUI ピッカー（fzf 風選択 UI）。クロスプラットフォーム TUI は重い → v1 は**非対話＋外部 fzf 連携**に徹する。
- ライブ履歴キャプチャ（シェルフック常駐・atuin 的自動記録）。飽和領域につき作らない。
- クリップボード直書き。`rcmd get` の出力を OS のクリップボードツール（`clip`/`pbcopy`/`wl-copy`）にパイプして代替。
- クラウド同期・共有 cheatsheet マーケット・暗号化。
- 複数ストア / プロファイル切替（`$RCMD_STORE` で十分）。

## 2. 設計判断

### 2.1 保存形式 = 単一 TOML ファイル（追加依存ゼロ）

「個人ナレッジベース＝手編集・git 同期・personal man page」の文化に最も合うため、不透明な SQLite ではなく**人間可読な単一 TOML** を採用。

- 読み込み = stdlib `tomllib`（Python 3.11+）。
- 書き込み = `store.py` 内の**閉じたスキーマ専用シリアライザ**（決定論的・round-trip をテスト）。任意 TOML を書くわけではなく固定スキーマ（`id`/`command`/`description`/`tags`/`created`/`source`）のみを出力するため、文字列エスケープを正しく実装すれば小さく安全に保てる。追加の実行時依存を持たない（typer のみ）。
- 却下 A: SQLite（stdlib だが不透明・手編集や同期マージが困難・diff が読めない）。
- 却下 B: JSONL（追記は楽だが複数行コマンドのエスケープが醜く手編集性で TOML に劣る）。

### 2.2 プレースホルダ構文 = `{{name}}`

navi の `<arg>` はシェルのリダイレクト `<` `>` と衝突しうる（`cmd < file` を保存できない）。曖昧さを避けるため **mustache 風 `{{name}}`** を採用。`run`/`get` 時に `--set name=value` で差し込む。未指定のプレースホルダがあれば**エラーで不足分を列挙**（非対話・決定論的）。

### 2.3 選択 UI = 非対話＋外部 fzf 連携

`search`/`list`/`history` は機械可読な行出力（既定 1 行 1 エントリ）。`rcmd search docker | fzf` で選べる。クロスプラットフォーム TUI 実装を避け、Windows でも確実に動かす。

## 3. CLI 仕様

```
rcmd save  [COMMAND] [-d/--desc TEXT] [-t/--tag TAG]...   # COMMAND 省略時は stdin
rcmd history [--shell auto|bash|zsh|fish|powershell] [--file PATH] [--limit N] [--unique] [--reverse]
rcmd search QUERY [-t/--tag TAG] [--json]
rcmd list [-t/--tag TAG] [--json]
rcmd show ID
rcmd get  ID [--set NAME=VALUE]...
rcmd run  ID [--set NAME=VALUE]... [--dry-run]
rcmd edit ID [-d/--desc TEXT] [-t/--tag TAG]... [--command TEXT]
rcmd rm   ID
rcmd version
```

- **save** … エントリを追加し採番した `id` を stdout に返す。`COMMAND` 省略かつ stdin がパイプなら stdin を読む（前後空白を strip）。`-t` は繰り返し可。重複コマンドは既定で別エントリ（警告は出さない）。
- **history** … 解決したシェル履歴を**行出力**（取込の橋渡し）。`--unique` で重複除去（出現順保持）、`--reverse` で新しい順、`--limit` で件数、`--shell`/`--file` で上書き。保存はしない（パイプ先で `rcmd save`）。
- **search** … `command` と `description` を部分一致（大小無視）。`-t` でタグ AND 絞り込み。既定は `ID␉command␉desc␉[tags]` の行（fzf 向け）、`--json` で配列。ヒット 0 件は終了コード 1。
- **list** … 全件（または `-t` でタグ）一覧。出力形式は search と同じ。
- **show** … 1 エントリの詳細（"man page" ビュー：id / command / description / tags / created / source / 検出した `{{placeholders}}`）。
- **get** … 解決後の**コマンド文字列だけ**を stdout に出力（`$(rcmd get ID)` やクリップボードツールへのパイプ用）。`--set` でプレースホルダ差込。
- **run** … プレースホルダ差込後に subprocess 実行。`--dry-run` は実行せず確定コマンドを表示。
- **edit** … 指定フィールドのみ更新。`-t` を与えるとタグは**置換**（追加は将来の `--add-tag` を検討、v1 は置換）。
- **rm** … 削除。存在しない ID は終了コード 1。
- **version** … バージョン表示。

**終了コード**（rsed/rcaudit 規約に一致）: `0`=正常、`1`=対象なし/一部 I/O 失敗（検索 0 件・存在しない ID・履歴ファイル無し等）、`2`=使い方/入力不正（プレースホルダ不足・不正な `--set`・空コマンドの保存等）。`run` の実行失敗時は**子プロセスの終了コードをそのまま返す**。

## 4. コンポーネント（単一責務・テスト可能）

```
rcmd/
  pyproject.toml
  src/rcmd/
    __init__.py        # __version__
    errors.py          # RcmdError（単一の利用者向け例外）
    models.py          # Entry（dataclass）
    store.py           # パス解決・load/save(TOML)・CRUD（純度高め：パス注入可）
    search.py          # filter_entries（純関数）
    history.py         # シェル履歴の場所特定＆パース（純関数：内容を入力に取る）
    placeholders.py    # find_placeholders / substitute（純関数）
    cli.py             # typer 配線（IO・エラー・終了コード）
  tests/
    test_store.py test_search.py test_history.py test_placeholders.py test_cli.py
  README.md
```

- **models.py**
  - `Entry`（dataclass）: `id: str, command: str, description: str = "", tags: list[str] = [], created: str = "", source: str = "manual"`。

- **store.py**
  - `store_path() -> Path`: `$RCMD_STORE` → 無ければ XDG (`~/.config/rcmd/store.toml`) / Windows (`%APPDATA%\rcmd\store.toml`)。親ディレクトリは保存時に作成。UTF-8（BOM なし）。
  - `load(path) -> list[Entry]`: `tomllib` で読む。ファイル無し→空リスト。壊れた TOML→`RcmdError`。
  - `save(path, entries)`: 固定スキーマ専用シリアライザで `[[entry]]` を出力。文字列は TOML basic string として正しくエスケープ（`\`, `"`, 制御文字→`\n`/`\t`/`\uXXXX`）。書き込みは一時ファイル→`os.replace` でアトミックに。
  - `add(entries, command, desc, tags, source) -> Entry`（採番した id 付き）／ `get(entries, id) -> Entry|None`（前方一致での一意解決も許容：曖昧時は `RcmdError`）／ `delete(entries, id) -> bool` / `update(entries, id, **fields) -> Entry`。
  - `gen_id() -> str`: 4〜6 文字の base32 風ランダム（衝突時は再採番）。

- **search.py**
  - `filter_entries(entries, query="", tags=()) -> list[Entry]`: `query` を `command`+`description` に部分一致（小文字化）、`tags` は AND。純関数。並びは登録順（安定）。

- **history.py**
  - `default_history_path(shell) -> Path|None` / `detect_shell() -> str`（`$SHELL` basename、無ければ Windows→`powershell`、他→`bash`）。
  - `parse_history(text, shell) -> list[str]`: シェル別フォーマットを正規化（下記 §6）。
  - `read_history(shell, file, limit, unique, reverse) -> list[str]` は CLI 層で path 解決＋parse を束ねる（純粋部分は `parse_history`）。

- **placeholders.py**
  - `find_placeholders(command) -> list[str]`: `{{name}}` を**出現順・重複排除**で抽出（`name` は `[A-Za-z0-9_]+`）。
  - `substitute(command, values) -> str`: 全プレースホルダを置換。未充足があれば `RcmdError`（不足名を列挙）。`--set` の `NAME=VALUE` パースは CLI 層。

- **cli.py**（typer, `add_completion=False`）… 各コマンドを配線。`RcmdError` を `rcmd: <msg>` で stderr＋`Exit(2)`、対象なし系は `Exit(1)`。`run` は確定コマンドを `subprocess.run` し戻り値を伝播。日本語ヘルプ。`store_path()` は `$RCMD_STORE` 経由でテストから差し替え。

## 5. データモデル / store.toml

```toml
[[entry]]
id = "k3f9"
command = "docker run --rm -it -v {{path}}:/work {{image}} bash"
description = "任意イメージで作業ディレクトリをマウントして対話シェル"
tags = ["docker", "dev"]
created = "2026-06-20T10:30:00"
source = "manual"           # manual | history:bash | history:zsh | history:powershell ...

[[entry]]
id = "a1b2"
command = "git log --oneline --graph --decorate --all"
description = "全ブランチのコミットグラフ"
tags = ["git"]
created = "2026-06-20T10:32:00"
source = "history:zsh"
```

`created` は ISO-8601（ローカル時刻、秒精度）。`tags` は空配列可。`description`/`source` は省略時の既定あり。

## 6. 履歴ソース解決（クロスプラットフォーム）

| シェル | 既定パス | フォーマット → 正規化 |
|---|---|---|
| bash | `~/.bash_history` | 素の 1 行 1 コマンド（複数行コマンドは `\` 継続を結合しない＝そのまま） |
| zsh | `~/.zsh_history` | 拡張形式 `: <epoch>:<dur>;<cmd>` の `<cmd>` 部を抽出。素行も許容 |
| fish | `~/.local/share/fish/fish_history` | YAML 風 `- cmd: <cmd>` 行の `<cmd>` を抽出（`when:` は無視） |
| powershell | `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` | 素の 1 行 1 コマンド |

- `auto` は `detect_shell()` で判定。`--shell` で明示、`--file` で任意パス。
- ファイルが存在しなければ stderr に明示し終了コード 1。
- パースは「ファイル内容（文字列）→ コマンド行リスト」の純関数（`parse_history`）として実装し、各フォーマットを単体テスト。

## 7. エラー処理

| 箇所 | 方針 |
|------|------|
| 空コマンドの保存 / 不正な `--set`（`=` 無し）/ プレースホルダ不足 | `RcmdError` を stderr、終了コード 2。 |
| 検索 0 件 / 存在しない ID / 履歴ファイル無し | stderr に明示、終了コード 1。 |
| 曖昧な ID 前方一致（複数該当） | 候補を列挙して `RcmdError`、終了コード 2。 |
| 壊れた `store.toml` | `RcmdError`（手編集ミスを示唆）、終了コード 2。書き込みはアトミック置換で破損を防ぐ。 |
| `run` の子プロセス失敗 | 子の終了コードをそのまま伝播。 |

## 8. テスト戦略（TDD・rcaudit 並みの密度 ~40+）

- **store**: TOML round-trip（特殊文字＝引用符・バックスラッシュ・改行・日本語・`{{}}` を含むコマンドが `save→tomllib.load` で完全一致）、`add`/`get`（完全＆前方一致＆曖昧）/`delete`/`update`、`gen_id` の形式、`store_path` の env/OS 分岐、空ファイル→空リスト、壊れ TOML→`RcmdError`、アトミック書き込み。
- **search**: query 部分一致（大小無視・command と description 双方）、tags AND、複合、0 件、安定順序。
- **history**: bash/zsh（拡張＆素）/fish/powershell 各フォーマットのパース、`--unique`（出現順保持）/`--reverse`/`--limit`、`detect_shell` の env/OS 分岐。
- **placeholders**: `find_placeholders`（出現順・重複排除・記号境界）、`substitute`（全置換・未充足で不足名列挙の `RcmdError`・プレースホルダ無しはそのまま）。
- **cli**: `CliRunner` ＋ 一時 `RCMD_STORE`。`save`（引数 / stdin）、`search`/`list`（行 /`--json`/0 件=1）、`show`、`get`（`--set` 差込）、`run --dry-run`、`edit`、`rm`（存在しない=1）、終了コード（2/1/0）、空コマンド=2。

## 9. 技術スタック

Python 3.11+ / uv / typer / pytest。**実行時依存は typer のみ**（保存は stdlib `tomllib`＋自前シリアライザ、履歴/プレースホルダ/検索は stdlib）。ネットワーク不要・ローカル完結・クロスプラットフォーム（Windows/macOS/Linux）。ビルドは hatchling、`[project.scripts] rcmd = "rcmd.cli:app"`、pytest `pythonpath=["src"]`、`testpaths=["tests"]`。

## 10. 実装マイルストーン（計画フェーズ入力）

1. 足場（pyproject, パッケージ, `uv sync`）
2. `models.py` ＋ `errors.py`
3. `store.py`（TOML round-trip・CRUD・パス解決）TDD
4. `placeholders.py` TDD
5. `search.py` TDD
6. `history.py`（各シェル形式パース・パス解決）TDD
7. `cli.py`（typer 配線・終了コード）＋ スモーク
8. README ＋ 実機検証（`rcmd save`／`history`／`search`／`get`／`run` を実 Windows で実行）

## 11. 既知の割り切り

- v1 は**非対話**。対話選択は fzf へ委譲（`rcmd search … | fzf | xargs -I{} rcmd get {}` 等を README に例示）。組込み TUI は将来。
- 自前 TOML シリアライザは**固定スキーマ専用**（任意 TOML を書かない）。round-trip テストで担保し、想定外の型は持ち込まない。
- 履歴パースは「行＝1 コマンド」を基本とし、複数行にまたがる複雑なヒアドキュメント等の完全復元は狙わない（実用上の大多数＝1 行コマンドに最適化）。
- `run` は保存済みコマンドを実行する＝**ユーザーが自分で保存したものを自己責任で実行**。安全側の既定として `get`/`--dry-run`（表示のみ）を併設。
