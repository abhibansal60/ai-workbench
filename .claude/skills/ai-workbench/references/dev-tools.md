# Developer tool components (ai-workbench)

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

### Node.js

Install the current LTS from nodejs.org as a tarball, verify its checksum, and link the
binaries into `~/.local/bin`:

```bash
V=$(curl -sSL https://nodejs.org/dist/index.json | python3 -c "import json,sys;print(next(r['version'] for r in json.load(sys.stdin) if r['lts']))")
a=$(uname -m | sed 's/x86_64/x64/;s/aarch64/arm64/')
curl -sSL "https://nodejs.org/dist/$V/node-$V-linux-$a.tar.xz" -o /tmp/node.tar.xz
curl -sSL "https://nodejs.org/dist/$V/SHASUMS256.txt" | grep "node-$V-linux-$a.tar.xz" \
  | awk '{print $1"  /tmp/node.tar.xz"}' | sha256sum -c -        # must print OK
mkdir -p ~/.local/share/node
tar -xJf /tmp/node.tar.xz -C ~/.local/share/node --strip-components=1
for b in node npm npx; do ln -sf ~/.local/share/node/bin/$b ~/.local/bin/$b; done
```

Verify: `node --version && npm --version`, then the status line mock payload (token
totals and any daily.dev line now render). `npm install -g` puts programs in
`~/.local/share/node/bin`, which isn't on `PATH`. Tell the user. If they want global
installs on `PATH`, ask before setting `npm config set prefix` or editing `~/.bashrc`.
Plugins that failed to install npm packages earlier (`claude plugin list` shows a note)
need a reinstall now.

### Clipboard tools

Claude Code reads pasted images on Linux with `wl-paste` (Wayland) or
`xclip` (X11). Without them, image paste silently does nothing. Both are small
Ubuntu packages whose only dependencies (`libwayland-client0`; `libx11-6`, `libxmu6`)
are already on any desktop, so pull the binaries out of the `.deb`s without root:

```bash
mkdir -p /tmp/clip && cd /tmp/clip
apt-get download wl-clipboard xclip                     # no root needed
for d in *.deb; do dpkg-deb -f "$d" Depends; dpkg-deb -x "$d" x; done
cp x/usr/bin/wl-copy x/usr/bin/wl-paste x/usr/bin/xclip ~/.local/bin/
ldd ~/.local/bin/wl-copy ~/.local/bin/xclip | grep 'not found'   # must print nothing
```

If `ldd` reports a missing library, or `apt-get` isn't there (non-Debian distro),
hand the user `sudo apt install -y wl-clipboard xclip` (or their distro's equivalent)
instead. The bash aliases add `pbcopy`/`pbpaste`, which pick the right one.

Verify with a round trip. Warn the user first: this replaces what's on their clipboard.

```bash
echo "ai-workbench test" | wl-copy && wl-paste                 # Wayland
echo "ai-workbench test" | xclip -selection clipboard && xclip -selection clipboard -o
```

### Claude Code plugins (optional)

Each plugin below is independent — install whichever subset the user picked in
Step 1, skip the rest. Tell the user what each one *does* before they choose, don't
just list names:

- **`mattpocock-skills`** — a skill pack for engineering workflows: TDD (red-green-
  refactor), debugging/diagnosis, code review, domain modeling (`GLOSSARY.md`/ADRs),
  prototyping, spec-to-tickets flows, PR bodies (`pr`) and session retros (`/retro`).
  Marketplace repo: `mattpocock/skills`.
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

Use `sudo tailscale up --ssh` instead if the user has more than one machine. It turns
on Tailscale SSH, so the machines reach each other with `ssh <machine-name>` and no keys.

(Read the install script first if the user wants; it's the official one.) If it's
installed but `tailscale ip -4` is empty, the fix is `sudo tailscale up` (or
`sudo systemctl start tailscaled`). Verify: `tailscale ip -4` prints a `100.x` address.
Install Tailscale on the phone and sign in to the same tailnet there; that is the
user's step too.
