# AI Workbench

A Claude Code **skill** that builds a cohesive matrix-green / cyber-purple developer
environment on Linux — one shared color palette across your prompt, terminal, editor,
system monitor, and diffs, instead of eleven mismatched default themes.

> Formerly `cyberdeck-setup`. Renamed throughout — GitHub repo, skill folder,
> `SKILL.md`'s internal name, and every asset filename/identifier.

Everything installs to `~/.local`. No `sudo`, no `apt`, no `snap` — every tool is
fetched as a portable binary/tarball from its own GitHub releases page, so this works
identically whether or not you have root on the machine.

## What it sets up

| Component | What you get |
|---|---|
| VS Code | Portable install + desktop launcher |
| Starship | Two-line prompt: directory, git branch/status, language runtimes, conda, cmd duration |
| Nerd Font | Correctly-metriced (readable) icon font — the naive "Mono" patch variant is broken in VTE terminals, this skill knows to avoid it |
| Terminal palette | Full 16-color ANSI theme (Ptyxis: automated; other terminals: palette file + manual pointer) |
| Claude Code status line | Themed status line inside Claude Code itself |
| eza / bat / fzf / zoxide | Modern `ls`/`cat`/history-search/`cd` replacements |
| git delta | Side-by-side, syntax-highlighted diffs in the same palette |
| zellij | Themed terminal multiplexer |
| btop | Themed system monitor |
| bash aliases | Git/Docker/Python/Node/nav shortcuts + a `dh` command that prints all of them |
| GitHub CLI | Installed and ready for you to run `gh auth login` (this one step stays manual, on purpose) |
| Claude Code plugins | Optional: `mattpocock-skills`, `daily.dev`, `ponytail`, `caveman`, `humanizer` — pick any subset |
| T3 Code | Optional: [t3.codes](https://t3.codes) as a background service on your tailnet, so your phone can run Claude sessions on this box. Telemetry off, Claude as default, no extra sign-ins |
| `ai-workbench-doctor` | Always installed — a `doctor` command that reports what's actually configured vs missing |

## Screenshot

![Claude Code with the ai-workbench status line](docs/screenshots/claude-code-statusline.png)

Themed status line: directory, git branch, model, context-usage bar, and the
Claude.ai 5-hour rate-limit bar — all in the matrix-green / cyber-purple palette.

![T3 Code running a Claude session in home-list](docs/screenshots/t3-code.jpg)

T3 Code driving Claude Code on the same box, with the global `CLAUDE.md` and skills loaded.

## Using it

This is a Claude Code skill, not a shell script — you run it *through* Claude Code so
it can detect your specific environment (terminal emulator, architecture, what's
already installed) and ask what you actually want before touching anything.

1. Copy `.claude/skills/ai-workbench/` into your own project's `.claude/skills/`
   directory (or your global `~/.claude/skills/`).
2. In Claude Code, ask it to set up the ai-workbench environment (or invoke the skill by
   name if your setup supports that).
3. Claude will detect your environment, ask which pieces you want, and walk through
   the runbook in `SKILL.md` — installing only what you selected, verifying each step,
   and never overwriting existing dotfile content without asking first.

## Why a skill and not a script

A shell script either overwrites your existing `~/.bashrc`/`~/.gitconfig` or gets
complicated fast trying not to. A Claude Code skill can actually *read* your existing
config first, detect which terminal you're running, adapt the handful of
terminal-specific steps (font/palette wiring) to what it finds, and explain what it's
about to do at each step — which is what this setup actually needs, since half the
components here (Ptyxis palette wiring, Nerd Font variant selection) have sharp edges
that a fixed script can't safely special-case for every environment.

## Structure

```
.claude/skills/ai-workbench/
├── SKILL.md              # the runbook Claude follows
└── assets/                # tested, ready-to-copy config templates
    ├── starship.toml
    ├── bash_aliases
    ├── statusline.sh
    ├── ai-workbench.theme        # btop
    ├── zellij-config.kdl
    ├── AI-Workbench.palette      # Ptyxis 16-color palette
    ├── gitconfig-delta.txt
    └── ai-workbench-doctor         # status-check command, installed unconditionally
```

## Known gotchas

See the **Known gotchas** section at the bottom of `SKILL.md` — it documents real bugs
hit while building this (a Nerd Font variant that breaks letter-spacing in VTE
terminals, PUA glyphs that can silently vanish when written by an LLM, GTK's
per-pane font caching) so they don't get rediscovered by every contributor.

## Contributing

Additional terminal emulators (Alacritty, kitty, Konsole, WezTerm) for the automated
palette-wiring step, a zsh variant, and additional themed tools are all welcome —
follow the existing pattern in `SKILL.md`: detect, ask, install to `~/.local`, verify,
report. PRs that add a new tool should ship a corresponding `assets/` template rather
than having Claude regenerate the config from a text description each time.

## See also

[macify](https://github.com/abhibansal60/macify) — makes Ubuntu GNOME look like
macOS (WhiteSur theme, dock, login screen). A separate concern on purpose: it
needs `sudo` and touches system files, breaking this repo's rootless promise.

## License

MIT — see `LICENSE`.
