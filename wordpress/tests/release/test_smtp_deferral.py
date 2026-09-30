"""One first cutover may expose the form before SMTP is configured."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from wordpress.release import host
from wordpress.release.manifest import ReleaseValidationError
from wordpress.tests.release.test_host import request


class SMTPDeferralTests(unittest.TestCase):
    def test_deferral_is_bound_to_one_first_cutover(self):
        validate = getattr(host, 'validate_smtp_deferral', None)
        self.assertIsNotNone(validate, 'exact SMTP deferral validation is missing')
        req = request()
        req.update(kind='first-cutover', authorization_ref='owner-approval')
        record = {key: req[key] for key in ('operation_id', 'git_sha', 'image', 'authorization_ref')}
        record['accept_contact_delivery_unavailable'] = True
        self.assertEqual(record, validate(record, req))
        for key, value in [('operation_id', 'other'), ('git_sha', 'b'*40),
                           ('image', 'other'), ('authorization_ref', 'other'),
                           ('accept_contact_delivery_unavailable', False)]:
            with self.subTest(key=key), self.assertRaises(ReleaseValidationError):
                validate({**record, key: value}, req)
        for kind in ('standard', 'routing-rollback', 'code-rollback'):
            with self.subTest(kind=kind), self.assertRaises(ReleaseValidationError):
                validate(record, {**req, 'kind': kind})

    def test_helper_only_defers_empty_smtp_on_stable_bootstrap(self):
        script = Path(__file__).resolve().parents[2] / 'bin/deploy-production'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = root / 'calls'
            docker = root / 'docker'
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$TEST_DOCKER_CALLS"\n'
                              'if [ "$1 $2" = "image inspect" ]; then printf "sha256:%064d\\n" 0; fi\n')
            docker.chmod(0o700)
            env_file = root / 'production.env'
            base_env = 'WP_ENVIRONMENT_TYPE=production\nWP_HOME=https://gama-software.com\n'
            image = 'sha256:' + '0'*64
            base = [str(script), '--project', 'gama-wp-production', '--env-file', str(env_file),
                    '--image', image, '--http-port', '8000', '--confirm-image', image]
            env = {**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                   'TEST_DOCKER_CALLS': str(calls)}
            env_file.write_text(base_env)
            result = subprocess.run(base + ['--bootstrap', '--defer-smtp', '--mutation-only'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn('run --rm bootstrap', calls.read_text())
            calls.unlink()
            for flags, settings in [(['--bootstrap'], ''), (['--defer-smtp'], ''),
                                    (['--bootstrap', '--defer-smtp'], 'GAMA_SMTP_HOST=smtp.gmail.com\n')]:
                env_file.write_text(base_env + settings)
                result = subprocess.run(base + flags + ['--mutation-only'], env=env,
                                        capture_output=True, text=True)
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(calls.exists(), 'rejected deferral reached Docker')
