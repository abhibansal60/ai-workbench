---
name: ai-workbench
description: Sets up a matrix-green / cyber-purple "AI Workbench" developer environment on Linux — Starship prompt, a correctly-metriced Nerd Font, a matching 16-color terminal palette, a Claude Code status line and optional 75% usage hard stop, modern CLI tools (eza, bat, fzf, zoxide), git delta, zellij, btop, Node.js, clipboard tools (wl-clipboard, xclip) for image paste, and bash aliases with a `dh` help command, plus optional Claude Code plugins, T3 Code (a phone-friendly web UI for Claude sessions), a clean GNOME dock, always-on host settings, offline voice typing (Handy) and remote desktop between machines. Also covers moving a setup from another machine over Tailscale. Use when the user asks to set up, theme, or customize their terminal/shell/dev environment on Linux, or wants an "AI Workbench" or similarly-themed dev machine.
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

## Moving from another machine (optional, before Step 0)

If the user has a machine that is already set up and wants this one to match, copy
their own files across first, then run the skill normally. Step 0 then finds the copied
config and Step 1 only offers what's still missing. Don't copy installed binaries; the
skill reinstalls those for the new architecture and paths.

1. **Join both machines to the same tailnet** (see **Tailscale**). On the new machine
   the user runs `sudo tailscale up --ssh`, so the old one can `ssh <new-name>` with no
   keys. If the tailnet uses Tailscale SSH "check" mode, the first connection prints a
   `login.tailscale.com` URL; the user approves it in a browser, then you retry.
2. **Use the same username on both.** `~/.claude/settings.json`, hooks and T3 store
   absolute `/home/<user>/...` paths.
3. **Look before you copy.** List the target's `~/code`, `~/.claude` and `~/.local/bin`
   first. Don't overwrite anything the user made on the new machine.
4. **Copy from the old machine** over the tailnet:
   ```bash
   NEW=<new-machine-tailnet-name>
   rsync -aHz --info=progress2 --exclude={node_modules,.next,.venv,venv,__pycache__,.turbo} ~/code/ $NEW:code/
   rsync -aH --exclude={cache,file-history,paste-cache,shell-snapshots,session-env,sessions,daemon,daemon.log,ide} ~/.claude/ $NEW:.claude/
   rsync -a ~/.gitconfig $NEW:
   ```
   Also copy the user's own scripts from `~/.local/bin` and any app config they name,
   but not the binaries this skill installs. Excluding build output cut a 5.4 GB
   `~/code` to about 700 MB.
5. **Don't copy logins.** Leave the new machine's `~/.claude.json` alone (it holds that
   machine's Claude login and is created by `claude` on first run). The user signs in
   again: `gh auth login`, and any other CLIs they use (`vercel login`, `npx -y
   firebase-tools login`, ...). Each project needs its `npm install` again.
6. **Optionally name the machines.** The user runs these on each one:
   ```bash
   sudo hostnamectl set-hostname <name>
   sudo sed -i "s/^127\.0\.1\.1.*/$(tailscale ip -4 | head -1) <name>/" /etc/hosts
   sudo tailscale set --hostname=<name>
   ```
   The `/etc/hosts` line maps the machine's own name to its tailnet IP. Ubuntu's default
   `127.0.1.1` line would make `http://<name>:3773` "connection refused" on the machine
   itself, because T3 listens only on the tailnet IP. Some line must name the host, or
   `sudo` warns it can't resolve it. The tailnet IP stays fixed for the machine.
   MagicDNS then makes `ssh <name>` and `http://<name>:3773` work from every device.

After the copy, each machine's `~/.claude` (memory, skills, `CLAUDE.md`) changes on
its own. Suggest the user treats one machine as the main one.

## Step 0 — Detect the environment

Gather this before doing anything else:

```bash
uname -s                      # must be Linux
uname -m                      # x86_64 / aarch64 / etc. — determines which release asset to fetch
echo "$SHELL"                 # must be bash (or /bin/bash)
sudo -n true 2>&1             # passwordless sudo available? (informational only — never rely on it)
command -v starship eza bat fzf zoxide delta zellij btop code gh t3 tailscale wl-copy xclip 2>&1  # what's already installed
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
- `node`: optional, offered as its own component in Step 1. The status line's
  session-token segment, the daily.dev status line, `npx` and some plugins (caveman
  installs npm packages) need it. Say what's missing without it; don't install it unasked.
- `claude`: the status line, plugins and T3 Code all need Claude Code. If it's missing,
  install it with `curl -fsSL https://claude.ai/install.sh | bash` (user-local, no
  sudo) and tell the user to run `claude` once to sign in.

This step is done when `command -v curl git jq` prints all three paths.

**Config that points at missing programs.** A machine that was set up before, or got
dotfiles copied from another box, can have config that names a program that isn't
there. Each one fails quietly, so check them in Step 0 and tell the user:

```bash
git config --global --get core.pager                                  # delta, but no delta = paged git output fails
git config --global --get-all credential.https://github.com.helper   # a gh path that doesn't exist = HTTPS push fails
jq -r '.statusLine.command // empty' ~/.claude/settings.json          # e.g. statusline-combined.sh, which runs node
```

Offer the matching component in Step 1 (git delta, GitHub CLI, Node.js) as the fix.

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

Use `AskUserQuestion` (multiSelect) with one line per component. It takes at most 4
questions with 4 options each, so group the components (look, CLI tools, apps,
Claude/optional) and leave out ones Step 0 found already done. Components:

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
- **Node.js** — LTS tarball in `~/.local/share/node`, checksum-verified, no sudo
- **Clipboard tools** — `wl-clipboard` and `xclip`, extracted from Ubuntu's own
  packages without root. Claude Code needs one of them to paste images on Linux
- **Claude Code plugins** — optional, pick any subset (see **Claude Code plugins**
  below for what each one does): `mattpocock-skills`, `daily.dev`, `ponytail`,
  `caveman`, `humanizer`
- **Tailscale** — optional hand-off: private network so a phone can reach this box.
  Needs root, so the skill checks it and gives you the commands instead of running them
- **T3 Code** — optional: a self-hosted web/mobile UI (t3.codes) that runs Claude Code
  sessions on this box as a background service, so you can drive them from a phone
- **Clean dock** — optional, GNOME: pin only the terminal and the browser
- **Always-on host** — optional: for a box that stays on as a server for T3 and long
  runs. No sleep on AC, lid close ignored, sleep masked, Wi-Fi before login. Partly
  root, so partly a hand-off
- **Voice typing** — optional, partly hand-off: Handy with an offline speech model, a
  GNOME shortcut, and text pasted into the focused app (T3, terminal, browser)
- **Remote desktop** — optional: see and control another GNOME machine's screen over
  the tailnet (GNOME Desktop Sharing on the host, Remmina on the client)

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

All `assets/` paths below and in the references are relative to this skill's directory.
Each component's steps live in a reference file. Read the file for every component the user selected, in full, before installing it:

- `references/shell-tools.md`: VS Code, Starship, Nerd Font and terminal font fix, terminal palette, Claude Code status line, usage hard stop, eza/bat/fzf/zoxide, git delta, zellij, btop, bash aliases and `dh`
- `references/dev-tools.md`: GitHub CLI, Node.js, clipboard tools, Claude Code plugins, Tailscale
- `references/t3-code.md`: T3 Code (service, tailnet access, two-machine updates, desktop app, T3 Connect, linking machines)
- `references/host-extras.md`: clean dock, always-on host, voice typing, remote desktop, `ai-workbench-doctor`

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

## Known gotchas

Read `references/gotchas.md` before debugging from scratch.
