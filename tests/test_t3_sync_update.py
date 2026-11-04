"""Run the updater with fake hosts and no access to live T3 or systemd."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.claude/skills/ai-workbench'
SCRIPT = SKILL / 'assets/t3-sync-update'

STUB = r'''#!/usr/bin/python3
import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
host = os.environ.get('FAKE_HOST', 'maxi')
root = pathlib.Path(os.environ['FAKE_ROOT'])
scenario = json.loads(os.environ['FAKE_SCENARIO'])
mode = scenario.get(host, 'success')
with (root / 'calls').open('a') as log:
    log.write(json.dumps([host, name, args]) + '\n')
if name == 'hostname':
    print(host)
elif name == 'sleep':
    pass
elif name == 'seq':
    # Exhaust the poll budget in two iterations; never wait five real minutes.
    print('1\n2')
elif name == 'ssh':
    remote, command = args[-2:]
    if scenario.get(remote) == 'offline':
        sys.exit(255)
    sys.exit(subprocess.run(['bash', '-c', command], env=dict(os.environ, FAKE_HOST=remote)).returncode)
elif name == 'systemd-run':
    if mode == 'launch-failure':
        sys.exit(1)
    assert '--property=RemainAfterExit=yes' in args
    assert '--collect' not in args
    unit = next(a.split('=', 1)[1] for a in args if a.startswith('--unit='))
    rc = subprocess.run(args[args.index('bash'):]).returncode if mode != 'timeout' else None
    (root / (host + '-' + unit)).write_text(json.dumps(rc))
elif name == 'systemctl':
    action = args[1]
    unit = args[2]
    record = root / (host + '-' + unit)
    assert record.exists(), 'queried wrong unit: ' + unit
    rc = json.loads(record.read_text())
    if action == 'show':
        if mode == 'inspect-failure':
            sys.exit(1)
        if 'ActiveState' in args:
            print('active' if rc in (None, 0) else 'failed')
        elif 'SubState' in args:
            print('running' if rc is None else 'exited')
        else:
            assert rc is not None
            print('Result=' + ('success' if rc == 0 else 'exit-code'))
            print('ExecMainCode=1')
            print('ExecMainStatus=' + str(rc))
            (root / ('inspected-' + host)).touch()
    elif action == 'stop':
        assert rc is None or mode == 'inspect-failure' or (root / ('inspected-' + host)).exists(), 'collected before checking exit status'
    elif action == 'reset-failed':
        record.unlink()
    else:
        raise AssertionError(args)
elif name == 't3':
    if args == ['update', '-y']:
        sys.exit(42 if mode == 'failed' else 0)
    assert args == ['--version']
    print('t3 0.1.8')
elif name == 'curl':
    print(json.dumps({'serverVersion': '0.1.8'}))
elif name == 't3-doctor':
    assert args == ['--fix']
else:
    raise AssertionError(name)
'''


class UpdateTests(unittest.TestCase):
    def run_update(self, scenario):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / 'bin'
            binary.mkdir()
            home = root / 'home'
            (home / '.t3').mkdir(parents=True)
            (home / '.local/bin').mkdir(parents=True)
            stub = binary / 'stub'
            stub.write_text(STUB)
            stub.chmod(0o755)
            for name in ('ssh', 'hostname', 'sleep', 'seq', 'systemd-run', 'systemctl', 't3', 'curl'):
                (binary / name).symlink_to(stub)
            (home / '.local/bin/t3-doctor').symlink_to(stub)
            env = dict(os.environ, PATH=f'{binary}:/usr/bin:/bin', HOME=str(home),
                       FAKE_ROOT=str(root), FAKE_SCENARIO=json.dumps(scenario),
                       T3_ALERT='0', FAKE_HOST='maxi')
            result = subprocess.run(['bash', str(SCRIPT), 'maxi', 'mini'], env=env,
                                    capture_output=True, text=True, timeout=45)
            calls = [json.loads(line) for line in (root / 'calls').read_text().splitlines()]
            return result, calls

    def test_success_both_hosts(self):
        result, calls = self.run_update({})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for host in ('maxi', 'mini'):
            self.assertIn(f'OK   {host} 0.1.8', result.stdout)
            self.assertTrue(any(h == host and name == 't3' and args == ['update', '-y']
                                for h, name, args in calls))
            self.assertTrue(any(h == host and name == 't3-doctor' for h, name, _ in calls))

    def test_matching_old_versions_do_not_hide_failures(self):
        result, calls = self.run_update({'maxi': 'failed', 'mini': 'failed'})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('ExecMainStatus=42', result.stdout)
        self.assertNotIn('OK  ', result.stdout)
        self.assertFalse(any(name == 'curl' for _, name, _ in calls))

    def test_remote_failure_still_finishes_local_host(self):
        result, _ = self.run_update({'mini': 'failed'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('OK   maxi', result.stdout)
        self.assertIn('FAIL mini update failed', result.stdout)

    def test_timeout_on_each_host(self):
        for host in ('maxi', 'mini'):
            with self.subTest(host=host):
                result, calls = self.run_update({host: 'timeout'})
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f'FAIL {host} update timed out', result.stdout)
                self.assertTrue(any(h == host and name == 'systemctl' and args[1] == 'stop'
                                    for h, name, args in calls))
                self.assertFalse(any(h == host and name == 't3-doctor' for h, name, _ in calls))

    def test_offline_host_does_not_block_other_update(self):
        result, calls = self.run_update({'mini': 'offline'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL mini unreachable', result.stdout)
        self.assertIn('OK   maxi', result.stdout)
        self.assertFalse(any(h == 'mini' and name == 'systemd-run' for h, name, _ in calls))

    def test_launch_failure(self):
        result, _ = self.run_update({'maxi': 'launch-failure'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL maxi could not launch', result.stdout)
        self.assertIn('OK   mini', result.stdout)

    def test_inspection_failure(self):
        result, _ = self.run_update({'mini': 'inspect-failure'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL mini cannot inspect', result.stdout)


class ReferenceTests(unittest.TestCase):
    def test_moved_reference_and_asset_paths(self):
        skill_text = (SKILL / 'SKILL.md').read_text()
        references = re.findall(r'`(references/[\w-]+\.md)`', skill_text)
        self.assertEqual(len(set(references)), 5)
        for name in set(references):
            path = SKILL / name
            self.assertTrue(path.is_file(), name)
            for asset in re.findall(r'assets/[\w.-]+', path.read_text()):
                self.assertTrue((SKILL / asset).is_file(), f'{name}: {asset}')
        for path in (ROOT / 'README.md', SKILL / 'SKILL.md', *SKILL.glob('references/*.md')):
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' not in target and not target.startswith('#'):
                    self.assertTrue((path.parent / target.split('#')[0]).is_file(), f'{path}: {target}')

    def test_shell_syntax(self):
        for name in ('t3-sync-update', 'ai-workbench-doctor'):
            subprocess.run(['bash', '-n', str(SKILL / 'assets' / name)], check=True)


if __name__ == '__main__':
    unittest.main()
