"""Read-only audit boundaries: closed output, trusted dispatch and pinned SSH."""
import base64
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


class ServerAuditTests(unittest.TestCase):
    def setUp(self):
        try:
            self.audit = importlib.import_module('wordpress.release.server_audit')
        except ModuleNotFoundError:
            self.fail('read-only server audit is not implemented')
        self.env = {
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'INPUT_OPERATION': 'read-only-audit',
            'GITHUB_REPOSITORY': 'grzegorzrzeznikiewicz/company-site',
            'GITHUB_REF': 'refs/heads/feature/GSWEB-9', 'GITHUB_SHA': 'a' * 40,
            'GITHUB_WORKFLOW_REF': 'grzegorzrzeznikiewicz/company-site/.github/workflows/deploy.yml@refs/heads/feature/GSWEB-9',
            'GITHUB_ACTOR_ID': '50638878', 'GITHUB_TRIGGERING_ACTOR': 'grzegorzrzeznikiewicz',
            'GITHUB_RUN_ATTEMPT': '1', 'GAMA_DEPLOYMENT_MODE': 'off',
        }
        self.key = base64.b64encode(b'fixture-host-public-key').decode()
        self.pin = 'SHA256:' + base64.b64encode(hashlib.sha256(b'fixture-host-public-key').digest()).decode().rstrip('=')
        self.env.update(SERVER_HOST='example.invalid', SERVER_USER='deploy', SSH_PORT='2222',
                        SSH_PRIVATE_KEY='fixture-private-key', SERVER_SSH_FINGERPRINT=self.pin)

    def test_only_owner_first_manual_attempt_on_exact_branch_in_off_mode_is_allowed(self):
        self.assertTrue(self.audit.allowed(self.env))
        for field, bad in [('GITHUB_EVENT_NAME', 'pull_request'), ('INPUT_OPERATION', 'legacy-release'),
                           ('GITHUB_REPOSITORY', 'attacker/company-site'), ('GITHUB_REF', 'refs/heads/main'),
                           ('GITHUB_ACTOR_ID', '42'), ('GITHUB_TRIGGERING_ACTOR', 'attacker'),
                           ('GITHUB_RUN_ATTEMPT', '2'), ('GAMA_DEPLOYMENT_MODE', 'legacy'),
                           ('GITHUB_WORKFLOW_REF', 'untrusted'), ('GITHUB_SHA', 'bad')]:
            with self.subTest(field=field):
                self.assertFalse(self.audit.allowed({**self.env, field: bad}))
        for field in self.env:
            if field.startswith('GITHUB_'):
                env = self.env.copy(); del env[field]
                self.assertFalse(self.audit.allowed(env))

    def test_absent_or_invalid_pin_refuses_before_any_network_or_private_key_use(self):
        for value in ('', 'SHA256:bad', 'untrusted\nvalue'):
            with self.subTest(value=value), patch.object(self.audit.subprocess, 'run') as run:
                with self.assertRaises(self.audit.AuditError):
                    self.audit.execute({**self.env, 'SERVER_SSH_FINGERPRINT': value})
                run.assert_not_called()

    def test_untrusted_dispatch_and_hostile_connection_arguments_never_connect(self):
        for field, value in [('GAMA_DEPLOYMENT_MODE', 'wordpress'), ('SERVER_HOST', '-oProxyCommand=bad'),
                             ('SERVER_HOST', 'host;id'), ('SERVER_USER', 'user@elsewhere'),
                             ('SSH_PORT', '0'), ('SSH_PORT', '65536'), ('SSH_PORT', '22\n22')]:
            with self.subTest(field=field), patch.object(self.audit.subprocess, 'run') as run:
                with self.assertRaises(self.audit.AuditError):
                    self.audit.execute({**self.env, field: value})
                run.assert_not_called()

    def test_mismatched_host_key_never_authenticates(self):
        with patch.object(self.audit.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 0, 'example.invalid ssh-ed25519 ' + base64.b64encode(b'wrong-key').decode(), '')) as run:
            with self.assertRaisesRegex(self.audit.AuditError, 'host key'):
                self.audit.execute(self.env)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][0], '/usr/bin/ssh-keyscan')

    def test_pinned_transport_sends_only_fixed_probe_and_removes_local_key(self):
        report = {'schema_version': 1, 'checks': {'linux': 'yes', 'amd64': 'yes', 'python_compatible': 'yes',
                  'docker_cli': 'missing', 'legacy_compose': 'missing', 'wordpress_tools': 'missing',
                  'control_directory': 'missing', 'host_config': 'missing',
                  'cutover_adapter': 'missing', 'rollback_adapter': 'missing'}}
        paths = []
        def external(args, **kwargs):
            self.assertNotIn('SSH_PRIVATE_KEY', kwargs['env'])
            self.assertFalse(kwargs.get('shell', False))
            if args[0] == '/usr/bin/ssh-keyscan':
                # Request only the owner's pinned key type; scanning all types
                # can exhaust the host's SSH connection rate limit before login.
                self.assertEqual(args, ['/usr/bin/ssh-keyscan', '-T', '10', '-t', 'ed25519',
                                        '-p', '2222', 'example.invalid'])
                return subprocess.CompletedProcess(args, 0, 'host ssh-ed25519 ' + self.key + '\n', '')
            self.assertEqual(args[0], '/usr/bin/ssh')
            self.assertEqual(args[-2:], ['deploy@example.invalid', '/usr/bin/python3 -I -B -'])
            self.assertIn('StrictHostKeyChecking=yes', args)
            self.assertIn('PasswordAuthentication=no', args)
            key = Path(args[args.index('-i') + 1]); paths.append(key)
            self.assertEqual(key.read_text(), 'fixture-private-key\n')
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            known = Path(next(a.split('=', 1)[1] for a in args if a.startswith('UserKnownHostsFile=')))
            self.assertEqual(known.read_text(), '[example.invalid]:2222 ssh-ed25519 ' + self.key + '\n')
            self.assertEqual(kwargs['input'], Path(self.audit.__file__).with_name('server_probe.py').read_text())
            return subprocess.CompletedProcess(args, 0, json.dumps(report), 'never log remote stderr')
        with patch.object(self.audit.subprocess, 'run', side_effect=external):
            self.assertEqual(self.audit.execute(self.env), report)
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())

    def test_remote_output_is_closed_and_never_echoes_arbitrary_text(self):
        for payload in ('SECRET', '{"schema_version":1,"checks":{"linux":"SECRET"}}',
                        '{"schema_version":true,"checks":{}}', '[]'):
            with self.subTest(payload=payload):
                with self.assertRaises(self.audit.AuditError) as error:
                    self.audit.validate_report(payload)
                self.assertNotIn('SECRET', str(error.exception))

    def test_probe_does_not_open_sensitive_files_or_execute_any_commands(self):
        probe = importlib.import_module('wordpress.release.server_probe')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'regular').write_text('DO NOT READ')
            (root / 'link').symlink_to(root / 'regular')
            with patch('builtins.open', side_effect=AssertionError('content read')), \
                    patch('subprocess.run', side_effect=AssertionError('remote command')):
                self.assertEqual(probe.path_state(root / 'missing'), 'missing')
                self.assertEqual(probe.path_state(root / 'link'), 'symlink')
                self.assertEqual(probe.path_state(root / 'regular'), 'file')
                self.assertEqual(probe.path_state(root), 'directory')
                report = probe.collect()
        self.assertEqual(self.audit.validate_report(json.dumps(report)), report)

    def test_cli_rejects_remote_output_without_printing_it_or_creating_summary(self):
        for code, output in [(1, 'PRIVATE failure'), (0, 'PRIVATE malformed JSON')]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                summary = Path(tmp) / 'summary'
                responses = [subprocess.CompletedProcess([], 0, 'host ssh-ed25519 ' + self.key, ''),
                             subprocess.CompletedProcess([], code, output, 'PRIVATE stderr')]
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {**self.env, 'GITHUB_STEP_SUMMARY': str(summary)}, clear=True), \
                        patch.object(self.audit.sys, 'argv', ['audit', 'run']), \
                        patch.object(self.audit.subprocess, 'run', side_effect=responses), \
                        redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(self.audit.main(), 1)
                self.assertEqual(stdout.getvalue(), '')
                self.assertIn('suppressed', stderr.getvalue())
                self.assertNotIn('PRIVATE', stderr.getvalue())
                self.assertFalse(summary.exists())

    def test_cli_guard_cannot_authorize_a_different_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            with patch.dict(os.environ, {**self.env, 'GITHUB_OUTPUT': str(output),
                                         'GITHUB_REF': 'refs/heads/main'}, clear=True), \
                    patch.object(self.audit.sys, 'argv', ['audit', 'guard']):
                self.assertEqual(self.audit.main(), 0)
            self.assertEqual(output.read_text(), 'allowed=false\n')

    def test_failed_ssh_cli_reports_closed_categories_without_sensitive_output(self):
        cases = [
            (255, 'Load key "/PRIVATE/identity": error in libcrypto', 'private_key_load'),
            (255, 'Load key "/PRIVATE/identity": invalid format', 'private_key_load'),
            (255, 'Load key "/PRIVATE/identity": incorrect passphrase supplied to decrypt private key', 'private_key_load'),
            (255, 'PRIVATE@PRIVATE: Permission denied (publickey).', 'authentication_rejected'),
            (255, 'Host key verification failed. PRIVATE', 'host_key_verification'),
            (255, 'ssh: connect to host PRIVATE port 22: Connection timed out', 'connection_timeout'),
            (255, 'ssh: connect to host PRIVATE port 22: Connection refused', 'connection_refused'),
            (255, 'ssh: Could not resolve hostname PRIVATE: Name or service not known', 'dns_resolution'),
            (255, 'Unable to negotiate with PRIVATE port 22: no matching host key type found.', 'algorithm_negotiation'),
            (255, 'kex_exchange_identification: Connection closed by remote host PRIVATE', 'connection_closed'),
            (255, 'Connection reset by PRIVATE port 22', 'connection_closed'),
            (127, 'bash: line 1: /usr/bin/python3: No such file or directory PRIVATE', 'remote_python_unavailable'),
            (1, 'Traceback PRIVATE', 'remote_command_failed'),
            (255, 'Unexpected PRIVATE failure ::warning::do not emit', 'unknown_ssh_failure'),
        ]
        for code, raw_error, category in cases:
            with self.subTest(category=category, raw_error=raw_error), tempfile.TemporaryDirectory() as tmp:
                summary = Path(tmp) / 'summary'
                responses = [subprocess.CompletedProcess([], 0, 'host ssh-ed25519 ' + self.key, ''),
                             subprocess.CompletedProcess([], code, 'PRIVATE stdout', raw_error)]
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {**self.env, 'GITHUB_STEP_SUMMARY': str(summary)}, clear=True), \
                        patch.object(self.audit.sys, 'argv', ['audit', 'run']), \
                        patch.object(self.audit.subprocess, 'run', side_effect=responses) as run, \
                        redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(self.audit.main(), 1)
                self.assertEqual(stdout.getvalue(), '')
                self.assertEqual(stderr.getvalue(), 'SSH audit failed [category=' + category
                                 + ', exit=' + str(code) + ']; raw connection output suppressed.\n')
                self.assertFalse(summary.exists())
                self.assertEqual(run.call_count, 2, 'Diagnostics must not retry SSH')
                ssh_args = run.call_args.args[0]
                self.assertFalse(Path(ssh_args[ssh_args.index('-i') + 1]).exists())

    def test_timeout_diagnostics_identify_stage_without_subprocess_data(self):
        for stage in ('host_key_scan', 'ssh_command'):
            timeout = subprocess.TimeoutExpired(['PRIVATE command'], 40, output='PRIVATE', stderr='PRIVATE')
            responses = [timeout] if stage == 'host_key_scan' else [
                subprocess.CompletedProcess([], 0, 'host ssh-ed25519 ' + self.key, ''), timeout]
            with self.subTest(stage=stage), patch.object(self.audit.subprocess, 'run', side_effect=responses):
                with self.assertRaises(self.audit.AuditError) as error:
                    self.audit.execute(self.env)
                self.assertEqual(str(error.exception), 'SSH audit transport failed [stage=' + stage
                                 + ', category=process_timeout]; raw connection output suppressed.')


if __name__ == '__main__':
    unittest.main()
