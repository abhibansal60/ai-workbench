# T3 Code (optional component of ai-workbench)

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
   # Retry forever: after resume the port can stay busy for a while (EADDRINUSE),
   # and the default start limit would leave T3 down until someone resets it.
   printf '[Unit]\nStartLimitIntervalSec=0\n' > "$d/watchdog.conf"
   systemctl --user daemon-reload && systemctl --user restart t3code.service
   cat ~/.t3/userdata/server-runtime.json   # "host" must match, port is 3773
   ```
   This is plain HTTP inside the tailnet. For HTTPS as well, when the tailnet has
   HTTPS certificates on and the user is the Tailscale operator
   (`tailscale debug prefs | jq .OperatorUser`), point Tailscale Serve at the bound IP.
   The config persists in `tailscaled` and doesn't restart T3:
   ```bash
   tailscale serve --bg http://$host:3773
   tailscale serve status   # https://<name>.<tailnet>.ts.net -> http://<tailnet IP>:3773
   ```
   Don't use `t3 pair --tailscale` or `T3CODE_TAILSCALE_SERVE` with a tailnet bind:
   they point Serve at `127.0.0.1:3773`, where nothing listens, so HTTPS times out.
   The first HTTPS request takes a few seconds while Tailscale issues the certificate.
   To pair over HTTPS, mint a normal `t3 pair` link and replace its
   `http://<IP>:3773` with `https://<name>.<tailnet>.ts.net`.
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

7. **Optional: T3 as a desktop app.** A launcher that opens T3 in its own Chrome app
   window, starts at login and sits in the dock. Use an address that reaches T3 *from
   this machine* and that this machine's Chrome is already paired with (the short name
   once `/etc/hosts` maps it to the tailnet IP, else the `100.x` IP):
   ```bash
   url=http://<name>:3773
   mkdir -p ~/.local/share/icons ~/.local/share/applications ~/.config/autostart
   curl -fsS "$url/apple-touch-icon.png" -o ~/.local/share/icons/t3code.png
   printf '[Desktop Entry]\nType=Application\nName=T3 Code\nExec=google-chrome --app=%s\nIcon=%s\nCategories=Development;\n' \
     "$url" "$HOME/.local/share/icons/t3code.png" > ~/.local/share/applications/t3code.desktop
   cp ~/.local/share/applications/t3code.desktop ~/.config/autostart/
   desktop-file-validate ~/.local/share/applications/t3code.desktop
   ```
   Then add `t3code.desktop` to the dock (see **Clean dock**). Swap `google-chrome`
   for the user's Chromium-based browser if they use another one.

Verify: `t3 --version`, `t3 service status`, the `host` in `server-runtime.json`, and
`ai-workbench-doctor`'s T3 section. Update later with `t3 update`. Remove with
`t3 uninstall` (projects and threads in `~/.t3/userdata` are kept).

**Inline HTML pages and previews.** Agents show charts and mockups in a thread with
`html_render`, and check them first with `html_preview`. Preview needs T3's headless
Chrome, which Ubuntu 23.10+ AppArmor blocks ("This host blocks the sandbox T3's
browser runs in"). Hand the user this root command, once per machine:
`sudo env "PATH=$PATH" t3 browser setup`. Rendering works without it; only previews fail.

**Known gaps.** The Claude Code status line and dev mods don't render in T3; they are
terminal-only. A hook that depends on status-line data (for example `usage-stop.sh`
reading cached rate-limit numbers) only stays fresh while a terminal Claude session
runs alongside T3.

**More than one machine.** Each machine's T3 is a separate server with its own
threads. A browser or phone paired with machine A sees none of machine B's threads,
even on the same tailnet. Pair each client with each server (`t3 pair` on the server
whose threads it should see) and open `http://<machine>:3773`. One client can also
hold both: **Settings → Connections → Add environment** with the other machine's
pairing URL lists both machines' threads together, and **Load balancing** (Prefer /
Manual only, saved per client) picks which machine new threads go to. Signing in to the same T3 Connect account on a client also lists both machines (`t3 connect status`).
For agents: `t3 environment link --pairing-code <code from t3 pair there> --access full-access https://<other>.<tailnet>.ts.net`
on each machine (https only; the link lapses after 30 days) lets a thread here `delegate_task` to the other
machine with `target.environmentId`; `t3 environment list` shows reachability. Start long-running work
on the machine that stays on. Keep the versions equal: the phone app refuses a
server whose orchestration protocol is older than its own ("Client not supported").
The app does this itself: the update button at the bottom of the sidebar (**Update everything**) updates
outdated provider CLIs, then every connected server, then the desktop app, and **Settings → About → Update
track** moves the whole fleet between Stable and Nightly with a database guard. Both need a client that lists
both machines and a person to click. `assets/t3-sync-update` (install to `~/.local/bin` on each machine) is the
unattended version: it runs `t3 update -y` on every host (each stays on its channel; `-y` restarts the
service without asking), then checks each server reports the version its `t3` is on and that all hosts match.
When a host has the desktop app (`~/Applications/t3code-app`), it then runs
`assets/t3-desktop-update <version>` there (install to `~/.local/bin` too): it extracts that version's AppImage
(no FUSE 2 needed) and points the `t3code-app` symlink at it, then `t3-doctor --fix`. Pass the hosts as
arguments, or set `T3_HOSTS="a b"` in `~/.bashrc`; remote hosts need SSH. `t3 update` restarts the service,
which ends every running session unless **Continue threads after restarts** (on by default) resumes it.
Channel switches (the Android app needs Nightly) go through About → Update track; a switch whose database is
ahead of the target is refused.

**Automatic sync (one machine only).** `assets/t3-sync-update.service` and
`assets/t3-sync-update.timer` go in `~/.config/systemd/user/` on the always-on
machine only; it reaches the others over SSH. Edit the hosts in `ExecStart`, then
`systemctl --user daemon-reload && systemctl --user enable --now t3-sync-update.timer`.
It runs daily at 04:00 (plus up to 5 min random delay, `Persistent=true`). A run
with nothing new restarts nothing; a run with a new release restarts T3 on every
host and ends running turns. Logs: `journalctl --user -u t3-sync-update`.

**Expected at boot:** T3 can fail once because the tailnet IP isn't up yet.
`Restart=always` brings it back within seconds; `journalctl --user -u t3code -b`
shows the one failure.

