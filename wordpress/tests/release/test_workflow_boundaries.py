"""Execute workflow shell boundaries; API/Docker/SSH behavior is separately tested.

Only external commands are replaced. Event inputs and expected calls are literal.
"""
import json
import base64
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / '.github/workflows'
SHA = '1234567890abcdef1234567890abcdef12345678'
IMAGE = 'sha256:' + 'a' * 64
REPOSITORY = 'grzegorzrzeznikiewicz/company-site'


def scalar(filename, name, key='run'):
    lines = (WORKFLOWS / filename).read_text().splitlines()
    inside = False
    for index, line in enumerate(lines):
        if line.strip() == '- name: ' + name:
            inside = True
        elif inside and line.strip().startswith('- name:'):
            break
        if inside and line.strip().startswith(key + ': '):
            value = line.strip()[len(key) + 2:]
            if value != '|':
                return value + '\n'
            indent = len(line) - len(line.lstrip()) + 2
            result = []
            for content in lines[index + 1:]:
                if content.strip() and len(content) - len(content.lstrip()) < indent:
                    break
                result.append(content[indent:] if content.strip() else '')
            return '\n'.join(result) + '\n'
    raise AssertionError('Missing executable workflow step: ' + filename + '/' + name)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.event = self.root / 'event.json'
        self.output = self.root / 'output'
        self.env = {**os.environ, 'GITHUB_EVENT_PATH': str(self.event),
                    'GITHUB_OUTPUT': str(self.output), 'RUNNER_TEMP': str(self.root),
                    'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
                    'GITHUB_RUN_ID': '901', 'GITHUB_RUN_ATTEMPT': '1',
                    'GITHUB_SHA': SHA, 'GAMA_DEPLOYMENT_MODE': 'wordpress',
                    'GITHUB_EVENT_NAME': 'workflow_run'}

    def run_step(self, workflow, step, env=None, key='run'):
        script = scalar(workflow, step, key)
        self.assertNotIn('${{', script, 'Shell must consume event/input data through env or JSON')
        return subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=ROOT,
                              env={**self.env, **(env or {})}, text=True, capture_output=True)

    def source_event(self):
        return {'repository': {'full_name': REPOSITORY, 'fork': False,
                               'default_branch': 'main'},
                'workflow_run': {'id': 41, 'run_attempt': 2, 'head_sha': SHA,
                                 'conclusion': 'success', 'event': 'push', 'head_branch': 'main',
                                 'head_repository': {'full_name': REPOSITORY, 'fork': False}}}

    def test_standard_guard_rejects_disabled_or_untrusted_before_privilege(self):
        valid = self.source_event()
        variants = [(valid, mode) for mode in ('', 'off', 'legacy', 'WORDPRESS')]
        for field, value in [('event', 'pull_request'), ('head_branch', 'feature/a'),
                             ('conclusion', 'failure')]:
            bad = json.loads(json.dumps(valid)); bad['workflow_run'][field] = value
            variants.append((bad, 'wordpress'))
        bad = json.loads(json.dumps(valid))
        bad['workflow_run']['head_repository']['full_name'] = 'attacker/company-site'
        variants.append((bad, 'wordpress'))
        for event, mode in variants:
            with self.subTest(mode=mode, event=event):
                self.event.write_text(json.dumps(event)); self.output.unlink(missing_ok=True)
                result = self.run_step('wordpress-production.yml', 'Guard production entry',
                                       {'GAMA_DEPLOYMENT_MODE': mode})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('operation=standard', self.output.read_text() if self.output.exists() else '')
        self.event.write_text(json.dumps(valid))
        result = self.run_step('wordpress-production.yml', 'Guard production entry')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('operation=standard\n', self.output.read_text())

    def test_legacy_tag_is_data_and_hostile_shell_never_executes(self):
        marker = self.root / 'injected'
        for tag in ['main-latest', 'sha-' + SHA]:
            result = self.run_step('rollback.yml', 'Prepare image metadata', {'INPUT_IMAGE_TAG': tag})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('company-site:' + tag, self.output.read_text())
        for tag in ['latest', 'sha-short', 'main-latest\nimage=attacker',
                    '$(touch ' + str(marker) + ')', '"; touch ' + str(marker) + '; #']:
            self.output.unlink(missing_ok=True)
            result = self.run_step('rollback.yml', 'Prepare image metadata', {'INPUT_IMAGE_TAG': tag})
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertFalse(self.output.exists())

    def test_legacy_and_recovery_guard_refuse_other_modes_branches_and_attempt_reuse(self):
        self.event.write_text(json.dumps(self.source_event()))
        for workflow in ('deploy.yml', 'rollback.yml'):
            for mode, ref, event_name, allowed in [
                ('legacy', 'refs/heads/main', 'workflow_dispatch', True),
                ('wordpress', 'refs/heads/main', 'workflow_dispatch', False),
                ('off', 'refs/heads/main', 'workflow_run', False),
                ('', 'refs/heads/main', 'workflow_run', False),
                ('legacy', 'refs/heads/feature/evil', 'workflow_dispatch', False),
                ('legacy', 'refs/heads/main', 'pull_request', False)]:
                self.output.unlink(missing_ok=True)
                result = self.run_step(workflow, 'Guard legacy entry', {
                    'GAMA_DEPLOYMENT_MODE': mode, 'GITHUB_REF': ref, 'GITHUB_EVENT_NAME': event_name})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('allowed=' + str(allowed).lower() + '\n', self.output.read_text())
        for mode, attempt, allowed in [('off', '1', True), ('wordpress', '1', True),
                                       ('legacy', '1', False), ('off', '2', False), ('', '1', False)]:
            self.output.unlink(missing_ok=True)
            result = self.run_step('wordpress-production-rollback.yml', 'Guard recovery entry', {
                'GAMA_DEPLOYMENT_MODE': mode, 'GITHUB_RUN_ATTEMPT': attempt,
                'GITHUB_EVENT_NAME': 'workflow_dispatch'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('allowed=' + str(allowed).lower() + '\n', self.output.read_text())
        self.output.unlink(missing_ok=True)
        result = self.run_step('wordpress-production.yml', 'Guard production entry', {
            'GAMA_DEPLOYMENT_MODE': 'off', 'GITHUB_RUN_ATTEMPT': '2', 'GITHUB_EVENT_NAME': 'workflow_dispatch'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(), 'operation=\n')

    def test_legacy_guard_limits_event_policy_to_requested_operation(self):
        self.event.write_text(json.dumps(self.source_event()))
        for workflow, allowed in [('deploy.yml', True), ('rollback.yml', False)]:
            self.output.unlink(missing_ok=True)
            result = self.run_step(workflow, 'Guard legacy entry', {
                'GAMA_DEPLOYMENT_MODE': 'legacy', 'GITHUB_EVENT_NAME': 'workflow_run'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('allowed=' + str(allowed).lower() + '\n', self.output.read_text())

    def test_pending_is_only_retry_signal_and_source_refusal_stops_before_transport(self):
        script = scalar('wordpress-production.yml', 'Validate source with bounded pending wait')
        fixture = self.root / 'bin'; fixture.mkdir()
        runner = fixture / 'promote-boundary'
        runner.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEMP']); args = sys.argv[1:]
with (root / 'calls').open('a') as out: out.write(json.dumps(args) + '\\n')
if args[0] == 'validate-source':
    assert args == ['validate-source', '--event', str(root/'source-event.json'), '--mode', 'wordpress', '--operation', 'standard', '--output', str(root/'source.json')]
    states = json.loads((root/'states').read_text()); status = states.pop(0)
    (root/'states').write_text(json.dumps(states))
    if status == 0: (root/'source.json').write_text('{}')
    raise SystemExit(status)
assert args == ['validate-transport', '--source', str(root/'source.json'), '--destination', str(root/'validated-release'), '--output', str(root/'validated-transport.json')]
''')
        runner.chmod(0o700)
        sleeper = fixture / 'sleep'
        sleeper.write_text('#!/bin/sh\n[ "$#" = 1 ] && [ "$1" -le 10 ] && [ "$1" -gt 0 ]\n')
        sleeper.chmod(0o700)
        script = script.replace('python3 wordpress/release/promote.py', str(runner))
        for statuses, expected in [([3, 0], ['validate-source', 'validate-source', 'validate-transport']),
                                   ([1], ['validate-source']), ([124], ['validate-source'])]:
            (self.root / 'states').write_text(json.dumps(statuses))
            (self.root / 'calls').unlink(missing_ok=True)
            (self.root / 'source.json').unlink(missing_ok=True)
            result = subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=ROOT, text=True,
                                    capture_output=True, env={**self.env, 'GITHUB_READ_TOKEN': 'fixture-read',
                                    'OPERATION': 'standard', 'PATH': str(fixture) + ':' + os.environ['PATH']})
            self.assertEqual(result.returncode, 0 if len(statuses) == 2 else statuses[0], result.stderr)
            self.assertEqual([json.loads(line)[0] for line in (self.root / 'calls').read_text().splitlines()], expected)

    def test_separate_publisher_downloads_and_uses_its_own_transport(self):
        transport = scalar('wordpress-production.yml', 'Verify exact transport on publisher runner')
        publish = scalar('wordpress-production.yml', 'Publish exact verified candidate without rebuilding')
        runner = self.root / 'publisher-boundary'
        runner.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEMP']); args = sys.argv[1:]
with (root/'calls').open('a') as out: out.write(json.dumps(args) + '\\n')
if args[0] == 'validate-transport':
    assert args == ['validate-transport', '--source', str(root/'source/source.json'), '--destination', str(root/'release'), '--output', str(root/'transport-source.json')]
    (root/'transport-source.json').write_text('publisher-local-receipt')
elif args[0] == 'publish':
    assert args == ['publish', '--release-dir', str(root/'release'), '--source', str(root/'transport-source.json'), '--repository', 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress', '--output', str(root/'publication.json')]
    assert (root/'transport-source.json').read_text() == 'publisher-local-receipt'
else: raise SystemExit('unexpected publication boundary')
''')
        runner.chmod(0o700)
        script = (transport + publish).replace('python3 wordpress/release/promote.py', str(runner))
        result = subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=ROOT,
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([json.loads(line)[0] for line in (self.root/'calls').read_text().splitlines()], ['validate-transport', 'publish'])

    def test_extracted_source_step_hard_refuses_superseded_real_api_attempt(self):
        from wordpress.tests.release.test_github_source import event
        (self.root / 'source-event.json').write_text(json.dumps(event()))
        runner = self.root / 'actual-source'
        runner.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
sys.path.insert(0, os.getcwd())
from wordpress.tests.release.test_github_source import HTTPFixture, ROOT
from wordpress.release import promote
with HTTPFixture() as fixture:
    fixture.data[ROOT + '/actions/runs/987654321']['run_attempt'] = 2
    promote.GitHubAPI = lambda token: fixture.api()
    status = promote.main(sys.argv[1:])
    assert not any('/artifacts' in path for path in fixture.requests)
    pathlib.Path(os.environ['RUNNER_TEMP'], 'source-status').write_text(str(status))
    raise SystemExit(status)
''')
        runner.chmod(0o700)
        script = scalar('wordpress-production.yml', 'Validate source with bounded pending wait')
        script = script.replace('python3 wordpress/release/promote.py', str(runner))
        result = subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=ROOT,
                                env={**self.env, 'GITHUB_READ_TOKEN': 'fixture-read', 'OPERATION': 'standard'},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((self.root / 'source-status').read_text(), '1')
        self.assertFalse((self.root / 'source.json').exists())
        self.assertFalse((self.root / 'validated-release').exists())

    def test_cutover_formatter_binds_current_dispatch_before_owner_gate(self):
        auth = {'authorization_id': 'cutover-901', 'git_sha': SHA, 'source_run_id': 41,
                'source_run_attempt': 2, 'artifact_id': 555, 'artifact_digest': 'sha256:' + 'c'*64,
                'operators': [{'id': 222, 'login': 'owner', 'type': 'User'}],
                'window_start': '2026-09-08T12:00:00Z', 'window_end': '2026-09-08T13:00:00Z'}
        summary = self.root / 'summary'
        result = self.run_step('wordpress-production.yml', 'Display exact requested cutover approval', {
            'INPUT_AUTHORIZATION': json.dumps(auth), 'GITHUB_STEP_SUMMARY': str(summary)})
        self.assertEqual(result.returncode, 0, result.stderr)
        canonical = summary.read_text().split('```json\n')[1].split('\n```')[0]
        self.assertEqual(json.loads(canonical), {**auth, 'promotion_run_id': 901, 'promotion_run_attempt': 1})
        self.assertEqual(canonical, json.dumps(json.loads(canonical), sort_keys=True, separators=(',', ':')))

    def test_ssh_steps_only_feed_json_to_fixed_installed_entrypoints(self):
        fixtures = self.root / 'bin'; fixtures.mkdir()
        sudo = fixtures / 'sudo'
        sudo.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEMP']); args = sys.argv[1:]
assert args in [
    ['/usr/bin/python3', '/srv/gama-wordpress-production/tools/wordpress/bin/production-release', '--config', '/srv/gama-wordpress-production/control/host-config.json'],
    ['/usr/bin/python3', '/srv/gama-wordpress-production/tools/wordpress/bin/production-legacy-release']]
raw = sys.stdin.buffer.read()
json.loads(raw)
(root/'received').write_bytes(raw)
with (root/'elevation').open('a') as out: out.write(json.dumps(args)+'\\n')
''')
        sudo.chmod(0o700)
        raw = json.dumps({'literal': '$(touch ' + str(self.root/'injected') + ');\n"hostile"'}).encode()
        env = {'RELEASE_REQUEST': base64.b64encode(raw).decode(), 'PATH': str(fixtures) + ':' + os.environ['PATH']}
        for workflow, step in [
            ('wordpress-production.yml', 'Execute installed serialized production transaction'),
            ('wordpress-production-rollback.yml', 'Execute installed serialized recovery transaction'),
            ('deploy.yml', 'Execute installed serialized legacy transaction'),
            ('rollback.yml', 'Execute installed serialized legacy transaction')]:
            result = self.run_step(workflow, step, env, 'script')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((self.root/'received').read_bytes(), raw)
            self.assertFalse((self.root/'injected').exists())
        self.assertEqual(len((self.root/'elevation').read_text().splitlines()), 4)

    def test_ci_passes_single_candidate_to_both_consumers(self):
        # Execute the actual orchestration with strict candidate/consumer executables.
        script = scalar('wordpress-ci.yml', 'Build rehearse and seal one candidate')
        fixture = self.root / 'bin'; fixture.mkdir()
        recorder = fixture / 'boundary'
        recorder.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEMP'])
args = sys.argv[1:]
with (root / 'calls').open('a') as out: out.write(json.dumps([args, os.environ.get('GAMA_RELEASE_IMAGE_ID')]) + '\\n')
if args[:2] == ['wordpress/release/candidate.py', 'build']:
    assert args[2:] == ['--output', str(root / 'candidate')]
    (root / 'candidate').mkdir()
    (root / 'candidate/candidate.json').write_text(json.dumps({'image_id': 'sha256:' + 'a'*64, 'git_sha': os.environ['GITHUB_SHA'], 'run_id': 901, 'run_attempt': 1}))
elif args[:2] == ['wordpress/release/candidate.py', 'seal']:
    assert os.environ['GAMA_RELEASE_IMAGE_ID'] == 'sha256:' + 'a'*64
    assert args[2:] == ['--candidate', str(root / 'candidate/candidate.json'), '--receipts', str(root / 'receipts'), '--output', str(root / 'release')]
elif args in [['wordpress/tests/staging-rollback-runtime.sh'], ['wordpress/tests/production-deployment-runtime.sh']]:
    receipt = pathlib.Path(os.environ['GAMA_RELEASE_RECEIPT_DIR'])
    assert receipt.is_absolute() and receipt.is_dir() and not receipt.is_symlink()
    assert receipt.stat().st_mode & 0o777 == 0o700
    assert os.environ['GAMA_RELEASE_IMAGE_ID'] == 'sha256:' + 'a'*64
    assert os.environ['GAMA_RELEASE_RUN_ID'] == '901'
    assert os.environ['GAMA_RELEASE_RUN_ATTEMPT'] == '1'
else: raise SystemExit('unexpected boundary argv: ' + repr(args))
''')
        recorder.chmod(0o700)
        script = script.replace('python3 wordpress/release/candidate.py', str(recorder) + ' wordpress/release/candidate.py')
        for consumer in ('staging-rollback-runtime.sh', 'production-deployment-runtime.sh'):
            script = script.replace('wordpress/tests/' + consumer, str(recorder) + ' wordpress/tests/' + consumer)
        result = subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=ROOT,
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line)[0] for line in (self.root / 'calls').read_text().splitlines()]
        self.assertEqual([call[:2] for call in calls], [
            ['wordpress/release/candidate.py', 'build'], ['wordpress/tests/staging-rollback-runtime.sh'],
            ['wordpress/tests/production-deployment-runtime.sh'], ['wordpress/release/candidate.py', 'seal']])


if __name__ == '__main__':
    unittest.main()
