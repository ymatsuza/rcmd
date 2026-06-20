# rcmd

Personal command knowledge base for the CLI. Import raw shell history, annotate
commands with descriptions and tags, search them, and recall (print or run) with
`{{placeholder}}` substitution. Local-only, single human-editable TOML file,
cross-platform (Windows / macOS / Linux). Dependency: `typer` only.

rcmd does not compete with `atuin`/`fzf`/`hstr` (which *search* live history) — it
*curates* the commands worth keeping.

## Install

```bash
uv sync
uv run rcmd --help
```

## Usage

```bash
# Save a command (or pipe from stdin)
rcmd save "docker run --rm -it -v {{path}}:/work {{image}} bash" -d "mount cwd, interactive shell" -t docker -t dev

# Bridge from raw shell history -> pick with fzf -> save
rcmd history --unique --reverse | fzf | rcmd save -d "describe me" -t imported

# Search / list (line output is fzf-friendly)
rcmd search docker
rcmd list -t git

# Inspect one entry (the "man page" view)
rcmd show k3f9

# Recall: print only (compose with $() or a clipboard tool)
rcmd get k3f9 --set path=$PWD --set image=alpine
rcmd get k3f9 --set path=. --set image=alpine | clip      # Windows
rcmd get k3f9 --set path=. --set image=alpine | pbcopy    # macOS

# Recall: run it (or --dry-run to preview)
rcmd run k3f9 --set path=. --set image=alpine
rcmd run k3f9 --set path=. --set image=alpine --dry-run

# Edit / remove
rcmd edit k3f9 -d "new description" -t docker
rcmd rm k3f9
```

## Store location

`$RCMD_STORE`, else `~/.config/rcmd/store.toml` (XDG) or
`%APPDATA%\rcmd\store.toml` (Windows). It is plain TOML — hand-edit and sync it
with your dotfiles.

## Exit codes

`0` success · `1` nothing found (empty search / missing id / no history file) ·
`2` usage error (empty command, bad `--set`, missing placeholder, ambiguous id,
corrupt store). `run` propagates the child process's exit code.
