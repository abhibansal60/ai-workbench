# Shell and terminal components (ai-workbench)

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

**Wiring the terminal: keep the system font.** The default is to leave the terminal
on the system monospace font (Ubuntu Sans Mono on Ubuntu). Its letters are narrower
than JetBrainsMono's, and that's the look the user wants. The Nerd Font still has to
be installed: fontconfig falls back to it for the icon glyphs the system font lacks,
so Starship/eza/btop icons render either way.

- **Ptyxis:**
  ```bash
  gsettings set org.gnome.Ptyxis use-system-font true
  gsettings set org.gnome.Ptyxis font-name 'JetBrainsMono Nerd Font 11'   # only used if the user turns the system font off
  ```
- **GNOME Terminal / other terminals:** leave the font setting alone.

Only switch the terminal to JetBrainsMono if the user asks for it (Ptyxis:
`use-system-font false`). Expect wider letter spacing; that is the font, not a bug.

**Important:** font changes only apply to *new* panes/windows/tabs — GTK terminals in
particular cache the font at pane-creation time. Always tell the user to open a new
tab (not reuse the current one) to see the change, and warn that a genuinely stuck
pane may need the whole app restarted, not just a new tab.

**Ptyxis needs a full restart after a *new* font is installed, not a new tab.** It
runs one background process (`ptyxis --gapplication-service`) for every window, and
closing windows doesn't always stop it. If that process started before the font
existed, every new tab and window draws each character in a cell far wider than the
letter, as if letter-spacing were on. Check and tell the user:

```bash
ps -o lstart= -p "$(pgrep -of 'ptyxis --gapplication-service')"   # before the font install = stale
```

The user restarts it (you can't: your own session usually runs inside Ptyxis): close
every Ptyxis window, run `pkill -f 'ptyxis --gapplication-service'`, open Ptyxis
again. To prove the font is fine before asking, open a fresh, separate instance:
`ptyxis --standalone -- bash -c 'echo MMMMMiiiii00000; sleep 60'`. Even spacing there
plus wide spacing in the user's windows means the service is stale, not the font.
`ai-workbench-doctor` checks this.

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
