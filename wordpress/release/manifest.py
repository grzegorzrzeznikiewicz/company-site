"""Strict validation for immutable WordPress release manifests."""

import json
import re


class ReleaseValidationError(ValueError):
    """Raised when release data does not satisfy the trusted contract."""


_MANIFEST_FIELDS = frozenset(
    {
        'schema_version',
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
        'archive_sha256',
        'packages',
        'evidence',
    }
)
_PROVENANCE_FIELDS = (
    'repository',
    'git_sha',
    'workflow_id',
    'workflow_path',
    'run_id',
    'run_attempt',
    'event',
    'ref',
    'platform',
)
_PACKAGE_FIELDS = frozenset({'name', 'version'})
_PACKAGE_NAMES = frozenset(
    {
        'wordpress',
        'theme/gama-software',
        'plugin/gama-contact',
        'plugin/gama-seo',
        'plugin/gama-security',
        'plugin/gama-local-mailpit',
        'plugin/gama-mail-transport',
    }
)
_EVIDENCE_FIELDS = frozenset(
    {'name', 'status', 'image_id', 'run_id', 'run_attempt'}
)
_EVIDENCE_NAMES = frozenset({'release-regression', 'production-runtime'})

_GIT_SHA_PATTERN = re.compile(r'[0-9a-f]{40}')
_SHA256_PATTERN = re.compile(r'[0-9a-f]{64}')
_IMAGE_ID_PATTERN = re.compile(r'sha256:[0-9a-f]{64}')
_OWNER_PATTERN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?')
_REPOSITORY_PATTERN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?')
_WORKFLOW_PATH_PATTERN = re.compile(
    r'\.github/workflows/[A-Za-z0-9][A-Za-z0-9._-]*\.ya?ml'
)
_BRANCH_PATTERN = re.compile(
    r'[A-Za-z0-9_][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)*'
)
_PULL_REQUEST_REF_PATTERN = re.compile(r'refs/pull/[1-9][0-9]*/merge')
_VERSION_PATTERN = re.compile(r'[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}')


def _fail(message):
    raise ReleaseValidationError(message)


def _positive_id(value):
    return type(value) is int and value > 0


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate JSON key')
        result[key] = value
    return result


def _reject_json_constant(value):
    _fail('non-finite JSON number: {0}'.format(value))


def _require_dict(value, label):
    if type(value) is not dict:
        _fail('{0} must be an object'.format(label))


def _require_exact_fields(value, fields, label):
    _require_dict(value, label)
    actual = frozenset(value.keys())
    if actual != fields:
        missing = sorted(fields - actual)
        unknown = sorted(actual - fields, key=str)
        _fail(
            '{0} fields do not match schema (missing={1}, unknown={2})'.format(
                label, missing, unknown
            )
        )


def _require_full_match(value, pattern, label):
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail('{0} is invalid'.format(label))
    return value


def _validate_repository(value):
    if type(value) is not str or value.count('/') != 1:
        _fail('repository is invalid')
    owner, repository = value.split('/')
    if (
        _OWNER_PATTERN.fullmatch(owner) is None
        or _REPOSITORY_PATTERN.fullmatch(repository) is None
        or repository in {'.', '..'}
    ):
        _fail('repository is invalid')
    return value


def _validate_workflow_path(value):
    return _require_full_match(value, _WORKFLOW_PATH_PATTERN, 'workflow_path')


def _validate_push_ref(value):
    prefix = 'refs/heads/'
    if type(value) is not str or not value.startswith(prefix):
        _fail('ref is invalid for push')
    branch = value[len(prefix) :]
    if (
        _BRANCH_PATTERN.fullmatch(branch) is None
        or '..' in branch
        or '@{' in branch
        or any(part.endswith('.lock') for part in branch.split('/'))
    ):
        _fail('ref is invalid for push')
    return value


def _validate_event_and_ref(event, ref):
    if type(event) is not str:
        _fail('event is invalid')
    if event == 'push':
        return 'push', _validate_push_ref(ref)
    if event == 'pull_request':
        return 'pull_request', _require_full_match(
            ref, _PULL_REQUEST_REF_PATTERN, 'ref for pull_request'
        )
    _fail('event is invalid')


def _validate_provenance(value, require_fields=True):
    fields = frozenset(_PROVENANCE_FIELDS)
    if require_fields:
        _require_exact_fields(value, fields, 'provenance')

    repository = _validate_repository(value['repository'])
    git_sha = _require_full_match(value['git_sha'], _GIT_SHA_PATTERN, 'git_sha')
    workflow_id = value['workflow_id']
    run_id = value['run_id']
    run_attempt = value['run_attempt']
    for label, identifier in (
        ('workflow_id', workflow_id),
        ('run_id', run_id),
        ('run_attempt', run_attempt),
    ):
        if not _positive_id(identifier):
            _fail('{0} must be a positive integer'.format(label))
    workflow_path = _validate_workflow_path(value['workflow_path'])
    event, ref = _validate_event_and_ref(value['event'], value['ref'])
    if type(value['platform']) is not str or value['platform'] != 'linux/amd64':
        _fail('platform must be linux/amd64')

    return {
        'repository': repository,
        'git_sha': git_sha,
        'workflow_id': workflow_id,
        'workflow_path': workflow_path,
        'run_id': run_id,
        'run_attempt': run_attempt,
        'event': event,
        'ref': ref,
        'platform': 'linux/amd64',
    }


def _validate_packages(value):
    if type(value) is not list:
        _fail('packages must be an array')

    normalized = []
    names = []
    for index, package in enumerate(value):
        label = 'packages[{0}]'.format(index)
        _require_exact_fields(package, _PACKAGE_FIELDS, label)
        name = package['name']
        if type(name) is not str or name not in _PACKAGE_NAMES:
            _fail('{0}.name is invalid'.format(label))
        version = _require_full_match(
            package['version'], _VERSION_PATTERN, '{0}.version'.format(label)
        )
        names.append(name)
        normalized.append({'name': name, 'version': version})

    if len(names) != len(set(names)) or frozenset(names) != _PACKAGE_NAMES:
        _fail('packages must contain each required package exactly once')
    return normalized


def _validate_evidence(value, provenance, image_id):
    if type(value) is not list:
        _fail('evidence must be an array')

    normalized = []
    names = []
    for index, item in enumerate(value):
        label = 'evidence[{0}]'.format(index)
        _require_exact_fields(item, _EVIDENCE_FIELDS, label)
        name = item['name']
        if type(name) is not str or name not in _EVIDENCE_NAMES:
            _fail('{0}.name is invalid'.format(label))
        if type(item['status']) is not str or item['status'] != 'passed':
            _fail('{0}.status must be passed'.format(label))
        evidence_image_id = _require_full_match(
            item['image_id'], _IMAGE_ID_PATTERN, '{0}.image_id'.format(label)
        )
        run_id = item['run_id']
        run_attempt = item['run_attempt']
        if not _positive_id(run_id):
            _fail('{0}.run_id must be a positive integer'.format(label))
        if not _positive_id(run_attempt):
            _fail('{0}.run_attempt must be a positive integer'.format(label))
        if evidence_image_id != image_id:
            _fail('{0}.image_id does not match the release'.format(label))
        if run_id != provenance['run_id']:
            _fail('{0}.run_id does not match the release'.format(label))
        if run_attempt != provenance['run_attempt']:
            _fail('{0}.run_attempt does not match the release'.format(label))

        names.append(name)
        normalized.append(
            {
                'name': name,
                'status': 'passed',
                'image_id': evidence_image_id,
                'run_id': run_id,
                'run_attempt': run_attempt,
            }
        )

    if len(names) != len(set(names)) or frozenset(names) != _EVIDENCE_NAMES:
        _fail('evidence must contain each required result exactly once')
    return normalized


def parse_manifest(raw: str) -> dict:
    """Parse and validate a JSON release manifest without retaining aliases."""

    if type(raw) is not str:
        _fail('manifest JSON must be a string')
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except ReleaseValidationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise ReleaseValidationError('invalid manifest JSON') from error
    return validate_manifest(parsed)


def validate_manifest(manifest: dict, expected: dict = None) -> dict:
    """Validate a closed manifest and optionally bind all trusted provenance."""

    _require_exact_fields(manifest, _MANIFEST_FIELDS, 'manifest')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        _fail('schema_version must be 1')

    provenance = _validate_provenance(manifest, require_fields=False)
    image_id = _require_full_match(
        manifest['image_id'], _IMAGE_ID_PATTERN, 'image_id'
    )
    archive_sha256 = _require_full_match(
        manifest['archive_sha256'], _SHA256_PATTERN, 'archive_sha256'
    )
    packages = _validate_packages(manifest['packages'])
    evidence = _validate_evidence(manifest['evidence'], provenance, image_id)

    if expected is not None:
        validated_expected = _validate_provenance(expected)
        if validated_expected != provenance:
            _fail('manifest provenance does not match expected source')

    return {
        'schema_version': 1,
        **provenance,
        'image_id': image_id,
        'archive_sha256': archive_sha256,
        'packages': packages,
        'evidence': evidence,
    }


def artifact_name(manifest: dict) -> str:
    """Return the immutable artifact name for a validated manifest."""

    validated = validate_manifest(manifest)
    return 'wordpress-release-{0}-{1}-{2}'.format(
        validated['git_sha'], validated['run_id'], validated['run_attempt']
    )
