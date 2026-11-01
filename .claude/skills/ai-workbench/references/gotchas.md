# Known gotchas (ai-workbench)



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
- **JetBrainsMono looks spaced out next to the system font.** It's a wider font, not
  the `NerdFontMono` bug. Keep Ptyxis on the system font (`use-system-font true`);
  icons still come from the Nerd Font through fontconfig fallback.
- **A Ptyxis started before the font install draws over-wide cells in every new
  window too.** Its background `--gapplication-service` process outlives its windows.
  The font metrics are fine (all glyphs 600/1000 units); the fix is a full restart.
  See the Nerd Font section. Don't chase the font file first.
- **Look before you guess at visual bugs.** The user's latest screenshot is usually in
  `~/Pictures/Screenshots/`. To capture one yourself on GNOME Wayland:
  `gdbus call --session --dest org.freedesktop.portal.Desktop --object-path
  /org/freedesktop/portal/desktop --method org.freedesktop.portal.Screenshot.Screenshot
  "" "{'interactive': <false>}"` saves `~/Pictures/Screenshot.png`. It captures the
  whole screen, including other apps, so delete it once you've looked.
- **Fresh Ubuntu has no `pip`.** To inspect a font's metrics, download the pure-Python
  `fonttools` wheel from PyPI and unpack it with `python3 -m zipfile -e`, then run it
  with `PYTHONPATH`.
- **Old config can name programs that aren't installed** (`core.pager = delta`, a `gh`
  credential helper, a status line that runs `node`). Nothing warns you. Step 0 checks
  them and the doctor flags them.
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
  render. See **Known gaps** in `references/t3-code.md`.
- **A paired T3 client sees only that server's threads.** Two machines means two T3
  servers. If a thread "doesn't show up", check which machine the client is paired with.
- **`http://<machine>:3773` is refused on that same machine.** The short name resolves
  to `127.0.1.1` from `/etc/hosts`; T3 binds only the tailnet IP. Point that line at the
  tailnet IP (see **Moving from another machine**, step 6). Changing the address also
  means pairing the browser again: Chrome treats each host:port as a separate site.
- **The lid setting needs a reboot.** `/etc/systemd/logind.conf.d/always-on.conf` is
  read at boot; until then the lid still suspends. `busctl` (see **Always-on host**)
  shows the live value, the file doesn't.
- **Over SSH, `gsettings` needs the session bus.** Prefix with
  `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus` or it reads defaults.
- **`--version` output isn't always plain text.** Some tools (`btop`, some `delta`
  builds) embed their own ANSI color codes even when piped. If you're composing that
  output into another colored line (like `ai-workbench-doctor` does), strip escape codes
  first (`sed -E 's/\x1b\[[0-9;]*m//g'`) or the two color schemes will visibly clash.
- **Boxes set up as `cyberdeck` fail four doctor checks.** Machines installed before
  the rename still have `cyberdeck.theme`, `theme "cyberdeck"`, `color_theme =
  "cyberdeck"` and the `Cyberdeck` Ptyxis palette, so the Ptyxis, zellij, btop theme
  and btop.conf checks fail. The old files differ from the current assets only in the
  name, so back them up and re-run the Ptyxis palette, zellij and btop steps.
