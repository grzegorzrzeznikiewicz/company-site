#!/usr/bin/env python3
"""Build and seal one immutable WordPress release candidate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from wordpress.release.manifest import (  # noqa: E402
    ReleaseValidationError,
    validate_manifest,
)


RELEASE_PLATFORM = 'linux/amd64'
NATIVE_DEVELOPMENT_PLATFORM = 'linux/arm64'
EXPECTED_REPOSITORY = 'grzegorzrzeznikiewicz/company-site'
EXPECTED_WORKFLOW_ID = 351411087
EXPECTED_WORKFLOW_PATH = '.github/workflows/wordpress-ci.yml'
CANDIDATE_FIELDS = frozenset(
    {
        'schema_version',
        'candidate_type',
        'repository',
        'git_sha',
        'workflow_id',
        'workflow_path',
        'run_id',
        'run_attempt',
        'event',
        'ref',
        'platform',
        'image_id',
        'source',
    }
)
SOURCE_FIELDS = frozenset({'clean', 'fingerprint'})
RECEIPT_FIELDS = frozenset(
    {
        'schema_version',
        'name',
        'status',
        'image_id',
        'git_sha',
        'run_id',
        'run_attempt',
    }
)
RECEIPT_NAMES = ('release-regression', 'production-runtime')
IMAGE_PATTERN = re.compile(r'sha256:[0-9a-f]{64}')
GIT_SHA_PATTERN = re.compile(r'[0-9a-f]{40}')
READ_LIMIT = 64 * 1024


def _fail(message, cause=None):
    if cause is None:
        raise ReleaseValidationError(message)
    raise ReleaseValidationError(message) from cause


def _run(arguments, **kwargs):
    try:
        return subprocess.run(arguments, check=True, **kwargs)
    except (OSError, subprocess.CalledProcessError) as error:
        _fail('command failed: {0}'.format(arguments[0]), error)


def _command_output(arguments):
    return _run(arguments, text=True, stdout=subprocess.PIPE).stdout.strip()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate JSON key')
        result[key] = value
    return result


def _load_json(path, label):
    try:
        path = Path(path)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            _fail('{0} must be an absolute regular file'.format(label))
        if path.stat().st_size > READ_LIMIT:
            _fail('{0} is too large'.format(label))
        return json.loads(
            path.read_text(encoding='utf-8'),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: _fail('non-finite JSON number'),
        )
    except ReleaseValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        _fail('{0} is invalid JSON'.format(label), error)


def _environment_positive_integer(name):
    raw = os.environ.get(name, '')
    if not raw.isdigit() or int(raw) < 1:
        _fail('{0} must be a positive integer'.format(name))
    return int(raw)


def _require_exact_fields(value, fields, label):
    if type(value) is not dict or frozenset(value) != fields:
        _fail('{0} fields do not match the closed schema'.format(label))


def _require_pattern(value, pattern, label):
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail('{0} is invalid'.format(label))
    return value


def _inspect_image(image_id, git_sha, marker, platform):
    raw = _command_output(['docker', 'image', 'inspect', image_id])
    try:
        values = json.loads(raw, object_pairs_hook=_unique_object)
        if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
            _fail('Docker returned an invalid image inspection')
        image = values[0]
        labels = image.get('Config', {}).get('Labels', {})
        if type(labels) is not dict:
            _fail('Docker returned invalid image labels')
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
        _fail('Docker returned an invalid image inspection', error)

    if image.get('Id') != image_id:
        _fail('inspected image identity does not match the candidate')
    expected_os, expected_architecture = platform.split('/', 1)
    if (
        image.get('Os') != expected_os
        or image.get('Architecture') != expected_architecture
    ):
        _fail('candidate image platform must be {0}'.format(platform))
    if labels.get('org.opencontainers.image.revision') != git_sha:
        _fail('candidate image revision label does not match Git')
    if labels.get('com.gamasoftware.wordpress.release-marker') != marker:
        _fail('candidate image release marker is invalid')


def _source_fingerprint():
    raw_paths = _run(
        [
            'git', '-C', str(REPOSITORY_ROOT), 'ls-files', '--cached',
            '--others', '--exclude-standard', '-z',
        ],
        stdout=subprocess.PIPE,
    ).stdout
    digest = hashlib.sha256()
    for raw_path in sorted(part for part in raw_paths.split(b'\0') if part):
        try:
            relative = raw_path.decode('utf-8')
        except UnicodeDecodeError as error:
            _fail('source path is not valid UTF-8', error)
        path = REPOSITORY_ROOT / relative
        digest.update(len(raw_path).to_bytes(8, 'big'))
        digest.update(raw_path)
        if path.is_symlink():
            payload = os.readlink(str(path)).encode('utf-8')
            kind = b'L'
        elif path.is_file():
            try:
                payload = path.read_bytes()
            except OSError as error:
                _fail('could not fingerprint source content', error)
            kind = b'F'
        elif not path.exists():
            payload = b''
            kind = b'D'
        else:
            _fail('source contains an unsupported tracked object')
        digest.update(kind)
        digest.update(len(payload).to_bytes(8, 'big'))
        digest.update(payload)
    return digest.hexdigest()


def _ci_provenance(git_sha):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        _fail('release candidates require a clean GitHub Actions checkout')
    repository = os.environ.get('GITHUB_REPOSITORY')
    if repository != EXPECTED_REPOSITORY:
        _fail('GITHUB_REPOSITORY does not identify the trusted repository')
    if os.environ.get('GITHUB_SHA') != git_sha:
        _fail('GITHUB_SHA does not match the checked-out commit')
    workflow_id = _environment_positive_integer('GAMA_RELEASE_WORKFLOW_ID')
    if workflow_id != EXPECTED_WORKFLOW_ID:
        _fail('release workflow ID is not trusted')
    workflow_path = os.environ.get('GAMA_RELEASE_WORKFLOW_PATH')
    if workflow_path != EXPECTED_WORKFLOW_PATH:
        _fail('release workflow path is not trusted')
    event = os.environ.get('GITHUB_EVENT_NAME', '')
    ref = os.environ.get('GITHUB_REF', '')
    if event not in {'push', 'pull_request'}:
        _fail('GITHUB_EVENT_NAME is not an accepted source event')
    return {
        'repository': repository,
        'git_sha': git_sha,
        'workflow_id': workflow_id,
        'workflow_path': workflow_path,
        'run_id': _environment_positive_integer('GITHUB_RUN_ID'),
        'run_attempt': _environment_positive_integer('GITHUB_RUN_ATTEMPT'),
        'event': event,
        'ref': ref,
        'platform': RELEASE_PLATFORM,
    }


def _development_provenance(git_sha, platform):
    def positive_or_default(name):
        raw = os.environ.get(name, '1')
        return int(raw) if raw.isdigit() and int(raw) > 0 else 1

    return {
        'repository': os.environ.get('GITHUB_REPOSITORY', EXPECTED_REPOSITORY),
        'git_sha': git_sha,
        'workflow_id': positive_or_default('GAMA_RELEASE_WORKFLOW_ID'),
        'workflow_path': os.environ.get(
            'GAMA_RELEASE_WORKFLOW_PATH', EXPECTED_WORKFLOW_PATH
        ),
        'run_id': positive_or_default('GITHUB_RUN_ID'),
        'run_attempt': positive_or_default('GITHUB_RUN_ATTEMPT'),
        'event': os.environ.get('GITHUB_EVENT_NAME', 'push'),
        'ref': os.environ.get('GITHUB_REF', 'refs/heads/local-development'),
        'platform': platform,
    }


def _validate_new_output(path):
    output = Path(path)
    if not output.is_absolute() or output == Path('/') or output.exists():
        _fail('output must be an absolute new directory')
    if not output.parent.is_dir() or output.parent.is_symlink():
        _fail('output parent must be an existing regular directory')
    return output


def _create_output(path):
    output = _validate_new_output(path)
    try:
        output.mkdir(mode=0o700)
    except OSError as error:
        _fail('could not create output directory', error)
    return output


def _write_json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=True) + '\n'
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
            target.write(payload)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def build_candidate(arguments):
    _validate_new_output(arguments.output)
    if arguments.development_platform and not arguments.development_dirty:
        _fail('--development-platform requires --development-dirty')
    git_sha = _require_pattern(
        _command_output(['git', '-C', str(REPOSITORY_ROOT), 'rev-parse', 'HEAD']),
        GIT_SHA_PATTERN,
        'Git HEAD',
    )
    status_before = _command_output(
        ['git', '-C', str(REPOSITORY_ROOT), 'status', '--porcelain']
    )
    dirty = bool(status_before)
    if dirty and not arguments.development_dirty:
        _fail('release image requires a clean Git checkout')
    if not dirty and arguments.development_dirty:
        _fail('--development-dirty requires a dirty source checkout')

    candidate_type = 'development' if dirty else 'release'
    marker = 'development' if dirty else 'release'
    platform = arguments.development_platform or RELEASE_PLATFORM
    fingerprint_before = _source_fingerprint() if dirty else None
    provenance = (
        _development_provenance(git_sha, platform)
        if dirty
        else _ci_provenance(git_sha)
    )
    tag = 'gama-wordpress:candidate-{0}-{1}-{2}'.format(
        marker, platform.split('/', 1)[1], git_sha
    )
    with tempfile.TemporaryDirectory(prefix='gama-wordpress-candidate-') as temporary:
        iidfile = Path(temporary) / 'image-id'
        _run(
            [
                'docker', 'build', '--platform', platform,
                '--file', str(REPOSITORY_ROOT / 'wordpress/runtime/Dockerfile'),
                '--build-arg', 'GAMA_GIT_SHA={0}'.format(git_sha),
                '--build-arg', 'GAMA_RELEASE_MARKER={0}'.format(marker),
                '--tag', tag, '--iidfile', str(iidfile), str(REPOSITORY_ROOT),
            ]
        )
        try:
            image_id = iidfile.read_text(encoding='utf-8').strip()
        except OSError as error:
            _fail('Docker did not record the candidate image identity', error)
    _require_pattern(image_id, IMAGE_PATTERN, 'candidate image ID')
    _inspect_image(image_id, git_sha, marker, platform)
    if _command_output(
        ['git', '-C', str(REPOSITORY_ROOT), 'rev-parse', 'HEAD']
    ) != git_sha or _command_output(
        ['git', '-C', str(REPOSITORY_ROOT), 'status', '--porcelain']
    ) != status_before:
        _fail('source checkout changed while the candidate was built')
    if dirty and _source_fingerprint() != fingerprint_before:
        _fail('source content changed while the candidate was built')

    candidate = {
        'schema_version': 1,
        'candidate_type': candidate_type,
        **provenance,
        'image_id': image_id,
        'source': {
            'clean': not dirty,
            'fingerprint': fingerprint_before,
        },
    }
    output = _create_output(arguments.output)
    try:
        _write_json(output / 'candidate.json', candidate)
    except Exception:
        shutil.rmtree(str(output))
        raise
    print(str(output / 'candidate.json'))


def _validate_candidate(value):
    _require_exact_fields(value, CANDIDATE_FIELDS, 'candidate')
    if value.get('schema_version') != 1:
        _fail('candidate schema_version must be 1')
    if value.get('candidate_type') != 'release':
        _fail('development candidates cannot be sealed as releases')
    _require_exact_fields(value.get('source'), SOURCE_FIELDS, 'candidate source')
    if value['source'] != {'clean': True, 'fingerprint': None}:
        _fail('release candidate source must be clean')
    _require_pattern(value.get('git_sha'), GIT_SHA_PATTERN, 'candidate git_sha')
    _require_pattern(value.get('image_id'), IMAGE_PATTERN, 'candidate image_id')
    if value.get('platform') != RELEASE_PLATFORM:
        _fail('candidate platform must be linux/amd64')
    if value.get('repository') != EXPECTED_REPOSITORY:
        _fail('candidate repository is not trusted')
    if value.get('workflow_id') != EXPECTED_WORKFLOW_ID:
        _fail('candidate workflow ID is not trusted')
    if value.get('workflow_path') != EXPECTED_WORKFLOW_PATH:
        _fail('candidate workflow path is not trusted')
    probe_evidence = [
        {
            'name': name,
            'status': 'passed',
            'image_id': value['image_id'],
            'run_id': value.get('run_id'),
            'run_attempt': value.get('run_attempt'),
        }
        for name in RECEIPT_NAMES
    ]
    validate_manifest(
        {
            'schema_version': 1,
            'repository': value.get('repository'),
            'git_sha': value.get('git_sha'),
            'workflow_id': value.get('workflow_id'),
            'workflow_path': value.get('workflow_path'),
            'run_id': value.get('run_id'),
            'run_attempt': value.get('run_attempt'),
            'event': value.get('event'),
            'ref': value.get('ref'),
            'platform': value.get('platform'),
            'image_id': value.get('image_id'),
            'archive_sha256': '0' * 64,
            'packages': [
                {'name': name, 'version': '0'}
                for name in (
                    'wordpress', 'theme/gama-software', 'plugin/gama-contact',
                    'plugin/gama-seo', 'plugin/gama-security',
                    'plugin/gama-local-mailpit', 'plugin/gama-mail-transport',
                )
            ],
            'evidence': probe_evidence,
        }
    )
    return value


def _sha256_file(path):
    digest = hashlib.sha256()
    try:
        with path.open('rb') as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as error:
        _fail('could not hash saved candidate image', error)
    return digest.hexdigest()


def _validate_receipt(value, name, candidate):
    _require_exact_fields(value, RECEIPT_FIELDS, '{0} receipt'.format(name))
    if value.get('schema_version') != 1 or value.get('name') != name:
        _fail('{0} receipt identity is invalid'.format(name))
    if value.get('status') != 'passed':
        _fail('{0} receipt did not pass'.format(name))
    for field in ('image_id', 'git_sha', 'run_id', 'run_attempt'):
        if value.get(field) != candidate.get(field):
            _fail('{0} receipt {1} does not match candidate'.format(name, field))
    return {
        'name': name,
        'status': 'passed',
        'image_id': candidate['image_id'],
        'run_id': candidate['run_id'],
        'run_attempt': candidate['run_attempt'],
    }


def _load_receipts(receipt_directory, candidate):
    directory = Path(receipt_directory)
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        _fail('receipts must be an absolute regular directory')
    actual = {path.name for path in directory.iterdir()}
    expected = {name + '.json' for name in RECEIPT_NAMES}
    if actual != expected:
        _fail('receipts directory must contain exactly both receipt files')
    return [
        _validate_receipt(
            _load_json(directory / (name + '.json'), name + ' receipt'),
            name,
            candidate,
        )
        for name in RECEIPT_NAMES
    ]


PACKAGE_SCRIPT = r'''
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


def _derive_packages(image_id):
    raw = _command_output(
        [
            'docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'php',
            image_id, '-r', PACKAGE_SCRIPT,
        ]
    )
    try:
        packages = json.loads(raw, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, ValueError) as error:
        _fail('candidate package inventory is invalid JSON', error)
    return packages


def seal_candidate(arguments):
    _validate_new_output(arguments.output)
    candidate = _validate_candidate(_load_json(arguments.candidate, 'candidate'))
    receipts = _load_receipts(arguments.receipts, candidate)
    _inspect_image(
        candidate['image_id'], candidate['git_sha'], 'release', RELEASE_PLATFORM
    )
    packages = _derive_packages(candidate['image_id'])

    output = _create_output(arguments.output)
    try:
        image_path = output / 'image.tar'
        _run(
            [
                'docker', 'save', '--output', str(image_path),
                candidate['image_id'],
            ]
        )
        image_path.chmod(0o600)
        archive_sha256 = _sha256_file(image_path)
        manifest = validate_manifest(
            {
                'schema_version': 1,
                'repository': candidate['repository'],
                'git_sha': candidate['git_sha'],
                'workflow_id': candidate['workflow_id'],
                'workflow_path': candidate['workflow_path'],
                'run_id': candidate['run_id'],
                'run_attempt': candidate['run_attempt'],
                'event': candidate['event'],
                'ref': candidate['ref'],
                'platform': candidate['platform'],
                'image_id': candidate['image_id'],
                'archive_sha256': archive_sha256,
                'packages': packages,
                'evidence': receipts,
            }
        )
        _write_json(output / 'release.json', manifest)
    except Exception:
        shutil.rmtree(str(output))
        raise
    print(str(output))


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    build = subparsers.add_parser('build')
    build.add_argument('--output', required=True)
    build.add_argument('--development-dirty', action='store_true')
    build.add_argument(
        '--development-platform', choices=(NATIVE_DEVELOPMENT_PLATFORM,)
    )
    build.set_defaults(handler=build_candidate)
    seal = subparsers.add_parser('seal')
    seal.add_argument('--candidate', required=True)
    seal.add_argument('--receipts', required=True)
    seal.add_argument('--output', required=True)
    seal.set_defaults(handler=seal_candidate)
    return parser


def main():
    arguments = _parser().parse_args()
    try:
        arguments.handler(arguments)
    except ReleaseValidationError as error:
        print('Candidate refused: {0}'.format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
