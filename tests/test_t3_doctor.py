"""Exercise service repair reporting without access to live T3 or host settings."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / '.claude/skills/ai-workbench/assets/t3-doctor'

STUB = r'''
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as log:
    log.write(json.dumps([name, args]) + '\n')
if name == 't3':
    if args == ['service', 'status']:
        print('needs an update or repair' if os.environ['NEEDS_REPAIR'] == '1' else 'running')
    elif args == ['service', 'install']:
        sys.exit(int(os.environ['INSTALL_EXIT']))
    else:
        sys.exit(99)
elif name == 'curl':
    assert args == ['-fsS', '-m', '5', 'http://100.64.0.1:3773/.well-known/t3/environment']
    print('{}')
elif name == 'tailscale':
    if args == ['ip', '-4']:
        print('100.64.0.1')
    else:
        assert args == ['serve', 'status', '--json']
        print(json.dumps({'Web': {'host:443': {'Handlers': {'/': {'Proxy': 'http://100.64.0.1:3773'}}}}}))
elif name == 'jq':
    if args == ['-r', '[.Web[]?.Handlers["/"].Proxy] | first // empty']:
        print(next(iter(json.load(sys.stdin)['Web'].values()))['Handlers']['/']['Proxy'])
    else:
        assert args[:2] == ['-e', '.tailscaleServeEnabled == true or has("serverExposureMode")']
        settings = json.loads(pathlib.Path(args[2]).read_text())
        sys.exit(0 if settings.get('tailscaleServeEnabled') is True or 'serverExposureMode' in settings else 1)
else:
    sys.exit(99)
'''


class DoctorTests(unittest.TestCase):
    def run_doctor(self, *, needs_repair=False, fix=False, install_exit=0):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / 'bin'
            binary.mkdir()
            home = root / 'home'
            (home / 'Applications/t3code-app').mkdir(parents=True)
            files = {}
            for relative in ('.local/share/applications/t3code-desktop.desktop',
                             '.config/autostart/t3code.desktop'):
                files[home / relative] = f'Exec=env T3CODE_HOME={home}/.t3-desktop t3code\n'
            files[home / '.t3-desktop/userdata/desktop-settings.json'] = '{"tailscaleServeEnabled": false}\n'
            for path, contents in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
            stub = binary / 'stub'
            stub.write_text(f'#!{sys.executable}\n' + STUB)
            stub.chmod(0o755)
            for name in ('t3', 'tailscale', 'curl', 'jq', 'systemctl', 'sleep', 'pgrep',
                         'pkill', 'gtk-launch', 'sed', 'mktemp', 'mv'):
                (binary / name).symlink_to(stub)
            # Only these read-only utilities can reach real host executables.
            for name in ('head', 'grep', 'basename'):
                (binary / name).symlink_to(shutil.which(name))
            calls_file = root / 'calls'
            env = dict(PATH=str(binary), HOME=str(home), T3_PORT='3773',
                       CALLS=str(calls_file), NEEDS_REPAIR=str(int(needs_repair)),
                       INSTALL_EXIT=str(install_exit))
            result = subprocess.run([shutil.which('bash'), str(SCRIPT)] + (['--fix'] if fix else []),
                                    env=env, capture_output=True, text=True, timeout=10)
            calls = [json.loads(line) for line in calls_file.read_text().splitlines()]
            self.assertEqual(result.stderr, '')
            for path, contents in files.items():
                self.assertEqual(path.read_text(), contents)
            self.assertIn('OK   service answers on 100.64.0.1:3773', result.stdout)
            self.assertIn('OK   tailscale serve -> http://100.64.0.1:3773', result.stdout)
            self.assertIn('OK   t3code-desktop.desktop uses ', result.stdout)
            self.assertIn('OK   t3code.desktop uses ', result.stdout)
            self.assertIn('OK   desktop app exposure off', result.stdout)
            self.assertTrue(all(name in ('t3', 'tailscale', 'curl', 'jq') for name, _ in calls), calls)
            installs = [args for name, args in calls if name == 't3' and args != ['service', 'status']]
            self.assertEqual(installs, [['service', 'install']] if needs_repair and fix else [])
            return result

    def test_healthy_service(self):
        for fix in (False, True):
            with self.subTest(fix=fix):
                result = self.run_doctor(fix=fix)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertNotIn('FAIL ', result.stdout)
                self.assertNotIn('FIX ', result.stdout)

    def test_needs_repair_without_fix(self):
        result = self.run_doctor(needs_repair=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('FAIL service unit needs repair', result.stdout)
        self.assertNotIn('FIX ', result.stdout)

    def test_successful_repair(self):
        result = self.run_doctor(needs_repair=True, fix=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('FIX  service unit reinstalled', result.stdout)
        self.assertNotIn('FAIL ', result.stdout)

    def test_failed_repair_with_other_probes_healthy(self):
        result = self.run_doctor(needs_repair=True, fix=True, install_exit=42)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('FAIL service unit reinstall failed', result.stdout)
        self.assertNotIn('FIX ', result.stdout)


if __name__ == '__main__':
    unittest.main()
