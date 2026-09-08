import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import tarfile
import textwrap
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_CLI = REPOSITORY_ROOT / 'wordpress' / 'release' / 'candidate.py'
BUILD_RELEASE = REPOSITORY_ROOT / 'wordpress' / 'bin' / 'build-release'
DEPLOY_PRODUCTION = REPOSITORY_ROOT / 'wordpress' / 'bin' / 'deploy-production'
ROLLBACK_PRODUCTION = REPOSITORY_ROOT / 'wordpress' / 'bin' / 'rollback-production'
STAGING_REHEARSAL = REPOSITORY_ROOT / 'wordpress' / 'tests' / 'staging-rollback-runtime.sh'
PRODUCTION_REHEARSAL = REPOSITORY_ROOT / 'wordpress' / 'tests' / 'production-deployment-runtime.sh'
IMAGE_A = 'sha256:' + ('a' * 64)
IMAGE_B = 'sha256:' + ('b' * 64)
GIT_SHA = '1' * 40
BEHAVIOR_HEAD = '3' * 40
BEHAVIOR_BASE = '4' * 40
BEHAVIOR_ROLLBACK_REF = 'refs/tags/task3-behavior-base'
ARCHIVE_BYTES = b'candidate-image-tar\n'
EXPECTED_PACKAGE_SCRIPT = r'''
$packages = array();
$header = static function ($path) {
    $content = file_get_contents($path);
    if (!preg_match('/^[ \t]*(?:\\*?[ \t]*)?Version:[ \t]*([^\r\n \t]+)/mi', $content, $match)) { exit(2); }
    return $match[1];
};
require '/usr/src/wordpress/wp-includes/version.php';
$packages[] = array('name' => 'wordpress', 'version' => $wp_version);
$packages[] = array('name' => 'theme/gama-software', 'version' => $header('/usr/src/wordpress/wp-content/themes/gama-software/style.css'));
foreach (array('gama-contact', 'gama-seo', 'gama-security', 'gama-local-mailpit', 'gama-mail-transport') as $plugin) {
    $packages[] = array('name' => 'plugin/' . $plugin, 'version' => $header('/usr/src/wordpress/wp-content/plugins/' . $plugin . '/' . $plugin . '.php'));
}
echo json_encode($packages, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
'''.strip()


def literal_packages():
    return [
        {'name': 'wordpress', 'version': '7.1'},
        {'name': 'theme/gama-software', 'version': '0.4.1'},
        {'name': 'plugin/gama-contact', 'version': '0.3.2'},
        {'name': 'plugin/gama-seo', 'version': '0.1.0'},
        {'name': 'plugin/gama-security', 'version': '0.1.1'},
        {'name': 'plugin/gama-local-mailpit', 'version': '0.1.0'},
        {'name': 'plugin/gama-mail-transport', 'version': '0.1.0'},
    ]


def literal_candidate(candidate_type='release'):
    source = {
        'clean': candidate_type == 'release',
        'fingerprint': None if candidate_type == 'release' else 'f' * 64,
    }
    return {
        'schema_version': 1,
        'candidate_type': candidate_type,
        'repository': 'grzegorzrzeznikiewicz/company-site',
        'git_sha': GIT_SHA,
        'workflow_id': 351411087,
        'workflow_path': '.github/workflows/wordpress-ci.yml',
        'run_id': 123456,
        'run_attempt': 2,
        'event': 'push',
        'ref': 'refs/heads/main',
        'platform': 'linux/amd64',
        'image_id': IMAGE_A,
        'source': source,
    }


def literal_receipt(name, image_id=IMAGE_A, run_id=123456, status='passed'):
    return {
        'schema_version': 1,
        'name': name,
        'status': status,
        'image_id': image_id,
        'git_sha': GIT_SHA,
        'run_id': run_id,
        'run_attempt': 2,
    }


class CandidateCliTest(unittest.TestCase):
    def test_null_image_labels_are_controlled_refusal(self):
        from unittest import mock
        from wordpress.release.candidate import _inspect_image
        from wordpress.release.manifest import ReleaseValidationError
        with mock.patch('wordpress.release.candidate._run') as command:
            command.return_value.stdout = json.dumps([{'Id': IMAGE_A, 'Os':'linux', 'Architecture':'amd64', 'Config':{'Labels':None}}]).encode()
            with self.assertRaises(ReleaseValidationError):
                _inspect_image(IMAGE_A, GIT_SHA, 'release', 'linux/amd64')

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name).resolve()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.command_log = self.root / 'commands.jsonl'
        self._write_recording_git()
        self._write_recording_docker()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                'PATH': str(self.bin) + os.pathsep + self.environment['PATH'],
                'FAKE_COMMAND_LOG': str(self.command_log),
                'FAKE_REPOSITORY_ROOT': str(REPOSITORY_ROOT),
                'FAKE_GIT_SHA': GIT_SHA,
                'FAKE_GIT_STATUS': '',
                'FAKE_IMAGE_ID': IMAGE_A,
                'FAKE_IMAGE_ARCHITECTURE': 'amd64',
                'FAKE_IMAGE_OS': 'linux',
                'FAKE_IMAGE_REVISION': GIT_SHA,
                'FAKE_RELEASE_MARKER': 'release',
                'FAKE_EXPECTED_PACKAGE_SCRIPT': EXPECTED_PACKAGE_SCRIPT,
                'GITHUB_ACTIONS': 'true',
                'GITHUB_REPOSITORY': 'grzegorzrzeznikiewicz/company-site',
                'GITHUB_SHA': GIT_SHA,
                'GAMA_RELEASE_WORKFLOW_ID': '351411087',
                'GAMA_RELEASE_WORKFLOW_PATH': '.github/workflows/wordpress-ci.yml',
                'GITHUB_RUN_ID': '123456',
                'GITHUB_RUN_ATTEMPT': '2',
                'GITHUB_EVENT_NAME': 'push',
                'GITHUB_REF': 'refs/heads/main',
            }
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_executable(self, name, body):
        path = self.bin / name
        path.write_text(textwrap.dedent(body), encoding='utf-8')
        path.chmod(0o755)

    def _write_recording_git(self):
        self._write_executable(
            'git',
            r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

with Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps(['git'] + sys.argv[1:]) + '\n')
args = sys.argv[1:]
root = os.environ['FAKE_REPOSITORY_ROOT']
if args == ['-C', root, 'rev-parse', 'HEAD']:
    print(os.environ['FAKE_GIT_SHA'])
elif args == ['-C', root, 'status', '--porcelain']:
    print(os.environ.get('FAKE_GIT_STATUS', ''))
elif args == ['-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z']:
    sys.stdout.buffer.write(b'wordpress/runtime/Dockerfile\0')
else:
    raise SystemExit('unexpected git command: ' + repr(args))
''',
        )

    def _write_recording_docker(self):
        self._write_executable(
            'docker',
            r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps(['docker'] + args) + '\n')
root = os.environ['FAKE_REPOSITORY_ROOT']
git_sha = os.environ['FAKE_GIT_SHA']
marker = os.environ['FAKE_RELEASE_MARKER']
platform = os.environ['FAKE_IMAGE_OS'] + '/' + os.environ['FAKE_IMAGE_ARCHITECTURE']
tag = 'gama-wordpress:candidate-{0}-{1}-{2}'.format(marker, platform.split('/', 1)[1], git_sha)
if args and args[0] == 'build':
    if '--iidfile' not in args:
        raise SystemExit('candidate build is missing --iidfile: ' + repr(args))
    iid_index = args.index('--iidfile')
    iidfile = Path(args[iid_index + 1])
    expected = [
        'build', '--platform', platform,
        '--file', str(Path(root) / 'wordpress/runtime/Dockerfile'),
        '--build-arg', 'GAMA_GIT_SHA=' + git_sha,
        '--build-arg', 'GAMA_RELEASE_MARKER=' + marker,
        '--tag', tag, '--iidfile', '<IIDFILE>', root,
    ]
    actual = args[:iid_index + 1] + ['<IIDFILE>'] + args[iid_index + 2:]
    if actual != expected or iidfile.name != 'image-id' or not iidfile.parent.name.startswith('gama-wordpress-candidate-'):
        raise SystemExit('unexpected candidate build argv: ' + repr(args))
    iidfile.write_text(os.environ['FAKE_IMAGE_ID'] + '\n', encoding='utf-8')
elif args == ['image', 'inspect', os.environ['FAKE_IMAGE_ID']]:
    print(json.dumps([{
        'Id': os.environ['FAKE_IMAGE_ID'],
        'Architecture': os.environ['FAKE_IMAGE_ARCHITECTURE'],
        'Os': os.environ['FAKE_IMAGE_OS'],
        'Config': {'Labels': {
            'org.opencontainers.image.revision': os.environ['FAKE_IMAGE_REVISION'],
            'com.gamasoftware.wordpress.release-marker': os.environ['FAKE_RELEASE_MARKER'],
        }},
    }]))
elif args == [
    'run', '--rm', '--network', 'none', '--entrypoint', 'php',
    os.environ['FAKE_IMAGE_ID'], '-r', os.environ['FAKE_EXPECTED_PACKAGE_SCRIPT'],
]:
    print(json.dumps([
        {'name': 'wordpress', 'version': '7.1'},
        {'name': 'theme/gama-software', 'version': '0.4.1'},
        {'name': 'plugin/gama-contact', 'version': '0.3.2'},
        {'name': 'plugin/gama-seo', 'version': '0.1.0'},
        {'name': 'plugin/gama-security', 'version': '0.1.1'},
        {'name': 'plugin/gama-local-mailpit', 'version': '0.1.0'},
        {'name': 'plugin/gama-mail-transport', 'version': '0.1.0'},
    ]))
elif len(args) == 4 and args[:2] == ['save', '--output'] and args[3] == os.environ['FAKE_IMAGE_ID']:
    output = Path(args[2])
    if output.name != 'image.tar' or not output.is_absolute():
        raise SystemExit('unexpected candidate save output: ' + repr(args))
    output.write_bytes(b'candidate-image-tar\n')
else:
    raise SystemExit('unexpected docker command: ' + repr(args))
''',
        )

    def _run(self, *arguments, environment=None):
        return subprocess.run(
            [sys.executable, str(CANDIDATE_CLI), *map(str, arguments)],
            cwd=REPOSITORY_ROOT,
            env=self.environment if environment is None else environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _commands(self):
        if not self.command_log.exists():
            return []
        return [
            json.loads(line)
            for line in self.command_log.read_text(encoding='utf-8').splitlines()
        ]

    def _write_seal_inputs(self, candidate=None, receipts=None):
        candidate_path = self.root / 'candidate.json'
        candidate_path.write_text(
            json.dumps(candidate or literal_candidate()), encoding='utf-8'
        )
        receipt_dir = self.root / 'receipts'
        receipt_dir.mkdir()
        if receipts is None:
            receipts = {
                'release-regression': literal_receipt('release-regression'),
                'production-runtime': literal_receipt('production-runtime'),
            }
        for name, receipt in receipts.items():
            (receipt_dir / (name + '.json')).write_text(
                json.dumps(receipt), encoding='utf-8'
            )
        return candidate_path, receipt_dir

    def test_clean_ci_build_records_one_immutable_candidate(self):
        output = self.root / 'candidate-output'

        result = self._run('build', '--output', output)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(literal_candidate(), json.loads((output / 'candidate.json').read_text()))
        build_commands = [
            command for command in self._commands() if command[:2] == ['docker', 'build']
        ]
        self.assertEqual(1, len(build_commands))
        self.assertIn('--platform', build_commands[0])
        self.assertEqual('linux/amd64', build_commands[0][build_commands[0].index('--platform') + 1])

    def test_recording_adapter_rejects_prefix_only_build_argv(self):
        rogue_iidfile = self.root / 'image-id'

        result = subprocess.run(
            ['docker', 'build', '--iidfile', str(rogue_iidfile)],
            cwd=REPOSITORY_ROOT, env=self.environment,
            text=True, capture_output=True, check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('unexpected candidate build argv', result.stderr)
        self.assertFalse(rogue_iidfile.exists())

    def test_build_release_exposes_the_candidate_builder(self):
        output = self.root / 'script-output'

        result = subprocess.run(
            [str(BUILD_RELEASE), '--output', str(output)],
            cwd=REPOSITORY_ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(IMAGE_A, json.loads((output / 'candidate.json').read_text())['image_id'])
        self.assertEqual(
            1,
            len([command for command in self._commands() if command[:2] == ['docker', 'build']]),
        )

    def test_build_release_allows_native_only_in_explicit_test_dirty_mode(self):
        environment = self.environment.copy()
        environment['FAKE_GIT_STATUS'] = ' M wordpress/runtime/Dockerfile'
        environment['FAKE_IMAGE_ARCHITECTURE'] = 'arm64'
        environment['FAKE_RELEASE_MARKER'] = 'development'
        output = self.root / 'wrapper-native'

        accepted = subprocess.run(
            [
                str(BUILD_RELEASE), '--test-dirty', 'local-rehearsal',
                '--development-platform', 'linux/arm64', '--output', str(output),
            ],
            cwd=REPOSITORY_ROOT, env=environment, text=True,
            capture_output=True, check=False,
        )

        self.assertEqual(0, accepted.returncode, accepted.stderr)
        self.assertEqual(
            'linux/arm64', json.loads((output / 'candidate.json').read_text())['platform']
        )

        refused = subprocess.run(
            [
                str(BUILD_RELEASE), '--development-platform', 'linux/arm64',
                '--output', str(self.root / 'wrapper-refused'),
            ],
            cwd=REPOSITORY_ROOT, env=self.environment, text=True,
            capture_output=True, check=False,
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn('development-dirty', refused.stderr)

    def test_dirty_source_requires_explicit_development_candidate(self):
        environment = self.environment.copy()
        environment['FAKE_GIT_STATUS'] = ' M wordpress/runtime/Dockerfile'
        refused = self._run('build', '--output', self.root / 'refused', environment=environment)

        self.assertNotEqual(0, refused.returncode)
        self.assertIn('clean', refused.stderr.lower())
        self.assertFalse(any(command[0] == 'docker' for command in self._commands()))

        output = self.root / 'development'
        environment['FAKE_RELEASE_MARKER'] = 'development'
        accepted = self._run(
            'build', '--development-dirty', '--output', output, environment=environment
        )
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        candidate = json.loads((output / 'candidate.json').read_text())
        self.assertEqual('development', candidate['candidate_type'])
        self.assertFalse(candidate['source']['clean'])
        self.assertRegex(candidate['source']['fingerprint'], r'^[0-9a-f]{64}$')

    def test_native_platform_is_available_only_to_dirty_development_builds(self):
        environment = self.environment.copy()
        environment['FAKE_GIT_STATUS'] = ' M wordpress/runtime/Dockerfile'
        environment['FAKE_IMAGE_ARCHITECTURE'] = 'arm64'
        environment['FAKE_RELEASE_MARKER'] = 'development'
        output = self.root / 'native-development'

        result = self._run(
            'build', '--development-dirty', '--development-platform', 'linux/arm64',
            '--output', output, environment=environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        candidate = json.loads((output / 'candidate.json').read_text())
        self.assertEqual('development', candidate['candidate_type'])
        self.assertEqual('linux/arm64', candidate['platform'])
        build = next(command for command in self._commands() if command[:2] == ['docker', 'build'])
        self.assertEqual('linux/arm64', build[build.index('--platform') + 1])

        clean_environment = self.environment.copy()
        refused = self._run(
            'build', '--development-platform', 'linux/arm64',
            '--output', self.root / 'native-release', environment=clean_environment,
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn('development-dirty', refused.stderr)

    def test_existing_build_output_is_refused_before_docker(self):
        output = self.root / 'existing-output'
        output.mkdir()

        result = self._run('build', '--output', output)

        self.assertNotEqual(0, result.returncode)
        self.assertIn('new directory', result.stderr)
        self.assertFalse(any(command[0] == 'docker' for command in self._commands()))

    def test_seal_writes_valid_manifest_and_exact_saved_image(self):
        candidate_path, receipts = self._write_seal_inputs()
        output = self.root / 'sealed'

        result = self._run(
            'seal', '--candidate', candidate_path, '--receipts', receipts,
            '--output', output,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(ARCHIVE_BYTES, (output / 'image.tar').read_bytes())
        self.assertEqual(0o600, stat.S_IMODE((output / 'image.tar').stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE((output / 'release.json').stat().st_mode))
        manifest = json.loads((output / 'release.json').read_text())
        self.assertEqual(
            {
                'schema_version': 1,
                'repository': 'grzegorzrzeznikiewicz/company-site',
                'git_sha': GIT_SHA,
                'workflow_id': 351411087,
                'workflow_path': '.github/workflows/wordpress-ci.yml',
                'run_id': 123456,
                'run_attempt': 2,
                'event': 'push',
                'ref': 'refs/heads/main',
                'platform': 'linux/amd64',
                'image_id': IMAGE_A,
                'archive_sha256': hashlib.sha256(ARCHIVE_BYTES).hexdigest(),
                'packages': literal_packages(),
                'evidence': [
                    {
                        'name': 'release-regression', 'status': 'passed',
                        'image_id': IMAGE_A, 'run_id': 123456, 'run_attempt': 2,
                    },
                    {
                        'name': 'production-runtime', 'status': 'passed',
                        'image_id': IMAGE_A, 'run_id': 123456, 'run_attempt': 2,
                    },
                ],
            },
            manifest,
        )

    def test_rejected_labels_or_platform_never_seal(self):
        candidate_path, receipts = self._write_seal_inputs()
        for field, invalid in (
            ('FAKE_RELEASE_MARKER', 'development'),
            ('FAKE_IMAGE_REVISION', '2' * 40),
            ('FAKE_IMAGE_ARCHITECTURE', 'arm64'),
            ('FAKE_IMAGE_OS', 'windows'),
        ):
            with self.subTest(field=field):
                environment = self.environment.copy()
                environment[field] = invalid
                output = self.root / ('invalid-' + field.lower())
                result = self._run(
                    'seal', '--candidate', candidate_path, '--receipts', receipts,
                    '--output', output, environment=environment,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(output.exists())

    def test_missing_failed_or_mixed_receipts_never_seal(self):
        cases = {
            'missing': {'release-regression': literal_receipt('release-regression')},
            'failed': {
                'release-regression': literal_receipt('release-regression', status='failed'),
                'production-runtime': literal_receipt('production-runtime'),
            },
            'mixed-image': {
                'release-regression': literal_receipt('release-regression'),
                'production-runtime': literal_receipt('production-runtime', image_id=IMAGE_B),
            },
            'mixed-run': {
                'release-regression': literal_receipt('release-regression'),
                'production-runtime': literal_receipt('production-runtime', run_id=999),
            },
        }
        for name, receipt_values in cases.items():
            with self.subTest(case=name):
                candidate_path, receipts = self._write_seal_inputs(receipts=receipt_values)
                output = self.root / ('rejected-' + name)
                result = self._run(
                    'seal', '--candidate', candidate_path, '--receipts', receipts,
                    '--output', output,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(output.exists())
                for path in receipts.glob('*.json'):
                    path.unlink()
                receipts.rmdir()

    def test_development_candidate_never_seals_as_release(self):
        development = literal_candidate('development')
        development['platform'] = 'linux/arm64'
        candidate_path, receipts = self._write_seal_inputs(candidate=development)

        result = self._run(
            'seal', '--candidate', candidate_path, '--receipts', receipts,
            '--output', self.root / 'not-a-release',
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('development', result.stderr.lower())
        self.assertFalse(any(command[0] == 'docker' for command in self._commands()))

    def test_untrusted_candidate_provenance_is_rejected_before_docker(self):
        candidate = literal_candidate()
        candidate['workflow_id'] = 999
        candidate_path, receipts = self._write_seal_inputs(candidate=candidate)

        result = self._run(
            'seal', '--candidate', candidate_path, '--receipts', receipts,
            '--output', self.root / 'untrusted-source',
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('workflow', result.stderr.lower())
        self.assertFalse(any(command[0] == 'docker' for command in self._commands()))


class ProductionHelperFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name).resolve()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.command_log = self.root / 'docker.jsonl'
        self._write_recording_docker()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                'PATH': str(self.bin) + os.pathsep + self.environment['PATH'],
                'FAKE_COMMAND_LOG': str(self.command_log),
                'FAKE_IMAGE_ID': IMAGE_A,
                'FAKE_RESOLVED_IMAGE_ID': IMAGE_A,
                'FAKE_RUNNING_IMAGE_ID': IMAGE_A,
            }
        )
        self.env_file = self.root / 'production.env'
        self.env_file.write_text(
            '\n'.join(
                (
                    'WP_DB_NAME=wordpress',
                    'WP_DB_USER=wordpress',
                    'WP_DB_PASSWORD=test-password',
                    'WP_DB_ROOT_PASSWORD=test-root-password',
                    'WP_HOME=https://gama-software.com',
                    'WP_SITE_TITLE=Gama Software',
                    'WP_ADMIN_USER=admin',
                    'WP_ADMIN_PASSWORD=admin-password',
                    'WP_ADMIN_EMAIL=admin@example.test',
                    'WP_ENVIRONMENT_TYPE=production',
                    'GAMA_CONTACT_RECIPIENT=contact@example.test',
                    'GAMA_CONTACT_SENDER=no-reply@example.test',
                    'GAMA_MAIL_SINK_HOST=',
                    'GAMA_SMTP_HOST=smtp.fixture.test',
                    'GAMA_SMTP_PORT=1025',
                    'GAMA_SMTP_USERNAME=test-user',
                    'GAMA_SMTP_PASSWORD=test-password',
                    'GAMA_SMTP_ENCRYPTION=tls',
                    '',
                )
            ),
            encoding='utf-8',
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_recording_docker(self):
        path = self.bin / 'docker'
        path.write_text(
            textwrap.dedent(
                r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps({'argv': args, 'fixture': os.environ.get('GAMA_PRODUCTION_REHEARSAL_FIXTURE')}) + '\n')
if args[:2] == ['image', 'inspect']:
    if '--format' in args:
        if args[args.index('--format') + 1] != '{{.Id}}':
            raise SystemExit('unexpected image inspect format: ' + repr(args))
        print(os.environ['FAKE_RESOLVED_IMAGE_ID'])
    else:
        print('[]')
elif args and args[0] == 'inspect':
    print(os.environ['FAKE_RUNNING_IMAGE_ID'])
elif args and args[0] == 'compose':
    if 'ps' in args and '-q' in args:
        print('fixture-wordpress-container')
    elif 'port' in args:
        print('127.0.0.1:49152')
else:
    raise SystemExit('unexpected docker command: ' + repr(args))
'''
            ),
            encoding='utf-8',
        )
        path.chmod(0o755)

    def _fixture(self, token='owned1234'):
        fixture = self.root / ('fixture-' + token)
        fixture.mkdir()
        (fixture / 'ca.crt').write_text('test ca\n', encoding='utf-8')
        (fixture / 'openssl-ca.ini').write_text(
            'openssl.cafile=/run/gama-test-ca/ca.crt\n', encoding='utf-8'
        )
        (fixture / '.gama-production-rehearsal-owner').write_text(
            token + '\n', encoding='utf-8'
        )
        return fixture

    def _run_helper(self, helper, project, fixture, image=IMAGE_A, environment=None):
        return subprocess.run(
            [
                str(helper), '--project', project, '--env-file', str(self.env_file),
                '--image', image, '--http-port', '0', '--confirm-image', image,
                '--rehearsal-fixture', str(fixture),
            ],
            cwd=REPOSITORY_ROOT,
            env=self.environment if environment is None else environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _commands(self):
        if not self.command_log.exists():
            return []
        return [json.loads(line) for line in self.command_log.read_text().splitlines()]

    def test_stable_namespace_rejects_fixture_before_docker_mutation(self):
        fixture = self._fixture()

        result = self._run_helper(DEPLOY_PRODUCTION, 'gama-wp-production', fixture)

        self.assertNotEqual(0, result.returncode)
        self.assertIn('stable production namespace', result.stderr)
        self.assertEqual([], self._commands())

    def test_owned_candidate_fixture_adds_only_repository_override(self):
        token = 'owned1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token

        result = self._run_helper(DEPLOY_PRODUCTION, project, fixture)

        self.assertEqual(0, result.returncode, result.stderr)
        commands = self._commands()
        compose = [item for item in commands if item['argv'][0] == 'compose']
        self.assertGreater(len(compose), 0)
        expected_override = str(
            REPOSITORY_ROOT / 'wordpress/tests/production-rehearsal.override.yaml'
        )
        for item in compose:
            self.assertIn(expected_override, item['argv'])
            self.assertEqual(str(fixture), item['fixture'])

    def test_host_mutation_only_finishes_writes_before_separate_health_probe(self):
        fixture = self._fixture()
        environment = {**self.environment, 'FAKE_RUNNING_IMAGE_ID':IMAGE_B}
        result = subprocess.run([str(DEPLOY_PRODUCTION),'--project','gama-wp-production-candidate-test-owned1234',
            '--env-file',str(self.env_file),'--image',IMAGE_A,'--http-port','0','--confirm-image',IMAGE_A,
            '--rehearsal-fixture',str(fixture),'--mutation-only'],cwd=REPOSITORY_ROOT,env=environment,text=True,capture_output=True)
        self.assertEqual(0,result.returncode,result.stderr)
        calls = [entry['argv'] for entry in self._commands()]
        self.assertTrue(any(call[-4:] == ['run','--rm','--no-deps','install'] for call in calls))
        self.assertTrue(any(call[-4:] == ['up','--detach','--no-deps','wordpress'] for call in calls))
        self.assertFalse(any('--wait' in call or '{{.Image}}' in call for call in calls))

    def test_digest_reference_resolves_to_local_id_for_runtime_assertion(self):
        token = 'digest1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token
        digest = 'registry.example.test/gama-wordpress@' + IMAGE_A

        result = self._run_helper(DEPLOY_PRODUCTION, project, fixture, image=digest)

        self.assertEqual(0, result.returncode, result.stderr)
        commands = [item['argv'] for item in self._commands()]
        self.assertTrue(any(command[0] == 'compose' and 'pull' in command for command in commands))
        self.assertIn(['image', 'inspect', '--format', '{{.Id}}', digest], commands)
        self.assertIn(['inspect', '--format', '{{.Image}}', 'fixture-wordpress-container'], commands)

    def test_local_image_id_is_resolved_and_matching_runtime_is_accepted(self):
        token = 'localid1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token

        result = self._run_helper(DEPLOY_PRODUCTION, project, fixture)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            ['image', 'inspect', '--format', '{{.Id}}', IMAGE_A],
            [item['argv'] for item in self._commands()],
        )

    def test_local_image_resolution_mismatch_refuses_before_mutation(self):
        token = 'mismatch1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token
        environment = self.environment.copy()
        environment['FAKE_RESOLVED_IMAGE_ID'] = IMAGE_B

        result = self._run_helper(
            DEPLOY_PRODUCTION, project, fixture, environment=environment
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('does not resolve to the confirmed local image ID', result.stderr)
        commands = [item['argv'] for item in self._commands()]
        self.assertFalse(any(command and command[0] == 'compose' for command in commands))

    def test_running_image_mismatch_is_refused_against_resolved_digest(self):
        token = 'runtime1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token
        digest = 'registry.example.test/gama-wordpress@' + IMAGE_A
        environment = self.environment.copy()
        environment['FAKE_RUNNING_IMAGE_ID'] = IMAGE_B

        result = self._run_helper(
            DEPLOY_PRODUCTION, project, fixture, image=digest, environment=environment
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('does not match resolved WORDPRESS_IMAGE', result.stderr)

    def test_fixture_owner_must_match_unique_namespace(self):
        fixture = self._fixture('different1234')

        result = self._run_helper(
            DEPLOY_PRODUCTION,
            'gama-wp-production-candidate-test-owned1234',
            fixture,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('ownership token', result.stderr)
        self.assertEqual([], self._commands())

    def test_rehearsal_rollback_uses_same_owned_fixture_boundary(self):
        token = 'rollback1234'
        fixture = self._fixture(token)
        project = 'gama-wp-production-candidate-test-' + token

        result = self._run_helper(ROLLBACK_PRODUCTION, project, fixture)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(any(item['argv'][0] == 'compose' for item in self._commands()))
        self.assertFalse(any(item['argv'][-3:] == ['run', '--rm', 'bootstrap'] for item in self._commands()))

    def test_ordinary_update_installs_code_without_bootstrapping_content(self):
        fixture = self._fixture('update1234')
        result = self._run_helper(DEPLOY_PRODUCTION, 'gama-wp-production-candidate-test-update1234', fixture)
        self.assertEqual(0, result.returncode, result.stderr)
        calls = [item['argv'] for item in self._commands()]
        self.assertTrue(any(call[-4:] == ['run', '--rm', '--no-deps', 'install'] for call in calls))
        self.assertFalse(any(call[-3:] == ['run', '--rm', 'bootstrap'] for call in calls))


class CandidateConsumerBehaviorTest(unittest.TestCase):
    def test_real_persistence_assertions_refuse_each_loss_even_in_bash_conditionals(self):
        import re
        for script, function in ((PRODUCTION_REHEARSAL, 'assert_persistence'),
                                 (STAGING_REHEARSAL, 'assert_persistent_page')):
            source = script.read_text()
            body = re.search(r'^' + function + r'\(\) \{\n.*?^\}', source, re.M | re.S).group()
            for loss in ('none', 'id', 'title', 'content', 'media', 'deleted-post', 'deleted-media'):
                with self.subTest(script=script.name, loss=loss):
                    fixture = self.bin/'docker'
                    fixture.write_text('''#!/usr/bin/env python3
import os,sys
a=' '.join(sys.argv); loss=os.environ['LOSS']
if 'post get' in a:
    if loss == 'deleted-post': raise SystemExit(1)
    field=a.split('--field=')[1].split()[0]
    print('bad' if loss == {'ID':'id','post_title':'title','post_content':'content'}[field] else ('101' if field=='ID' else 'fixture-marker'))
elif 'hash_file' in a:
    print('missing' if loss=='deleted-media' else ('bad' if loss=='media' else 'd'*64))
else: raise SystemExit('unexpected fixture argv')
''')
                    fixture.chmod(0o700)
                    receipt = self.root/'negative-receipt'
                    if receipt.exists(): receipt.unlink()
                    program = body + '''
persistent_post_id=101; marker=fixture-marker; source_upload_sha=''' + 'd'*64 + '''
upload_name=owned.txt; COMPOSE=(docker compose)
if ''' + function + ''' owned-container; then printf passed > "$RECEIPT"; fi
'''
                    result = subprocess.run(['bash','-euo','pipefail','-c',program],env={**self.environment,'LOSS':loss,'RECEIPT':str(receipt)},text=True,capture_output=True)
                    self.assertEqual(loss == 'none', receipt.exists(), result.stdout + result.stderr)

    def test_real_consumers_withhold_receipt_on_unrepaired_fixture_loss(self):
        for index, script in enumerate((STAGING_REHEARSAL, PRODUCTION_REHEARSAL)):
            for loss in ('id', 'title', 'content', 'media', 'deleted-post', 'deleted-media'):
                with self.subTest(script=script.name, loss=loss):
                    receipts = self.root/('receipts-'+str(index)+'-'+loss)
                    receipts.mkdir()
                    environment = {**self.environment, 'FAKE_PERSISTENCE_LOSS':loss,
                        'FAKE_BASE_SHA':BEHAVIOR_BASE, 'GAMA_ROLLBACK_BASE_REF':BEHAVIOR_ROLLBACK_REF,
                        'GAMA_RELEASE_IMAGE_ID':IMAGE_A, 'GAMA_RELEASE_GIT_SHA':BEHAVIOR_HEAD,
                        'GAMA_RELEASE_RUN_ID':'777001', 'GAMA_RELEASE_RUN_ATTEMPT':'3',
                        'GAMA_RELEASE_RECEIPT_DIR':str(receipts), 'GAMA_RELEASE_DEVELOPMENT_PLATFORM':'linux/arm64'}
                    result = subprocess.run([str(script)],cwd=REPOSITORY_ROOT,env=environment,text=True,capture_output=True)
                    self.assertNotEqual(0,result.returncode,result.stdout)
                    self.assertEqual([],list(receipts.iterdir()))

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name).resolve()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.root / 'tmp').mkdir()
        self.state_path = self.root / 'docker-state.json'
        self.command_log = self.root / 'docker-commands.jsonl'
        self.git_command_log = self.root / 'git-commands.jsonl'
        self.state_path.write_text(
            json.dumps({'candidate_builds': 0, 'images': {}, 'projects': {}, 'volumes': {}, 'containers': {}, 'options': {}}),
            encoding='utf-8',
        )
        self._write_recording_git()
        self._write_stateful_docker()
        self._write_fake_openssl()
        self._write_fake_curl()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                'PATH': str(self.bin) + os.pathsep + self.environment['PATH'],
                'FAKE_DOCKER_STATE': str(self.state_path),
                'FAKE_COMMAND_LOG': str(self.command_log),
                'FAKE_GIT_COMMAND_LOG': str(self.git_command_log),
                'FAKE_GIT_REPOSITORY_ROOT': str(REPOSITORY_ROOT),
                'FAKE_GIT_RUNTIME_ROOT': str(REPOSITORY_ROOT / 'wordpress' / '..'),
                'FAKE_GIT_HEAD': BEHAVIOR_HEAD,
                'FAKE_GIT_BASE': BEHAVIOR_BASE,
                'FAKE_GIT_ROLLBACK_REF': BEHAVIOR_ROLLBACK_REF,
                'FAKE_GIT_STATUS': ' M wordpress/runtime/Dockerfile',
                'GIT_DIR': str(self.root / 'deliberately-missing.git'),
                'GIT_WORK_TREE': str(self.root / 'deliberately-missing-worktree'),
                'FAKE_CANDIDATE_IMAGE': IMAGE_A,
                'FAKE_BASE_IMAGE': IMAGE_B,
                'FAKE_BROWSER_IMAGE': 'sha256:' + ('c' * 64),
                'TMPDIR': str(self.root / 'tmp'),
                'GITHUB_REPOSITORY': 'grzegorzrzeznikiewicz/company-site',
                'GITHUB_SHA': BEHAVIOR_HEAD,
                'GAMA_RELEASE_WORKFLOW_ID': '351411087',
                'GAMA_RELEASE_WORKFLOW_PATH': '.github/workflows/wordpress-ci.yml',
                'GITHUB_RUN_ID': '777001',
                'GITHUB_RUN_ATTEMPT': '3',
                'GITHUB_EVENT_NAME': 'push',
                'GITHUB_REF': 'refs/heads/feature/GSWEB-9',
            }
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_executable(self, name, body):
        path = self.bin / name
        path.write_text(textwrap.dedent(body), encoding='utf-8')
        path.chmod(0o755)

    def _write_recording_git(self):
        self._write_executable(
            'git',
            r'''#!/usr/bin/env python3
import io
import json
import os
from pathlib import Path
import sys
import tarfile

args = sys.argv[1:]
with Path(os.environ['FAKE_GIT_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps(args) + '\n')
root = os.environ['FAKE_GIT_REPOSITORY_ROOT']
runtime_root = os.environ['FAKE_GIT_RUNTIME_ROOT']
head = os.environ['FAKE_GIT_HEAD']
base = os.environ['FAKE_GIT_BASE']
rollback = os.environ['FAKE_GIT_ROLLBACK_REF']
if args in (
    ['-C', root, 'rev-parse', 'HEAD'],
    ['-C', runtime_root, 'rev-parse', 'HEAD'],
):
    print(head)
elif args == ['-C', runtime_root, 'rev-parse', rollback + '^{commit}']:
    print(base)
elif args == ['-C', root, 'status', '--porcelain']:
    print(os.environ['FAKE_GIT_STATUS'])
elif args == ['-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z']:
    sys.stdout.buffer.write(b'wordpress/runtime/Dockerfile\0')
elif args == ['-C', runtime_root, 'archive', base]:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        payload = b'FROM scratch\n'
        info = tarfile.TarInfo('wordpress/runtime/Dockerfile')
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))
    sys.stdout.buffer.write(stream.getvalue())
else:
    raise SystemExit('unexpected git argv: ' + repr(args))
''',
        )

    def _write_fake_openssl(self):
        self._write_executable(
            'openssl',
            r'''#!/usr/bin/env python3
from pathlib import Path
import os
import sys

args = sys.argv[1:]
if args == ['rand', '-hex', '8']:
    print('f1e2d3c4b5a69788')
elif args and args[0] in {'req', 'x509'}:
    if '-fingerprint' in args:
        print('SHA256 Fingerprint=' + ('AB:' * 31) + 'AB')
    else:
        for option in ('-keyout', '-out'):
            if option in args:
                path = Path(args[args.index(option) + 1])
                path.write_text('fixture certificate material\n', encoding='utf-8')
                path.chmod(0o600)
else:
    raise SystemExit('unexpected openssl argv: ' + repr(args))
''',
        )

    def _write_fake_curl(self):
        self._write_executable(
            'curl',
            r'''#!/usr/bin/env python3
import sys

url = sys.argv[-1]
if url.endswith('/api/v1/messages'):
    print('{"total":1}')
elif url.endswith('/api/v1/info'):
    print('{}')
else:
    raise SystemExit('unexpected curl URL: ' + url)
''',
        )

    def _write_stateful_docker(self):
        self._write_executable(
            'docker',
            r'''#!/usr/bin/env python3
import io
import json
import os
from pathlib import Path
import sys
import tarfile

args = sys.argv[1:]
state_path = Path(os.environ['FAKE_DOCKER_STATE'])
state = json.loads(state_path.read_text(encoding='utf-8'))
with Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps(args) + '\n')

candidate = os.environ['FAKE_CANDIDATE_IMAGE']
base = os.environ['FAKE_BASE_IMAGE']
browser = os.environ['FAKE_BROWSER_IMAGE']
head = os.environ['GITHUB_SHA']
base_sha = os.environ['FAKE_BASE_SHA']

def save():
    state_path.write_text(json.dumps(state), encoding='utf-8')

def project_from_args(values):
    return values[values.index('--project-name') + 1]

def env_image(values):
    if '--env-file' not in values:
        return None
    env_file = Path(values[values.index('--env-file') + 1])
    if not env_file.exists():
        return os.environ.get('WORDPRESS_IMAGE')
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if line.startswith('WORDPRESS_IMAGE='):
            return line.split('=', 1)[1]
    return os.environ.get('WORDPRESS_IMAGE')

def image_values(reference):
    image_id = state['images'].get(reference, reference)
    if image_id == candidate:
        return image_id, head, 'development', 'arm64'
    if image_id == browser:
        return image_id, head, 'browser', 'arm64'
    return base, base_sha, 'rollback-base', 'arm64'

def wordpress_output(values):
    joined = ' '.join(values)
    if 'post create' in joined and '--porcelain' in values:
        for value in values:
            if value.startswith('--post_title=GSWEB26-persistent-') or value.startswith('--post_title=GSWEB29-production-'):
                state['marker'] = value.split('=', 1)[1]
                state['post_title'] = state['marker']
                state['post_content'] = state['marker']
                state['post_exists'] = True
        save()
        print('101')
    elif 'user create' in joined and '--porcelain' in values:
        print('201')
    elif 'post list' in joined:
        print('')
    elif 'post get' in joined:
        loss = os.environ.get('FAKE_PERSISTENCE_LOSS')
        if loss == 'deleted-post': raise SystemExit(1)
        if not state.get('post_exists', True): raise SystemExit(1)
        field = next((value.split('=', 1)[1] for value in values if value.startswith('--field=')), '')
        if loss == {'ID':'id','post_title':'title','post_content':'content'}.get(field):
            print('incorrect-fixture-value'); return
        print('101' if field == 'ID' else state.get(field, state.get('marker', 'fixture-marker')))
    elif 'post update 101' in joined:
        for field in ('post_title', 'post_content'):
            for value in values:
                if value.startswith('--'+field+'='): state[field] = value.split('=',1)[1]
        save()
    elif 'post delete 101' in joined:
        state['post_exists'] = False
        save()
    elif 'unlink(' in joined:
        state['upload_sha'] = 'missing'
        save()
    elif 'file_put_contents' in joined:
        state['upload_sha'] = 'corrupted' if 'corrupted-owned-fixture' in joined else 'd'*64
        save()
        if 'echo hash_file' in joined: print(state['upload_sha'])
    elif 'wp_upload_bits' in joined:
        print('d' * 64)
    elif 'hash_file' in joined and 'exit(' not in joined:
        loss = os.environ.get('FAKE_PERSISTENCE_LOSS')
        if loss in ('media','deleted-media'):
            print('missing' if loss == 'deleted-media' else 'altered'); return
        print(state.get('upload_sha', 'd'*64))
    elif 'gama_production_runtime_upload' in joined and 'is_file' in joined:
        print('d' * 64)
    elif 'option get' in joined:
        option = values[values.index('get') + 1]
        print(state['options'].get(option, 'http://wordpress'))
    elif 'option update' in joined:
        option = values[values.index('update') + 1]
        state['options'][option] = values[values.index('update') + 2]
        save()

if not args:
    raise SystemExit('missing docker argv')
if args[0] == 'build':
    tag = args[args.index('--tag') + 1]
    if '--iidfile' in args:
        state['candidate_builds'] += 1
        state['images'][tag] = candidate
        Path(args[args.index('--iidfile') + 1]).write_text(candidate + '\n', encoding='utf-8')
    elif tag.startswith('gama-wordpress-browser:'):
        state['images'][tag] = browser
    else:
        state['images'][tag] = base
    save()
elif args[:2] == ['image', 'inspect']:
    reference = args[-1]
    image_id, revision, marker, architecture = image_values(reference)
    if '--format' not in args:
        print(json.dumps([{'Id': image_id, 'Os': 'linux', 'Architecture': architecture, 'Config': {'Labels': {'org.opencontainers.image.revision': revision, 'com.gamasoftware.wordpress.release-marker': marker}}}]))
    else:
        value = args[args.index('--format') + 1]
        if value == '{{.Id}}': print(image_id)
        elif value == '{{.Os}}/{{.Architecture}}': print('linux/' + architecture)
        elif 'org.opencontainers.image.revision' in value: print(revision)
        elif 'release-marker' in value: print(marker)
        else: raise SystemExit('unexpected image inspect format: ' + value)
elif args[0] == 'compose':
    project = project_from_args(args)
    operation = next((value for value in ('up', 'stop', 'run', 'ps', 'port', 'logs', 'down', 'rm') if value in args), None)
    if operation == 'up':
        selected = env_image(args)
        if selected:
            state['projects'][project] = selected
            save()
    elif operation == 'run':
        wordpress_output(args)
    elif operation == 'ps' and '-q' in args:
        service = args[-1]
        print(project + ('-mailpit' if service == 'mailpit' else '-wordpress'))
    elif operation == 'port':
        print('127.0.0.1:49152')
    elif operation == 'down':
        state['projects'].pop(project, None)
        save()
elif args[0] == 'inspect':
    target = args[-1]
    if '--format' not in args:
        print('{}')
    else:
        value = args[args.index('--format') + 1]
        if value == '{{.State.Health.Status}}': print('healthy')
        elif value == '{{.Image}}':
            project = target.rsplit('-', 1)[0]
            print(state['projects'].get(project, candidate))
        elif 'gama.rehearsal.owner' in value:
            print(state['containers'].get(target, {}).get('owner', ''))
        elif value == '{{json .HostConfig.PortBindings}}': print('{}')
        elif 'IPAddress' in value: print('127.0.0.2')
        else: raise SystemExit('unexpected container inspect format: ' + value)
elif args[0] == 'exec':
    if args[2:] == ['sh', '-ec', 'printf "<?php throw new RuntimeException(\\"recovery fixture\\");" > /var/www/html/wp-includes/version.php']:
        state['broken_php'] = True
        save()
    elif args[2:] == ['wp', '--allow-root', 'core', 'is-installed']:
        raise SystemExit(1 if state.get('broken_php') else 0)
    elif 'wget' in args:
        print(state.get('marker', 'fixture-marker'))
    else:
        wordpress_output(args)
elif args[0] == 'ps':
    if '--format' in args and any('service=wordpress-tls' in value for value in args):
        print('fixture-wordpress-tls')
    elif '--format' in args and any('service=wordpress' in value for value in args):
        project_filter = next(value for value in args if 'project=' in value)
        print(project_filter.rsplit('=', 1)[1] + '-wordpress')
elif args[:2] == ['volume', 'ls'] or args[:2] == ['network', 'ls']:
    pass
elif args[:2] == ['network', 'inspect']:
    print('{}')
elif args[:2] == ['volume', 'create']:
    volume = args[-1]
    owner = next((value.split('=', 1)[1] for value in args if value.startswith('gama.release-evidence-owner=')), '')
    state['volumes'][volume] = owner
    save()
    print(volume)
elif args[:2] == ['volume', 'inspect']:
    volume = args[-1]
    if volume not in state['volumes']:
        raise SystemExit(1)
    if '--format' in args:
        print(state['volumes'][volume])
    else:
        print('{}')
elif args[:2] == ['volume', 'rm']:
    state['volumes'].pop(args[-1], None)
    save()
elif args[:2] == ['image', 'rm']:
    state['images'].pop(args[-1], None)
    save()
elif args[0] == 'rm':
    state['containers'].pop(args[-1], None)
    save()
elif args[0] == 'port':
    print('127.0.0.1:49153')
elif args[0] == 'run':
    if '--detach' in args:
        name = args[args.index('--name') + 1]
        owner = next(value.split('=', 1)[1] for value in args if value.startswith('gama.rehearsal.owner='))
        state['containers'][name] = {'owner': owner}
        save()
        print('fixture-smtp-container')
    elif '--entrypoint' in args and args[args.index('--entrypoint') + 1] == 'tar':
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            payload = b'evidence\n'
            info = tarfile.TarInfo('./evidence.txt')
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        sys.stdout.buffer.write(stream.getvalue())
    elif any(value.endswith(':/tls') for value in args if ':' in value):
        mount = next(value for value in args if value.endswith(':/tls'))
        fixture = Path(mount[:-5])
        for name in ('ca.key', 'leaf.key', 'ca.crt', 'leaf.crt'):
            path = fixture / name
            path.write_text('fixture tls material\n', encoding='utf-8')
            path.chmod(0o600 if name.endswith('.key') else 0o644)
    elif args[-1] in {'reject-untrusted', 'reject-wrong-hostname', 'accept-valid'}:
        print(json.dumps({'mode': args[-1], 'status': 'passed'}))
    elif './specs/support/release-matrix-contract.cjs' in args:
        pass
    elif 'npm' in args and 'test' in args:
        pass
    elif '--entrypoint' in args and args[args.index('--entrypoint') + 1] == 'sh' and any(
        marker in args[-1]
        for marker in ('find /trust', 'JSON.parse', 'test -f /artifacts', 'mkdir -p /artifacts/tls-probes')
    ):
        pass
    else:
        raise SystemExit('unexpected docker run argv: ' + repr(args))
else:
    raise SystemExit('unexpected docker argv: ' + repr(args))
''',
        )

    def test_git_boundary_uses_fixed_history_and_rejects_unknown_argv(self):
        git_boundary = self.bin / 'git'

        self.assertTrue(git_boundary.is_file(), 'behavioral test resolved real Git')
        head = subprocess.run(
            [str(git_boundary), '-C', str(REPOSITORY_ROOT), 'rev-parse', 'HEAD'],
            env=self.environment, text=True, capture_output=True, check=True,
        )
        base = subprocess.run(
            [
                str(git_boundary), '-C', str(REPOSITORY_ROOT / 'wordpress' / '..'), 'rev-parse',
                BEHAVIOR_ROLLBACK_REF + '^{commit}',
            ],
            env=self.environment, text=True, capture_output=True, check=True,
        )
        status = subprocess.run(
            [str(git_boundary), '-C', str(REPOSITORY_ROOT), 'status', '--porcelain'],
            env=self.environment, text=True, capture_output=True, check=True,
        )
        archive = subprocess.run(
            [
                str(git_boundary), '-C', str(REPOSITORY_ROOT / 'wordpress' / '..'),
                'archive', BEHAVIOR_BASE,
            ],
            env=self.environment, capture_output=True, check=True,
        )
        self.assertEqual(BEHAVIOR_HEAD, head.stdout.strip())
        self.assertEqual(BEHAVIOR_BASE, base.stdout.strip())
        self.assertEqual(' M wordpress/runtime/Dockerfile', status.stdout.strip('\n'))
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode='r:') as fixture:
            self.assertEqual(
                ['wordpress/runtime/Dockerfile'], fixture.getnames()
            )
        refused = subprocess.run(
            [str(git_boundary), '-C', str(REPOSITORY_ROOT), 'rev-parse', 'HEAD^'],
            cwd=REPOSITORY_ROOT, env=self.environment,
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn('unexpected git argv', refused.stderr)

    def test_one_build_is_consumed_by_both_real_rehearsals_and_receipts(self):
        environment = self.environment.copy()
        environment.update(
            {
                'FAKE_BASE_SHA': BEHAVIOR_BASE,
                'GAMA_ROLLBACK_BASE_REF': BEHAVIOR_ROLLBACK_REF,
            }
        )
        candidate_output = self.root / 'candidate'
        build = subprocess.run(
            [
                str(BUILD_RELEASE), '--test-dirty', 'behavioral-boundary',
                '--development-platform', 'linux/arm64', '--output', str(candidate_output),
            ],
            cwd=REPOSITORY_ROOT, env=environment, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(0, build.returncode, build.stderr)
        candidate = json.loads((candidate_output / 'candidate.json').read_text(encoding='utf-8'))
        receipts = self.root / 'receipts'
        receipts.mkdir()
        artifact_root = self.root / 'evidence'
        environment.update(
            {
                'GAMA_RELEASE_IMAGE_ID': candidate['image_id'],
                'GAMA_RELEASE_GIT_SHA': candidate['git_sha'],
                'GAMA_RELEASE_RUN_ID': str(candidate['run_id']),
                'GAMA_RELEASE_RUN_ATTEMPT': str(candidate['run_attempt']),
                'GAMA_RELEASE_RECEIPT_DIR': str(receipts),
                'GAMA_RELEASE_DEVELOPMENT_PLATFORM': 'linux/arm64',
                'GAMA_RELEASE_ARTIFACT_ROOT': str(artifact_root),
            }
        )
        for script in (STAGING_REHEARSAL, PRODUCTION_REHEARSAL):
            result = subprocess.run(
                [str(script)], cwd=REPOSITORY_ROOT, env=environment,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(
                0,
                result.returncode,
                '{0}\nstdout:\n{1}\nstderr:\n{2}\ndocker:\n{3}'.format(
                    script.name,
                    result.stdout,
                    result.stderr,
                    self.command_log.read_text(encoding='utf-8'),
                ),
            )

        produced = [
            json.loads((receipts / name).read_text(encoding='utf-8'))
            for name in ('release-regression.json', 'production-runtime.json')
        ]
        for receipt in produced:
            self.assertEqual(candidate['image_id'], receipt['image_id'])
            self.assertEqual(candidate['git_sha'], receipt['git_sha'])
            self.assertEqual(candidate['run_id'], receipt['run_id'])
            self.assertEqual(candidate['run_attempt'], receipt['run_attempt'])
        self.assertEqual(1, json.loads(self.state_path.read_text())['candidate_builds'])
        git_commands = [
            json.loads(line)
            for line in self.git_command_log.read_text(encoding='utf-8').splitlines()
        ]
        self.assertNotIn(
            ['-C', str(REPOSITORY_ROOT), 'rev-parse', 'HEAD^'], git_commands
        )
        self.assertIn(
            [
                '-C', str(REPOSITORY_ROOT / 'wordpress' / '..'), 'rev-parse',
                BEHAVIOR_ROLLBACK_REF + '^{commit}',
            ],
            git_commands,
        )


class RehearsalInputTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name).resolve()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.command_log = self.root / 'docker-called'
        docker = self.bin / 'docker'
        docker.write_text(
            textwrap.dedent(
                r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8') as log:
    log.write(json.dumps(args) + '\n')
if args[:2] == ['image', 'inspect'] and '--format' in args:
    value = args[args.index('--format') + 1]
    if value == '{{.Id}}': print(os.environ['GAMA_RELEASE_IMAGE_ID'])
    elif value == '{{.Os}}/{{.Architecture}}': print(os.environ.get('FAKE_IMAGE_PLATFORM', 'linux/amd64'))
    elif 'org.opencontainers.image.revision' in value: print(os.environ['GAMA_RELEASE_GIT_SHA'])
    elif 'release-marker' in value: print(os.environ.get('FAKE_RELEASE_MARKER', 'development'))
    else: raise SystemExit('unexpected inspect format: ' + value)
elif os.environ.get('FAKE_PREEXISTING') == '1' and args and args[0] == 'ps':
    print('existing-owner-resource')
else:
    raise SystemExit(99)
'''
            ),
            encoding='utf-8',
        )
        docker.chmod(0o755)
        self.environment = os.environ.copy()
        self.environment['PATH'] = str(self.bin) + os.pathsep + self.environment['PATH']
        self.environment['FAKE_COMMAND_LOG'] = str(self.command_log)
        for name in (
            'GAMA_RELEASE_IMAGE_ID', 'GAMA_RELEASE_GIT_SHA', 'GAMA_RELEASE_RUN_ID',
            'GAMA_RELEASE_RUN_ATTEMPT', 'GAMA_RELEASE_RECEIPT_DIR',
        ):
            self.environment.pop(name, None)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _run(self, script, environment=None):
        return subprocess.run(
            [str(script)], cwd=REPOSITORY_ROOT,
            env=self.environment if environment is None else environment,
            text=True, capture_output=True, check=False,
        )

    def test_both_rehearsals_reject_missing_candidate_before_docker(self):
        for script in (STAGING_REHEARSAL, PRODUCTION_REHEARSAL):
            with self.subTest(script=script.name):
                result = self._run(script)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('GAMA_RELEASE_IMAGE_ID', result.stderr)
                self.assertFalse(self.command_log.exists())

    def test_existing_receipt_is_refused_before_docker(self):
        receipt_directory = self.root / 'receipts'
        receipt_directory.mkdir()
        environment = self.environment.copy()
        environment.update(
            {
                'GAMA_RELEASE_IMAGE_ID': IMAGE_A,
                'GAMA_RELEASE_GIT_SHA': GIT_SHA,
                'GAMA_RELEASE_RUN_ID': '123456',
                'GAMA_RELEASE_RUN_ATTEMPT': '2',
                'GAMA_RELEASE_RECEIPT_DIR': str(receipt_directory),
            }
        )
        for script, receipt_name in (
            (STAGING_REHEARSAL, 'release-regression.json'),
            (PRODUCTION_REHEARSAL, 'production-runtime.json'),
        ):
            with self.subTest(script=script.name):
                receipt = receipt_directory / receipt_name
                receipt.write_text('{}\n', encoding='utf-8')
                result = self._run(script, environment)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('overwrite', result.stderr.lower())
                self.assertFalse(self.command_log.exists())
                receipt.unlink()

    def test_preexisting_namespace_refusal_never_installs_cleanup(self):
        receipt_directory = self.root / 'owned-receipts'
        receipt_directory.mkdir()
        head = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=REPOSITORY_ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        environment = self.environment.copy()
        environment.update(
            {
                'GAMA_RELEASE_IMAGE_ID': IMAGE_A,
                'GAMA_RELEASE_GIT_SHA': head,
                'GAMA_RELEASE_RUN_ID': '123456',
                'GAMA_RELEASE_RUN_ATTEMPT': '2',
                'GAMA_RELEASE_RECEIPT_DIR': str(receipt_directory),
                'FAKE_PREEXISTING': '1',
            }
        )

        for script in (STAGING_REHEARSAL, PRODUCTION_REHEARSAL):
            with self.subTest(script=script.name):
                if self.command_log.exists():
                    self.command_log.unlink()
                result = self._run(script, environment)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('already exists', result.stderr)
                commands = [
                    json.loads(line) for line in self.command_log.read_text().splitlines()
                ]
                self.assertFalse(any('compose' in command or 'rm' in command for command in commands))

    def test_native_rehearsal_override_requires_matching_development_image(self):
        receipt_directory = self.root / 'native-receipts'
        receipt_directory.mkdir()
        head = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=REPOSITORY_ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        base_environment = self.environment.copy()
        base_environment.update(
            {
                'GAMA_RELEASE_IMAGE_ID': IMAGE_A,
                'GAMA_RELEASE_GIT_SHA': head,
                'GAMA_RELEASE_RUN_ID': '123456',
                'GAMA_RELEASE_RUN_ATTEMPT': '2',
                'GAMA_RELEASE_RECEIPT_DIR': str(receipt_directory),
                'GAMA_RELEASE_DEVELOPMENT_PLATFORM': 'linux/arm64',
                'FAKE_IMAGE_PLATFORM': 'linux/arm64',
                'FAKE_RELEASE_MARKER': 'development',
                'FAKE_PREEXISTING': '1',
            }
        )
        for script in (STAGING_REHEARSAL, PRODUCTION_REHEARSAL):
            with self.subTest(script=script.name, case='matching-development'):
                if self.command_log.exists():
                    self.command_log.unlink()
                accepted = self._run(script, base_environment)
                self.assertIn('already exists', accepted.stderr)

            with self.subTest(script=script.name, case='release-cannot-bypass'):
                if self.command_log.exists():
                    self.command_log.unlink()
                release_environment = base_environment.copy()
                release_environment['FAKE_RELEASE_MARKER'] = 'release'
                refused = self._run(script, release_environment)
                self.assertNotEqual(0, refused.returncode)
                self.assertIn('development', refused.stderr.lower())
                commands = [
                    json.loads(line) for line in self.command_log.read_text().splitlines()
                ]
                self.assertFalse(any(command and command[0] in {'build', 'compose', 'run', 'exec', 'rm'} for command in commands))

            with self.subTest(script=script.name, case='platform-mismatch'):
                if self.command_log.exists():
                    self.command_log.unlink()
                mismatch_environment = base_environment.copy()
                mismatch_environment['FAKE_IMAGE_PLATFORM'] = 'linux/amd64'
                refused = self._run(script, mismatch_environment)
                self.assertNotEqual(0, refused.returncode)
                self.assertIn('platform does not match', refused.stderr.lower())
                commands = [
                    json.loads(line) for line in self.command_log.read_text().splitlines()
                ]
                self.assertFalse(any(command and command[0] in {'build', 'compose', 'run', 'exec', 'rm'} for command in commands))

    def test_unset_native_override_still_requires_amd64(self):
        receipt_directory = self.root / 'default-platform-receipts'
        receipt_directory.mkdir()
        head = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=REPOSITORY_ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        environment = self.environment.copy()
        environment.update(
            {
                'GAMA_RELEASE_IMAGE_ID': IMAGE_A,
                'GAMA_RELEASE_GIT_SHA': head,
                'GAMA_RELEASE_RUN_ID': '123456',
                'GAMA_RELEASE_RUN_ATTEMPT': '2',
                'GAMA_RELEASE_RECEIPT_DIR': str(receipt_directory),
                'FAKE_IMAGE_PLATFORM': 'linux/arm64',
                'FAKE_RELEASE_MARKER': 'development',
            }
        )
        environment.pop('GAMA_RELEASE_DEVELOPMENT_PLATFORM', None)

        for script in (STAGING_REHEARSAL, PRODUCTION_REHEARSAL):
            with self.subTest(script=script.name):
                if self.command_log.exists():
                    self.command_log.unlink()
                result = self._run(script, environment)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('linux/amd64', result.stderr)


if __name__ == '__main__':
    unittest.main()
