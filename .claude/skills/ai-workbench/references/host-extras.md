# Host and extras components (ai-workbench)

### Clean dock (optional, GNOME)

Read the current dock first and show it to the user:

```bash
gsettings get org.gnome.shell favorite-apps
ls /usr/share/applications ~/.local/share/applications /var/lib/snapd/desktop/applications 2>/dev/null \
  | grep -iE 'ptyxis|gnome-terminal|chrome|firefox|chromium'
```

Ask which apps to keep. The default is the terminal detected in Step 0 and the user's
browser. Use only `.desktop` IDs that exist in the listing above; GNOME silently drops
the rest. Common IDs: `org.gnome.Ptyxis.desktop`, `google-chrome.desktop`,
`firefox_firefox.desktop` (snap).

```bash
gsettings set org.gnome.shell favorite-apps "['org.gnome.Ptyxis.desktop', 'google-chrome.desktop']"
```

Unpinning only removes the shortcut; the apps stay installed. Undo with
`gsettings reset org.gnome.shell favorite-apps`. Fresh Ubuntu has no Chrome: it's a
`.deb` from google.com/chrome, so hand the user
`sudo apt install ./google-chrome-stable_current_amd64.deb`.

Verify: the `gsettings get` above prints only the chosen IDs.

### Always-on host (optional, partly hand-off)

For a machine that stays on so T3, Claude sessions and the tailnet are always
reachable, often with its lid shut and a monitor attached. Lingering (T3's service
install) already keeps user services running with nobody logged in. These cover the rest:

1. **No sleep on AC.** No root needed:
   ```bash
   gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
   ```
   Ask about battery too. A laptop the user carries, or one that should stay reachable
   while unplugged, needs `sleep-inactive-battery-type 'nothing'` as well (the default
   suspends after about 15 minutes on battery). On a box that is always plugged in,
   leaving it at `suspend` saves the battery during a power cut. The screen still blanks
   after `org.gnome.desktop.session idle-delay`; that doesn't stop anything running.
2. **Lid close does nothing.** Root, so hand the user:
   ```bash
   sudo mkdir -p /etc/systemd/logind.conf.d
   printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
     | sudo tee /etc/systemd/logind.conf.d/always-on.conf
   ```
   It takes effect at the next reboot. Restarting `systemd-logind` also applies it, but
   that logs out the desktop. **Until then, closing the lid still suspends the box.**
   With a monitor attached, GNOME turns off the built-in screen when the lid closes,
   which helps when that screen is broken.
3. **Never suspend, whatever asks.** Steps 1 and 2 don't stop a Suspend click in the
   GNOME menu or another D-Bus caller. Masking the sleep targets does, and takes effect
   at once. Root, so hand the user:
   ```bash
   sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
   ```
   Undo with the same line using `unmask`. A masked machine still shuts down and reboots.
4. **Wi-Fi before login.** Check that the active connection's password is stored
   system-wide:
   ```bash
   c=$(nmcli -t -f NAME,TYPE con show --active | awk -F: '$2=="802-11-wireless"{print $1; exit}')
   nmcli -g 802-11-wireless-security.psk-flags con show "$c"   # 0 = OK; 1 = keyring, connects only after login
   ```
   If it prints `1`, the user ticks **Make available to other users** in that
   connection's settings.
5. **Firmware (the user's step).** In the BIOS/UEFI setup (`sudo systemctl reboot
   --firmware-setup` opens it on most UEFI machines), set a battery charge limit for a
   machine that is always plugged in (HP: Battery Health Manager → *Maximize my battery
   health*), and power on after AC loss. Check
   `/sys/class/power_supply/BAT*/charge_control_end_threshold` first: if it exists,
   the limit can be set from Linux instead.

Verify after the reboot:

```bash
busctl get-property org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager HandleLidSwitch  # "ignore"
loginctl show-user "$USER" -p Linger      # yes
systemctl is-enabled suspend.target       # masked
systemctl is-enabled tailscaled           # enabled
ai-workbench-doctor                       # Always-on section
```

### Voice typing (optional, partly hand-off)

[Handy](https://github.com/cjpais/Handy) records while a shortcut is held or toggled,
transcribes on the machine (nothing leaves it), and pastes into the focused window.
Notes are for GNOME on Wayland (Ubuntu 26.04), where most dictation tools can't type
into other apps.

1. **Install (root, hand off).** Download the latest `.deb` with
   `gh release download -R cjpais/Handy -p 'Handy_*_amd64.deb' -D /tmp`, then give
   the user:
   ```bash
   sudo apt install -y /tmp/Handy_*_amd64.deb ydotool
   echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/80-uinput.rules
   sudo usermod -aG input "$USER"
   sudo systemctl reboot -i     # -i: a logged-in desktop session otherwise blocks it
   ```
   Tell the user the `input` group lets their programs create a virtual keyboard and
   read keyboard input. Ubuntu's `ydotool` package ships and enables its own
   `ydotool.service` user unit; don't add a second one (two daemons fight over the
   socket and one crash-loops).
2. **Model.** Use **Parakeet V2** (`parakeet-tdt-0.6b-v2`, English, ONNX int8 on CPU,
   transcribes once on stop). Download and verify it into Handy's models folder:
   ```bash
   d=~/.local/share/com.pais.handy/models; mkdir -p "$d"
   curl -fsSL -o /tmp/pv2.tgz https://blob.handy.computer/parakeet-v2-int8.tar.gz
   echo "ac9b9429984dd565b25097337a887bb7f0f8ac393573661c651f0e7d31563991  /tmp/pv2.tgz" | sha256sum -c && tar -xzf /tmp/pv2.tgz -C "$d"
   ```
   The streaming default (Parakeet Unified GGUF) picks the Vulkan backend on Intel
   iGPUs and ran at 0.65x real time on a UHD 620; V2 on the CPU ran at 6x. Check
   `Transcription completed in` lines in `~/.local/share/com.pais.handy/logs/handy.log`.
3. **Settings.** Quit Handy, edit `~/.local/share/com.pais.handy/settings_store.json`
   with `jq`, then start it again:
   `selected_model=parakeet-tdt-0.6b-v2`, `paste_method=ctrl_shift_v`,
   `audio_feedback=true` (start/stop chimes), `model_unload_timeout=never`,
   `overlay_style=none`, `autostart_enabled=true`. Keep the overlay off: GNOME has no
   layer-shell, so the overlay becomes a normal window that takes focus and swallows
   the paste. Running Handy under X11 (`GDK_BACKEND=x11`) doesn't fix that, and it hung.
4. **Shortcut.** Handy's own global shortcut doesn't fire in other apps on GNOME
   Wayland, so add a GNOME custom shortcut that runs `handy --toggle-transcription`.
   Use `<Super>z` unless the user wants another key. Ubuntu already owns
   `<Control><Alt>d` (show desktop) and `<Super>d`. Confirm GNOME accepted the binding:
   `journalctl --user --since -1min | grep "Failed to grab accelerator.*handy"` must
   print nothing.
   ```bash
   p=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/handy/
   s=org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$p
   gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings
   # prints @as [] when empty; otherwise put $p into the existing list, don't replace it
   gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['$p']"
   gsettings set $s name 'Handy dictation'; gsettings set $s command 'handy --toggle-transcription'
   gsettings set $s binding '<Super>z'
   ```

Verify: `handy --toggle-transcription`, two seconds, `handy --cancel`, then the log
shows `Microphone is receiving samples` and `returned to idle state`.

### Remote desktop (optional)

To see and control machine A's real GNOME screen from machine B over the tailnet. No
root on A. B needs a client (`sudo apt install -y remmina`, hand off).

On A (over SSH, prefix `gsettings`/`grdctl` with
`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus`):
```bash
d=~/.local/share/gnome-remote-desktop; mkdir -p $d
openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 -subj /CN=$(hostname) -keyout $d/rdp-tls.key -out $d/rdp-tls.crt
grdctl rdp set-tls-key $d/rdp-tls.key; grdctl rdp set-tls-cert $d/rdp-tls.crt
grdctl rdp set-credentials "$USER" '<random password>'   # store it on B with chmod 600
grdctl rdp disable-view-only; grdctl rdp enable
systemctl --user enable --now gnome-remote-desktop
grdctl status        # RDP enabled, View-only: no; port 3389
```
It listens on every interface, not only the tailnet; tell the user.

On B, write a saved Remmina profile instead of using quick connect, because Remmina
can't save the password for a quick connect. `~/.local/share/remmina/<A>.remmina`:
```ini
[remmina]
name=<A>
protocol=RDP
server=<A>
username=<user>
scale=1
window_maximize=1
precommand=ssh -o BatchMode=yes -o ConnectTimeout=8 <A> 'loginctl unlock-session $(loginctl show-user <user> -p Display --value)'
```
`scale=1` fits A's screen to the window (Desktop Sharing can't change A's resolution).
`precommand` unlocks A first: GNOME refuses to share a locked session, so the window
opens and closes at once and A's log says `Session creation inhibited`.

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
