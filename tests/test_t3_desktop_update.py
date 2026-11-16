"""Install the desktop app into a temporary HOME from a fake release; no network, no live app."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / '.claude/skills/ai-workbench/assets/t3-desktop-update'

# Linux desktop assets as published on pingdotgg/t3code (checked 2026-11-16).
NIGHTLY = ('0.1.10-nightly.20261116.4787',
           ['T3-Code-0.1.10-nightly.20261116.4787-amd64.deb', 'T3-Code-Nightly-arm64.AppImage',
            'T3-Code-Nightly-x86_64.AppImage', 't3-0.1.10-nightly.20261116.4787-linux-x64.tar.gz'])
STABLE = ('0.1.9', ['T3-Code-0.1.9-arm64.AppImage', 'T3-Code-0.1.9-x86_64.AppImage'])
PREVIEW = ('0.1.10-preview.20261111.4547',
           ['T3-Code-0.1.10-preview.20261111.4547-arm64.AppImage',
            'T3-Code-0.1.10-preview.20261111.4547-x86_64.AppImage'])

STUB = r'''
import fnmatch, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
if name in ('pgrep', 'pkill'):
    sys.exit(1)  # the desktop app is not running
assert name == 'gh' and args[:2] == ['release', 'download'], args
assert args[2] == 'v' + os.environ['FAKE_VERSION'], args
pattern, folder = args[args.index('-p') + 1], args[args.index('-D') + 1]
found = [a for a in os.environ['FAKE_ASSETS'].split() if fnmatch.fnmatchcase(a, pattern)]
if not found:
    sys.exit('no assets match the file pattern')
for asset in found:
    path = pathlib.Path(folder, asset)
    path.write_text('#!/bin/sh\nmkdir squashfs-root && echo ' + asset + ' >squashfs-root/asset\n')
'''


class DesktopUpdateTests(unittest.TestCase):
    def test_installs_the_x86_64_appimage_of_each_channel(self):
        for version, assets in (NIGHTLY, STABLE, PREVIEW):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                binary = root / 'bin'
                binary.mkdir()
                stub = binary / 'stub'
                stub.write_text(f'#!{sys.executable}\n' + STUB)
                stub.chmod(0o755)
                for name in ('gh', 'pgrep', 'pkill'):
                    (binary / name).symlink_to(stub)
                home = root / 'home'
                (home / 'Applications').mkdir(parents=True)
                env = dict(PATH=f'{binary}:/usr/bin:/bin', HOME=str(home), TMPDIR=str(root),
                           FAKE_VERSION=version, FAKE_ASSETS=' '.join(assets))
                result = subprocess.run(['bash', str(SCRIPT), version], env=env,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f'desktop: installed {version}', result.stdout)
                link = home / 'Applications/t3code-app'
                self.assertEqual(link.resolve(), home / f'Applications/t3code-{version}')
                installed = (link / 'asset').read_text().strip()
                self.assertTrue(installed.endswith('-x86_64.AppImage'), installed)


if __name__ == '__main__':
    unittest.main()
