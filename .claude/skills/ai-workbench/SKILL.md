---
name: ai-workbench
description: Sets up a matrix-green / cyber-purple "AI Workbench" developer environment on Linux — Starship prompt, a correctly-metriced Nerd Font, a matching 16-color terminal palette, a Claude Code status line and optional 75% usage hard stop, modern CLI tools (eza, bat, fzf, zoxide), git delta, zellij, btop, and bash aliases with a `dh` help command, plus optional Claude Code plugins and T3 Code (a phone-friendly web UI for Claude sessions). Use when the user asks to set up, theme, or customize their terminal/shell/dev environment on Linux, or wants an "AI Workbench" or similarly-themed dev machine.
---

# AI Workbench

Builds a cohesive, matrix-green/cyber-purple terminal environment across every tool a
Linux developer touches daily — one shared palette, not eleven mismatched ones.

This skill was reverse-engineered from a real end-to-end session, including the bugs
hit along the way. Follow it as a runbook, not a suggestion list — several steps exist
specifically because the naive approach silently breaks (see **Known gotchas** below).

## Ground rules

- **Linux + bash only.** If `uname -s` isn't `Linux`, or the user's shell isn't bash
  (check `$SHELL`), stop and tell the user this skill doesn't cover their setup yet.
- **Never run `sudo` yourself.** This environment usually has no interactive TTY for a
  password prompt, and even when it does, silently escalating is not this skill's call
  to make. Every install in this skill uses a **no-sudo, user-local** pattern
  (`~/.local/bin`, `~/.local/share/fonts`, tarball/binary downloads) specifically so
  root is never required. If a step genuinely needs `apt`/`dnf`/etc., say so and hand
  the user the exact command — don't run it for them.
- **Idempotent and non-destructive.** Before writing to a dotfile that might already
  have user content (`~/.bashrc`, `~/.bash_aliases`, `~/.gitconfig`), read it first.
  Never blind-overwrite. Append with a clear marker comment, or merge structured files
  (JSON/TOML) programmatically instead of clobbering.
- **Verify every step**, don't just assume success. Run `--version`, config-validate
  commands (`starship print-config`, `zellij setup --check`, `bash -n file`), and where
  possible a live smoke test with sample input. A step isn't done until you've checked.
- **Ask before you build**, per Step 1 below — don't install things nobody asked for.

## Step 0 — Detect the environment

Gather this before doing anything else:

```bash
uname -s                      # must be Linux
uname -m                      # x86_64 / aarch64 / etc. — determines which release asset to fetch
echo "$SHELL"                 # must be bash (or /bin/bash)
sudo -n true 2>&1             # passwordless sudo available? (informational only — never rely on it)
command -v starship eza bat fzf zoxide delta zellij btop code t3 tailscale 2>&1  # what's already installed
command -v curl git unzip python3 jq node claude 2>&1   # prerequisites, see below
```

**Prerequisites.** A fresh Ubuntu desktop can lack `curl` and `git`, and usually lacks
`jq` and `node`. Handle each before Step 1:

- `curl`, `git`: these need apt, so hand the user `sudo apt install -y curl git` and
  wait for them to confirm it's done.
- `unzip`: only the Nerd Font step uses it. Without it, extract with
  `python3 -m zipfile -e <zip> <dir>`.
- `jq`: the status line and the usage hard stop parse their JSON with it, and render
  nothing without it. Install the static binary, no sudo:
  ```bash
  a=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  mkdir -p ~/.local/bin
  curl -fsSL "https://github.com/jqlang/jq/releases/latest/download/jq-linux-$a" -o ~/.local/bin/jq
  chmod +x ~/.local/bin/jq && jq --version
  ```
- `node`: optional. Only the status line's session-token segment uses it, and that
  segment is skipped without it. Mention it; don't install it unasked.
- `claude`: the status line, plugins and T3 Code all need Claude Code. If it's missing,
  install it with `curl -fsSL https://claude.ai/install.sh | bash` (user-local, no
  sudo) and tell the user to run `claude` once to sign in.

This step is done when `command -v curl git jq` prints all three paths.

**Terminal emulator detection** (determines whether the palette/font steps in Step 2
can be automated or need manual instructions):

```bash
# Walk up the process tree looking for a known terminal emulator name
ps -o comm= -p $PPID 2>/dev/null
# Common values to match on: gnome-terminal-, ptyxis, konsole, xfce4-terminal,
# alacritty, kitty, wezterm, xterm, tilix
```

Also check for terminal-specific config surfaces:
```bash
which ptyxis 2>/dev/null && gsettings list-schemas 2>/dev/null | grep -q "^org.gnome.Ptyxis$" && echo "ptyxis: gsettings-controllable"
which gnome-terminal 2>/dev/null && echo "gnome-terminal: dconf-controllable"
```

This skill has fully automated palette + font wiring for **Ptyxis** (GNOME's modern
VTE-based terminal). For any other terminal, still install the font and write the
palette file, but tell the user how to point their terminal at it manually (see the
per-terminal notes inside Step 2's palette section) rather than guessing at that
terminal's config format.

## Step 1 — Ask what to install

Use `AskUserQuestion` (multiSelect) with one line per component, e.g.:

- **VS Code** — installed as a portable user-local build, with a desktop launcher (no sudo/snap/apt needed)
- **Starship prompt** — matrix-green/cyber-purple two-line prompt (git, language runtimes, cmd duration)
- **Nerd Font + terminal font fix** — required for the icons Starship/btop/etc. use
- **Terminal color palette** — 16-color ANSI theme so `ls`, `man`, `less`, everything matches (Ptyxis only, automated)
- **Claude Code status line** — themed status line inside Claude Code itself: context,
  5h and 7-day limit bars, session token totals
- **Usage hard stop** — optional: a hook that stops every Claude tool call once the
  5-hour subscription limit reaches 75%, so a long run can't burn the whole window
- **Modern CLI tools** — eza, bat, fzf, zoxide
- **git delta** — themed side-by-side diffs
- **zellij** — themed terminal multiplexer
- **btop** — themed system monitor
- **bash aliases + `dh` help command** — dev shortcuts (git, docker, npm, etc.) plus a colorized help listing
- **GitHub CLI (`gh`)** — installed and ready for the user to authenticate
- **Claude Code plugins** — optional, pick any subset (see **Claude Code plugins**
  below for what each one does): `mattpocock-skills`, `daily.dev`, `ponytail`,
  `caveman`, `humanizer`
- **Tailscale** — optional hand-off: private network so a phone can reach this box.
  Needs root, so the skill checks it and gives you the commands instead of running them
- **T3 Code** — optional: a self-hosted web/mobile UI (t3.codes) that runs Claude Code
  sessions on this box as a background service, so you can drive them from a phone

`ai-workbench-doctor` (see its own section near the end of Step 2) is **not** one of
these choices — it's installed unconditionally at the end, since it's the tool for
checking the state of everything else, including pieces the user chose to skip.

Don't install anything the user didn't select. Each is independent — none depend on
another except that most of them look better once the font step has run.

## Step 2 — Install each selected component

For every binary in this section: **resolve the latest release for the detected
architecture via the GitHub API**, don't hardcode a version or a single-arch URL.
Pattern:

```bash
curl -sSL "https://api.github.com/repos/<owner>/<repo>/releases/latest" \
  | grep -o '"browser_download_url": *"[^"]*<ASSET_PATTERN>"' \
  | head -1 | cut -d'"' -f4
```

Where `<ASSET_PATTERN>` matches the detected `uname -m` (e.g. `x86_64-unknown-linux-gnu`,
`aarch64-unknown-linux-musl` — check each project's actual release asset names, they
aren't consistent). Download to a scratch dir, extract, `cp` the binary into
`~/.local/bin/`, `chmod +x`. Confirm `~/.local/bin` is on `$PATH` in `~/.bashrc`
(add `export PATH="$HOME/.local/bin:$PATH"` once, guarded by a grep-check so it's
never duplicated on a re-run).

### VS Code

Install as a portable tarball — no root, no snap, no apt:

```bash
curl -sSL "https://code.visualstudio.com/sha/download?build=stable&os=linux-x64" -o /tmp/vscode.tar.gz
mkdir -p ~/.local/share/vscode
tar -xzf /tmp/vscode.tar.gz -C ~/.local/share/vscode --strip-components=1
ln -sf ~/.local/share/vscode/bin/code ~/.local/bin/code
```
(For non-x64, VS Code's download endpoint also accepts `os=linux-arm64`/`linux-armhf`.)

Add a desktop launcher so it appears in the app grid, not just the terminal:
```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/code.desktop << EOF
[Desktop Entry]
Name=Visual Studio Code
Comment=Code Editing. Redefined.
Exec=$HOME/.local/share/vscode/bin/code %F
Icon=$HOME/.local/share/vscode/resources/app/resources/linux/code.png
Type=Application
StartupNotify=true
StartupWMClass=Code
Categories=Utility;TextEditor;Development;IDE;
MimeType=text/plain;inode/directory;application/x-code-workspace;
EOF
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

Verify: `code --version` (this works headlessly; actually launching the GUI needs a
display, so `--version` is the practical check here).

### Starship prompt

```bash
curl -sSL https://starship.rs/install.sh -o /tmp/install_starship.sh
BIN_DIR=~/.local/bin sh /tmp/install_starship.sh -y
```

Copy `assets/starship.toml` to `~/.config/starship.toml` (create `~/.config` if
missing). If a starship.toml already exists there, ask the user before overwriting —
offer to back it up to `starship.toml.bak` first.

Add to `~/.bashrc` (only if not already present — grep for `starship init` first):
```bash
eval "$(starship init bash)"
```

Validate: `starship print-config >/dev/null && echo OK`.

### Nerd Font + terminal font fix

**Use the plain `NerdFont` build, never the `NerdFontMono` build.** The "Mono" patch
forces *every* glyph — including plain ASCII — into an oversized fixed-width cell to
keep icons aligned, which produces badly-spread letter-spacing in VTE-based terminals
(GNOME Terminal, Ptyxis). This is a real, reported upstream issue
(ryanoasis/nerd-fonts#1511) affecting multiple font families, not a one-off bug in a
specific font. The plain variant keeps the base font's real metrics.

```bash
mkdir -p ~/.local/share/fonts
curl -sSL -o /tmp/JetBrainsMono.zip \
  "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip"
unzip -o -q /tmp/JetBrainsMono.zip -d /tmp/JetBrainsMonoNF
mkdir -p ~/.local/share/fonts/JetBrainsMonoNerdFont
cp /tmp/JetBrainsMonoNF/JetBrainsMonoNerdFont-*.ttf ~/.local/share/fonts/JetBrainsMonoNerdFont/
fc-cache -f ~/.local/share/fonts
```

Verify it registered correctly: `fc-match "JetBrainsMono Nerd Font"` should resolve to
one of the files you just copied, and `fc-query --format='%{spacing}\n' <file>` should
print `100` (monospace).

**Wiring the terminal to actually use it:**

- **Ptyxis:**
  ```bash
  gsettings set org.gnome.Ptyxis use-system-font false
  gsettings set org.gnome.Ptyxis font-name 'JetBrainsMono Nerd Font 11'
  ```
- **GNOME Terminal:** set the font on the relevant profile UUID under
  `org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:<uuid>/`.
- **Other terminals (Konsole, Alacritty, kitty, xterm, etc.):** don't guess at the
  config file. Tell the user the exact font name (`JetBrainsMono Nerd Font`) and point
  them at that terminal's font preference — every terminal exposes this differently.

**Important:** font changes only apply to *new* panes/windows/tabs — GTK terminals in
particular cache the font at pane-creation time. Always tell the user to open a new
tab (not reuse the current one) to see the change, and warn that a genuinely stuck
pane may need the whole app restarted, not just a new tab.

### Terminal color palette (Ptyxis-automated; other terminals: manual)

Ptyxis ships dozens of bundled palettes as GResources and supports user palettes
dropped into a specific directory, referenced by profile:

```bash
mkdir -p ~/.local/share/org.gnome.Ptyxis/palettes
cp assets/AI-Workbench.palette ~/.local/share/org.gnome.Ptyxis/palettes/AI-Workbench.palette

UUID=$(gsettings get org.gnome.Ptyxis default-profile-uuid | tr -d "'")
gsettings set "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/Profiles/$UUID/" palette 'AI Workbench'
```

(`ptyxis --import-palette FILE` also works if the file isn't already at that exact
path — but don't call it if you just wrote the file there yourself, it'll error
claiming the file already exists.)

For any other terminal, still write `assets/AI-Workbench.palette` somewhere durable
(e.g. `~/.config/ai-workbench/AI-Workbench.palette`) and tell the user it's a standard
16-color-plus-bg/fg/cursor palette they can translate into their terminal's own format
(most terminals — kitty, Alacritty, Konsole — have a "import palette"/theme mechanism,
just not a shared file format).

### Claude Code status line

Check `~/.claude/settings.json` first — read it, don't overwrite it. If a `statusLine`
key already exists, ask the user before replacing it.

Needs `jq` (see **Prerequisites**).

```bash
cp assets/statusline.sh ~/.claude/statusline.sh
cp assets/statusline-tokens.mjs ~/.claude/statusline-tokens.mjs
```

Renders `dir on Ψ branch │ model │ ctx ▓▓▓▓▓░░░░░ 48% │ 5h ▓▓░░░░░░░░ 20% resets 14:30 │ 7d ▓░░░░░░░░░ 13% │ in 12.3M 97% cached  out 85k`.
Bars go amber at 70% and red at 90%. Each segment appears only when its data exists:
the 5h and 7d bars when the payload has `.rate_limits`, the token totals when `node`
is installed.

Merge (don't overwrite) the settings file, preserving every other key:

```bash
python3 - <<'EOF'
import json, os
path = os.path.expanduser("~/.claude/settings.json")
data = json.load(open(path)) if os.path.exists(path) else {}
data["statusLine"] = {"type": "command", "command": 'bash "$HOME/.claude/statusline.sh"', "refreshInterval": 10}
json.dump(data, open(path, "w"), indent=2)
EOF
```

Verify with a mock payload that exercises every bar:
```bash
echo '{"model":{"display_name":"Claude Opus 5.5"},"workspace":{"current_dir":"'$HOME'"},"context_window":{"used_percentage":34},"rate_limits":{"five_hour":{"used_percentage":20},"seven_day":{"used_percentage":13}}}' \
  | bash ~/.claude/statusline.sh
```
Done when the output shows a colored ctx, 5h and 7d bar on one line.

### Usage hard stop (optional)

A `PreToolUse` hook that denies every tool call once the 5-hour limit reaches 75%, and
tells Claude to stop and report what's done and what's left. The status line writes
the current percentage to `~/.claude/usage-5h.txt` while the hook is installed, and the
hook ignores readings older than 10 minutes. So it only works with the status line
installed and a terminal Claude session running. Override for one stretch with
`touch ~/.claude/usage-stop-off`.

```bash
mkdir -p ~/.claude/hooks
cp assets/usage-stop.sh ~/.claude/hooks/usage-stop.sh
python3 - <<'EOF'
import json, os
path = os.path.expanduser("~/.claude/settings.json")
data = json.load(open(path)) if os.path.exists(path) else {}
pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
cmd = 'bash "$HOME/.claude/hooks/usage-stop.sh"'
if not any(h.get("command") == cmd for g in pre for h in g.get("hooks", [])):
    pre.append({"matcher": "*", "hooks": [{"type": "command", "command": cmd, "timeout": 5}]})
json.dump(data, open(path, "w"), indent=2)
EOF
```

Verify both paths:
```bash
echo "80 $(date +%s)" > ~/.claude/usage-5h.txt && bash ~/.claude/hooks/usage-stop.sh   # prints a deny JSON
echo "10 $(date +%s)" > ~/.claude/usage-5h.txt && bash ~/.claude/hooks/usage-stop.sh   # prints nothing
```

### Modern CLI tools — eza, bat, fzf, zoxide

Resolve + install each via the GitHub-releases pattern above. Asset name fragments to
match (adjust for detected arch):
- eza: `eza-community/eza`, asset `eza_<arch>-unknown-linux-gnu.tar.gz`
- bat: `sharkdp/bat`, asset `bat-v*-<arch>-unknown-linux-gnu.tar.gz` (binary is nested
  one directory deep inside the tarball)
- fzf: `junegunn/fzf`, asset `fzf-*-linux_<goarch>.tar.gz` (`amd64`/`arm64`, not
  `x86_64`/`aarch64` — fzf uses Go arch naming)
- zoxide: `ajeetdsouza/zoxide`, asset `zoxide-*-<arch>-unknown-linux-musl.tar.gz`

Add to `~/.bashrc` (guarded against duplication):
```bash
eval "$(fzf --bash)"
eval "$(zoxide init bash)"
```

### git delta

Install `dandavison/delta`, asset `delta-*-<arch>-unknown-linux-gnu.tar.gz`.

Don't overwrite `~/.gitconfig` wholesale — the user may already have `[user]` identity
or other sections in it. Instead, apply each key with `git config --global`:
```bash
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
git config --global delta.navigate true
git config --global delta.line-numbers true
git config --global delta.side-by-side true
git config --global delta.syntax-theme Dracula
git config --global delta.file-style '"#9d4bff" bold'
git config --global delta.file-decoration-style '"#7d5bed" ul'
git config --global delta.hunk-header-style "file line-number syntax"
git config --global delta.hunk-header-decoration-style '"#00fff9" box'
git config --global delta.line-numbers-left-color '"#5c5c6e"'
git config --global delta.line-numbers-right-color '"#5c5c6e"'
git config --global delta.line-numbers-minus-color '"#ff003c"'
git config --global delta.line-numbers-plus-color '"#39ff14"'
git config --global delta.minus-style 'syntax "#2d0a14"'
git config --global delta.minus-emph-style 'syntax "#5c1428"'
git config --global delta.plus-style 'syntax "#0d2818"'
git config --global delta.plus-emph-style 'syntax "#145c34"'
git config --global merge.conflictstyle diff3
git config --global diff.colorMoved default
```
(`assets/gitconfig-delta.txt` has the same values in raw `.gitconfig` block form, for
reference or for a user with no existing `~/.gitconfig` at all — safe to use directly
as the whole file only in that empty case.)

Verify: pipe a real diff through delta directly (piped commands bypass `core.pager`,
so testing via `git diff` alone won't actually invoke it):
```bash
git diff --color=always <file> | delta --paging never
```

### zellij

Install `zellij-org/zellij`, asset `zellij-<arch>-unknown-linux-musl.tar.gz`.

```bash
mkdir -p ~/.config/zellij
cp assets/zellij-config.kdl ~/.config/zellij/config.kdl   # ask before overwriting if one exists
zellij setup --check   # must print "[CONFIG FILE]: Well defined."
```

### btop

Install `aristocratos/btop`, asset `btop-<arch>-unknown-linux-musl.tar.gz` (binary is
at `btop/bin/btop` inside the tarball). Bundle also ships a `themes/` dir — ignore it,
we provide our own.

```bash
mkdir -p ~/.config/btop/themes
cp assets/ai-workbench.theme ~/.config/btop/themes/ai-workbench.theme
if [ ! -f ~/.config/btop/btop.conf ]; then
  btop --default-config > ~/.config/btop/btop.conf
fi
# then set (don't blind-overwrite the whole conf if it already existed):
sed -i 's/^color_theme = .*/color_theme = "ai-workbench"/' ~/.config/btop/btop.conf
```

Validate the theme file structurally (btop needs a real TTY to run, so this is the
practical verification): every line should match `theme[a-z_]+="#[0-9a-fA-F]{6}"`.

Optional: alias `top`/`htop` to `btop` in the bash aliases step below.

### bash aliases + `dh` help command

`assets/bash_aliases` is a complete, ready-to-use file (Claude Code and Codex aliases, git,
docker, python/conda, node, navigation, the modern-CLI-tools aliases, zellij, system/
network, utility functions, and the `devhelp`/`dh` function that prints all of it in
the ai-workbench palette).

If `~/.bash_aliases` doesn't exist, copy it directly. If it does, **read it first** —
either merge in only the sections/aliases the user doesn't already have, or append the
whole file under a clearly marked `# --- ai-workbench additions ---` block, and
flag any alias name collisions to the user instead of silently overriding them.

Ensure `~/.bashrc` sources it (standard Debian/Ubuntu bashrc already has this — check
before adding):
```bash
grep -q 'bash_aliases' ~/.bashrc || cat >> ~/.bashrc << 'EOF'
if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi
EOF
```

Validate: `bash -n ~/.bash_aliases`, then a live check that `dh` resolves and runs
without error in an interactive shell.

### GitHub CLI (`gh`)

Install like every other tool here — `cli/cli`, asset `gh_*_linux_<goarch>.tar.gz`
(`amd64`/`arm64`; the binary is nested one directory deep, at `bin/gh` inside the
extracted folder).

**Authentication is the one step in this whole skill that cannot be automated safely
or silently** — don't try. `gh auth login` is an interactive device-code/browser flow
by design. After installing the binary, tell the user to run it themselves:

```
gh auth login
```

(suggest `GitHub.com` → `HTTPS` → `Login with a web browser`).

If the user instead pastes a personal access token directly into the conversation,
you *can* use it — pipe it straight into `gh auth login --with-token`, which hands it
to `gh`'s own credential storage (OS keyring) without ever writing it to a file:
```bash
echo "$TOKEN" | gh auth login --with-token
```
When this happens, say so plainly: mention that pasting tokens into chat means it's
sitting in that conversation's history, and that the user may want to rotate/revoke it
on GitHub afterward if that matters to them. Never `echo`, log, write to a file
(including this skill's own asset files), or otherwise persist the raw token anywhere
outside that one `gh auth login` invocation.

Verify: `gh auth status` (exit 0 = authenticated).

### Claude Code plugins (optional)

Each plugin below is independent — install whichever subset the user picked in
Step 1, skip the rest. Tell the user what each one *does* before they choose, don't
just list names:

- **`mattpocock-skills`** — a skill pack for engineering workflows: TDD (red-green-
  refactor), debugging/diagnosis, code review, domain modeling (`CONTEXT.md`/ADRs),
  merge-conflict resolution, prototyping. Marketplace repo: `mattpocock/skills`.
- **`daily.dev`** — pulls real-time developer articles/trends into Claude's answers,
  as a workaround for the model's training-data cutoff. Marketplace repo:
  `dailydotdev/daily`.
- **`ponytail`** — an always-on style guard that pushes every coding answer toward
  the smallest solution that actually works (YAGNI, stdlib-first, no speculative
  abstraction) instead of over-engineering. Intensity levels `lite`/`full`/`ultra`,
  toggle with `/ponytail`. Marketplace repo: `DietrichGebert/ponytail`.
- **`caveman`** — compresses Claude's own prose output (not code) into terse
  fragments to cut response tokens, while keeping technical content exact. Same
  `lite`/`full`/`ultra` levels, toggle with `/caveman`. Marketplace repo:
  `JuliusBrussee/caveman`.
- **`humanizer`** — rewrites AI-sounding prose (inflated claims, stock phrasing,
  chatbot tics) into plain natural writing, without changing what it says.
  Marketplace repo: `blader/humanizer`.

**These change how Claude Code itself behaves, globally** — unlike every other
component in this skill, there's no visual/terminal effect to preview, so lean
harder on explaining behavior than usual before the user picks.

For each plugin the user selects:
```bash
claude plugin marketplace add <owner/repo>     # e.g. DietrichGebert/ponytail
claude plugin install <plugin-name>@<marketplace-name>   # e.g. ponytail@ponytail
```
The marketplace name defaults to the repo name; check `claude plugin marketplace list`
if unsure what a given `add` registered it as. Installing enables it automatically —
this writes `enabledPlugins` and `extraKnownMarketplaces` into `~/.claude/settings.json`
itself, so don't hand-edit that file for this step.

Verify: `claude plugin list` shows the plugin, and `claude plugin details <name>`
confirms it resolved correctly.

To remove one later: `claude plugin uninstall <plugin-name>`.

### Tailscale (optional, hand-off)

Tailscale is the one component here that can't be rootless: `tailscaled` is a system
daemon and the install and `tailscale up` both need root. So the skill only checks and
hands off, like `gh auth login`. Never run `sudo`, never run `tailscale up` or log in.

```bash
command -v tailscale && tailscale version | head -1
tailscale ip -4          # empty = not installed, stopped or logged out
tailscale status | head  # the phone should be listed
```

If it's missing, give the user these to run themselves, then wait:

```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

(Read the install script first if the user wants; it's the official one.) If it's
installed but `tailscale ip -4` is empty, the fix is `sudo tailscale up` (or
`sudo systemctl start tailscaled`). Verify: `tailscale ip -4` prints a `100.x` address.
Install Tailscale on the phone and sign in to the same tailnet there; that is the
user's step too.

### T3 Code (optional)

[T3 Code](https://t3.codes) (`pingdotgg/t3code`) is a web and mobile UI for coding
agents. It runs the real `claude` binary on this box, with your `CLAUDE.md`, hooks and
skills, and lets a phone start and follow sessions. Upstream docs:
`github.com/pingdotgg/t3code/tree/main/docs/user`.

It installs to `~/.local/bin/t3` and `~/.t3`, with no sudo. **Never sign in to
anything for it**: skip `t3 connect` (T3's own cloud relay) and every provider
sign-in button. T3 reuses the `claude` (and `codex`) CLI logins that already exist on
the box. If `claude` isn't logged in, tell the user to run `claude auth login`
themselves.

Phone access goes over Tailscale (see the **Tailscale** section above). Without it,
T3 still works on this machine at `127.0.0.1`.

Ask before each piece below. Each one changes something that outlives the session.

1. **Install.** Download the installer and read it before running it. It should
   only fetch a GitHub release, check its sha256, unpack it under
   `~/.t3/runtime/versions/` and link `~/.local/bin/t3`:
   ```bash
   curl -fsSL https://t3.codes/install.sh -o /tmp/t3-install.sh
   less /tmp/t3-install.sh        # read it; stop if it does anything else
   sh /tmp/t3-install.sh
   t3 --version
   ```
2. **Background service.** This writes a systemd user unit
   (`~/.config/systemd/user/t3code.service`) and enables lingering so T3 survives
   logout. If lingering needs root, T3 prints a `sudo loginctl enable-linger` command;
   hand it to the user, don't run it.
   ```bash
   t3 service install
   t3 service status
   ```
3. **Telemetry off and bind address**, as systemd drop-ins. Don't edit the unit
   itself, because `t3 update` and `t3 service install` rewrite it. Bind to the
   tailnet IP when `tailscale ip -4` returns one, so the phone can reach T3 over the
   tailnet. Otherwise use `127.0.0.1`. Never bind to `0.0.0.0`.
   ```bash
   d=~/.config/systemd/user/t3code.service.d
   mkdir -p "$d"
   ls "$d"                        # read any existing drop-ins before writing
   printf '[Service]\nEnvironment=T3CODE_TELEMETRY_ENABLED=false\n' > "$d/telemetry.conf"
   host=$(tailscale ip -4 2>/dev/null | head -1); host=${host:-127.0.0.1}
   printf '[Service]\nEnvironment=T3CODE_HOST=%s\n' "$host" > "$d/tailnet.conf"
   systemctl --user daemon-reload && systemctl --user restart t3code.service
   cat ~/.t3/userdata/server-runtime.json   # "host" must match, port is 3773
   ```
   This is plain HTTP inside the tailnet. If Tailscale Serve (HTTPS) is enabled on
   the tailnet, `t3 pair --tailscale` publishes T3 over HTTPS instead.
4. **Projects.** Add each repo the user works in. Ask which ones; for a `~/code`
   layout, offer all of its git repos:
   ```bash
   for r in ~/code/*/.git; do t3 project add "${r%/.git}"; done
   ```
5. **Claude as default provider.** Open T3 in a browser (the `origin` in
   `server-runtime.json`). In **Settings**, have the user pick a Claude model as
   the default. The user chooses the model, not you. This writes
   `defaultModelSelection.instanceId = "claudeAgent"` to `~/.t3/userdata/settings.json`.
   Turn off providers whose CLI isn't installed, or that T3 flags as an unsupported
   version, in **Settings → Providers**.
6. **Pair the phone.** Install the T3 Code app (App Store or Google Play) and join
   the phone to the same tailnet. Then mint a short-lived link and show the QR code
   and URL:
   ```bash
   t3 pair --label phone --ttl 30m
   ```
   Treat the pairing URL like a password. Don't paste it into commits, logs or
   screenshots.

Verify: `t3 --version`, `t3 service status`, the `host` in `server-runtime.json`, and
`ai-workbench-doctor`'s T3 section. Update later with `t3 update`. Remove with
`t3 uninstall` (projects and threads in `~/.t3/userdata` are kept).

**Known gaps.** The Claude Code status line and dev mods don't render in T3; they are
terminal-only. A hook that depends on status-line data (for example `usage-stop.sh`
reading cached rate-limit numbers) only stays fresh while a terminal Claude session
runs alongside T3.

### `ai-workbench-doctor` (always installed, regardless of Step 1 selections)

Copy `assets/ai-workbench-doctor` to `~/.local/bin/ai-workbench-doctor` and `chmod +x` it.
It's a standalone, read-only status script — running it makes no changes, so it's safe
to install and run even for components the user chose not to set up (they'll just show
as missing, which is correct and useful information, not an error).

It checks, per component: is the binary on `$PATH` (and its `--version`), is the
relevant config file present, and — where it's cheap to check — whether that config
file actually reflects the ai-workbench theme rather than just existing. It also
specifically flags if the broken `NerdFontMono` variant is present (see **Known
gotchas**), since that's a silent trap otherwise. It's already aliased as `doctor` in
`assets/bash_aliases`.

Two things worth knowing if you extend `ai-workbench-doctor` for a new component:
- Any `$(...)` output you show the user should be passed through the script's
  `strip_ansi` helper first — several tools (`btop --version`, some `delta` builds)
  embed their own ANSI color codes in `--version` output, which garbles the doctor
  script's own coloring if piped straight through unstripped.
- Match family/theme names precisely enough to avoid false positives. e.g. checking
  `fc-list | grep "JetBrainsMono Nerd Font"` alone would also match the broken `...Nerd
  Font Mono` family as a substring — anchor on the delimiter that follows the name in
  that tool's actual output (here, a trailing `,` or `:`) instead.

## Step 3 — Final verification pass

Before reporting done, actually re-check everything, don't just trust each step's own
"it worked" — mirror what a human would do:
- `bash -n` every shell file touched
- `--version`/`--check`/`print-config` on every tool with a validation flag
- At least one live rendered sample per visual component (a mock starship prompt via
  `starship prompt --status=0`, a mock statusline payload, a real diff through delta)
- Confirm nothing in `~/.bashrc`/`~/.bash_aliases`/`~/.gitconfig` got duplicated if this
  skill is being re-run on a machine it already touched
- Finish with `ai-workbench-doctor` itself and read its output — it's the single source
  of truth for what actually landed vs what silently didn't

## Step 4 — Report back

Tell the user plainly:
- What was installed and where (paths matter — these are all user-local, nothing
  touched `/usr` or needed root)
- What requires a new terminal tab/window (or full app restart) to actually show up
- What was terminal-specific and either automated or left as manual instructions
- Run `dh` for the full alias/shortcut reference, `doctor` any time to re-check status

## Known gotchas (read before debugging from scratch)

- **`NerdFontMono` vs `NerdFont`**: the "Mono" patch variant is the one with the
  spacing bug. Always use the plain variant.
- **Private-Use-Area glyphs can silently vanish** when an LLM types them directly into
  a generated config file — some pipelines drop raw BMP PUA characters (`U+E000`–
  `U+F8FF`) even though nearby Supplementary-Plane PUA characters (`U+F0000`+) survive.
  If Claude is filling in Nerd Font icon values, prefer pulling exact codepoints from
  `starship preset nerd-font-symbols` (or writing them via explicit `\uXXXX` Python
  escapes) over typing the glyph character directly, and always verify with `tomllib`/
  a strict parser afterward rather than trusting a visual diff.
- **GTK terminal font/palette changes need a fresh pane.** `gsettings set` doesn't
  retroactively re-render an already-open tab.
- **`git diff | delta` won't show delta's styling if you only set `core.pager`** — git
  only invokes the configured pager for direct TTY output, not piped/redirected output.
  Test by piping into delta explicitly.
- **No sudo, no problem**: every tool here ships a portable Linux binary/tarball on its
  GitHub releases page. Don't reach for `apt`/`snap` first — they need root and this
  skill is designed to never need it.
- **Never automate `gh auth login`, and never persist a token the user pastes.** If a
  user pastes a PAT into the conversation, pipe it directly into
  `gh auth login --with-token` and nowhere else — not a file, not a log, not an asset
  template, not this skill's own repo. Tell the user plainly that a token pasted into
  chat lives in that conversation's history, so they can decide whether to rotate it.
- **T3 Code shows no status line or mods.** T3 drives the real `claude` binary through
  the Agent SDK, so `CLAUDE.md`, hooks and skills load, but TUI-only features don't
  render. See **Known gaps** in the T3 Code section.
- **`--version` output isn't always plain text.** Some tools (`btop`, some `delta`
  builds) embed their own ANSI color codes even when piped. If you're composing that
  output into another colored line (like `ai-workbench-doctor` does), strip escape codes
  first (`sed -E 's/\x1b\[[0-9;]*m//g'`) or the two color schemes will visibly clash.
- **Boxes set up as `cyberdeck` fail four doctor checks.** Machines installed before
  the rename still have `cyberdeck.theme`, `theme "cyberdeck"`, `color_theme =
  "cyberdeck"` and the `Cyberdeck` Ptyxis palette, so the Ptyxis, zellij, btop theme
  and btop.conf checks fail. The old files differ from the current assets only in the
  name, so back them up and re-run the Ptyxis palette, zellij and btop steps.
