"""Shared real host lock and durable legacy transaction tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from wordpress.release.manifest import ReleaseValidationError
from wordpress.release.host import OperationCleanupError, atomic, fingerprint
try:
    from wordpress.release.legacy import execute, LegacyOps
except ModuleNotFoundError:
    execute = LegacyOps = None


class LegacyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(execute, 'legacy coordinator missing')
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('GAMA_HOST_TEST_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        (self.root / 'mode').write_text('legacy')
        self.request = {'operation_id': 'legacy-901-1', 'kind': 'deploy',
                        'git_sha': 'a' * 40, 'image_tag': 'sha-' + 'a' * 40}
        self.effects = []
        parent = self
        class Ops:
            def mutate(self, request):
                parent.effects.append('mutate')
                journal = json.loads((parent.root / 'operation.json').read_text())
                parent.assertEqual(journal['status'], 'mutating')
            def verify(self, request): parent.effects.append('verify')
        self.ops = Ops()

    def test_mode_and_unresolved_state_block_before_mutation(self):
        for mode in ('off', 'wordpress', '', 'LEGACY'):
            (self.root / 'mode').write_text(mode)
            with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        (self.root / 'mode').write_text('legacy')
        for status in ('pending', 'mutating', 'interrupted', 'failed'):
            (self.root / 'operation.json').write_text(json.dumps({'status': status}))
            with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, [])

    def test_success_has_intent_before_mutation_and_duplicate_has_no_effect(self):
        self.assertEqual(execute(self.request, self.root, self.ops)['status'], 'completed')
        self.assertEqual(self.effects, ['mutate', 'verify'])
        execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, ['mutate', 'verify'])
        self.assertFalse((self.root / 'accepted.json').exists())

    def test_historical_replay_does_not_remutate_or_overwrite_newer_journal(self):
        accepted = '{"fixture":"existing WordPress acceptance"}'
        (self.root / 'accepted.json').write_text(accepted)
        first = execute(self.request, self.root, self.ops)
        second = {**self.request, 'operation_id': 'legacy-902-1',
                  'git_sha': 'b' * 40, 'image_tag': 'sha-' + 'b' * 40}
        execute(second, self.root, self.ops)
        journal = (self.root / 'operation.json').read_bytes()
        self.assertEqual(execute(self.request, self.root, self.ops), first)
        self.assertEqual(self.effects, ['mutate', 'verify', 'mutate', 'verify'])
        self.assertEqual((self.root / 'operation.json').read_bytes(), journal)
        self.assertEqual((self.root / 'accepted.json').read_text(), accepted)

    def test_conflicting_historical_identity_refuses_before_mutation(self):
        execute(self.request, self.root, self.ops)
        execute({**self.request, 'operation_id': 'legacy-902-1'}, self.root, self.ops)
        conflict = {**self.request, 'git_sha': 'b' * 40, 'image_tag': 'sha-' + 'b' * 40}
        with self.assertRaises(ReleaseValidationError): execute(conflict, self.root, self.ops)
        self.assertEqual(self.effects, ['mutate', 'verify', 'mutate', 'verify'])

    def test_completion_is_private_and_durable_before_completed_journal_under_lock(self):
        import fcntl
        writes = []
        def observe(path, value):
            with (self.root / 'lock').open('a') as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if path.name == 'operation.json' and value['status'] == 'completed':
                history = json.loads((self.root / 'legacy-completed.json').read_text())
                self.assertIn(self.request['operation_id'], history['operations'])
            atomic(path, value)
            writes.append((path.name, value.get('status')))
        with patch('wordpress.release.legacy.atomic', observe):
            execute(self.request, self.root, self.ops)
        self.assertLess(writes.index(('legacy-completed.json', None)), writes.index(('operation.json', 'completed')))
        self.assertEqual((self.root / 'legacy-completed.json').stat().st_mode & 0o777, 0o600)

    def test_ledger_write_failure_keeps_incident_and_blocks_retry(self):
        def fail_history(path, value):
            if path.name == 'legacy-completed.json': raise OSError('fixture fsync/write failure')
            atomic(path, value)
        with patch('wordpress.release.legacy.atomic', fail_history):
            self.assertEqual(execute(self.request, self.root, self.ops)['status'], 'failed')
        self.assertTrue((self.root / 'incident.json').exists())
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, ['mutate', 'verify'])

    def test_existing_preledger_completed_journal_is_preserved_before_next_operation(self):
        atomic(self.root / 'operation.json', {'status': 'completed', 'kind': 'legacy-deploy',
               'operation_id': self.request['operation_id'], 'fingerprint': fingerprint(self.request)})
        execute({**self.request, 'operation_id': 'legacy-902-1'}, self.root, self.ops)
        self.assertEqual(execute(self.request, self.root, self.ops)['status'], 'completed')
        self.assertEqual(self.effects, ['mutate', 'verify'])

    def test_malformed_completion_history_refuses_before_mutation(self):
        atomic(self.root / 'legacy-completed.json', {'schema_version': 1, 'operations': {
            'legacy-901-1': {'fingerprint': 'invalid', 'result': {'status': 'completed', 'operation_id': 'legacy-901-1'}}}})
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, [])

    def test_existing_null_completion_history_is_corruption_not_new_state(self):
        (self.root / 'legacy-completed.json').write_text('null')
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, [])

    def test_failed_verification_blocks_following_operations(self):
        def fail(request): raise ReleaseValidationError('not healthy')
        self.ops.verify = fail
        self.assertEqual(execute(self.request, self.root, self.ops)['status'], 'failed')
        self.assertTrue((self.root / 'incident.json').exists())
        self.request['operation_id'] = 'legacy-902-1'
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, ['mutate'])

    def test_cleanup_uncertainty_is_interrupted_and_never_retried(self):
        def fail(request): raise OperationCleanupError('cleanup uncertain')
        self.ops.mutate = fail
        self.assertEqual(execute(self.request, self.root, self.ops)['status'], 'interrupted')
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)

    def test_request_is_closed_and_tags_cannot_inject_shell(self):
        for tag in ('latest', 'sha-short', 'main-latest\nOTHER=evil', '$(id)'):
            self.request['image_tag'] = tag
            with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.request['image_tag'] = 'sha-' + 'a' * 40
        self.request['command'] = 'id'
        with self.assertRaises(ReleaseValidationError): execute(self.request, self.root, self.ops)
        self.assertEqual(self.effects, [])

    def test_real_commands_wait_and_verify_under_shared_lock_without_leaking_secrets(self):
        self._real_commands({'Running': True, 'Health': {'Status': 'healthy'}}, 'completed')

    def test_running_legacy_without_configured_healthcheck_is_accepted(self):
        self._real_commands({'Running': True}, 'completed')

    def test_unhealthy_legacy_is_refused(self):
        self._real_commands({'Running': True, 'Health': {'Status': 'unhealthy'}}, 'failed')

    def test_stopped_legacy_is_refused(self):
        self._real_commands({'Running': False}, 'failed')

    def test_wrong_legacy_image_is_refused(self):
        self._real_commands({'Running': True}, 'failed', wrong_image=True)

    def _real_commands(self, state, expected_status, wrong_image=False):
        (self.root / 'observation.json').write_text(json.dumps({'state': state, 'wrong_image': wrong_image}))
        compose = self.root / 'docker-compose.yml'; compose.write_text('services: {}')
        env_file = self.root / '.env'; env_file.write_text('fixture'); env_file.chmod(0o600)
        docker = self.root / 'docker'
        docker.write_text('''#!/usr/bin/env python3
import fcntl, json, os, pathlib, sys
root = pathlib.Path(__file__).parent
with (root / 'lock').open('a') as lock:
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: pass
    else: raise SystemExit('host transaction released lock')
journal = json.loads((root / 'operation.json').read_text())
assert journal['status'] == 'mutating'
assert 'fixture-secret' not in json.dumps(journal)
args = sys.argv[1:]
with (root / 'commands').open('a') as out: out.write(json.dumps(args) + '\\n')
prefix = ['compose', '--project-name', 'vm2', '--env-file', str(root / '.env'), '--file', str(root / 'docker-compose.yml')]
tag = 'sha-' + 'a'*40
images = ['ghcr.io/grzegorzrzeznikiewicz/company-site:' + tag, 'ghcr.io/grzegorzrzeznikiewicz/company-site-backend:' + tag]
if args[0] == 'pull': assert args[1:] in [[image] for image in images]
elif args[:len(prefix)] == prefix:
    tail = args[len(prefix):]
    assert os.environ['MAILER_DSN'] == 'smtp://fixture-secret'
    assert os.environ['PERSONAL_APP_IMAGE'] == images[0]
    assert os.environ['COMPANY_API_IMAGE'] == images[1]
    if tail == ['up', '-d', '--no-build', '--wait', '--wait-timeout', '120', 'company-db']:
        assert os.environ['COMPANY_DB_PASSWORD'] == 'fixture-secret@/'
    elif tail == ['up', '-d', '--no-build', '--wait', '--wait-timeout', '120', 'company-api', 'personal-site']:
        assert os.environ['COMPANY_DB_PASSWORD'] == 'fixture-secret%40%2F'
    elif tail[:2] == ['ps', '-q']:
        assert tail[2:] in [['personal-site'], ['company-api']]
        print('b'*64 if tail[2] == 'personal-site' else 'c'*64)
    else: raise SystemExit('unexpected compose argv')
elif args[0] == 'inspect':
    assert args[1:] in [['b'*64], ['c'*64]]
    image = images[0] if args[1] == 'b'*64 else images[1]
    observation = json.loads((root/'observation.json').read_text())
    print(json.dumps([{'Image': 'sha256:'+('e' if observation['wrong_image'] else 'd')*64, 'Config': {'Image': image}, 'State': observation['state']}]))
elif args[:2] == ['image', 'inspect']:
    assert args[2:] in [[image] for image in images]
    print(json.dumps([{'Id': 'sha256:'+'d'*64}]))
else: raise SystemExit('unexpected docker argv')
''')
        docker.chmod(0o700)
        config = {'docker': str(docker), 'environment': {
            'MAILER_DSN': 'MAILER_DSN=smtp://fixture-secret', 'CONTACT_RECIPIENT': 'fixture-secret',
            'CONTACT_SENDER': 'fixture-secret', 'COMPANY_API_APP_SECRET': 'fixture-secret',
            'COMPANY_DB_PASSWORD': 'fixture-secret@/', 'ADMIN_PASSWORD_HASH': 'fixture-secret'}}
        with patch('wordpress.release.legacy.COMPOSE', compose), patch('wordpress.release.legacy.ENV_FILE', env_file):
            result = execute(self.request, self.root, LegacyOps(config))
        self.assertEqual(result['status'], expected_status)
        self.assertEqual(len((self.root / 'commands').read_text().splitlines()), 10 if expected_status == 'completed' else 7)
        self.assertNotIn('fixture-secret', (self.root / 'commands').read_text())
        self.assertNotIn('fixture-secret', (self.root / 'operation.json').read_text())
