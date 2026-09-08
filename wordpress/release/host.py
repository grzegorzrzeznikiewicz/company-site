"""Serialized host release state. All operational observations occur under flock.

Root is the trust boundary: even a root-owned leaf beneath a writable ancestor
is refused. A killed process leaves its journal; absence of a response is never
interpreted as permission to repeat a mutation.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from wordpress.release.github_source import (authorization_comment, full_sha,
                                             json_object, require, timestamp)
from wordpress.release.manifest import ReleaseValidationError

STATE_ROOT = Path('/srv/gama-wordpress-production/control')
IMAGE = r'ghcr\.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:[0-9a-f]{64}'
IDENTIFIER = r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}'


class OperationCleanupError(ReleaseValidationError):
    """Local or external mutation completion is uncertain; recovery must wait."""


def protected(path, *, directory=False):
    """Validate physical absolute ancestry without resolving away symlinks."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute physical path required')
    for item in reversed((path, *path.parents)):
        try:
            value = item.lstat()
        except OSError as error:
            raise ValueError('protected path is unavailable') from error
        require(value.st_uid == 0 and not value.st_mode & 0o022
                and not stat.S_ISLNK(value.st_mode), 'untrusted path ownership or permissions')
        require(stat.S_ISDIR(value.st_mode) if item != path or directory
                else stat.S_ISREG(value.st_mode), 'unexpected protected path type')
        if item == path and not directory:
            require(value.st_nlink == 1, 'hard-linked control/tool file refused')
    return path


def read_json(path, optional=False):
    try:
        path.lstat()
    except FileNotFoundError:
        if optional: return None
        raise
    protected(path)
    with path.open('rb') as source:
        raw = source.read(1024 * 1024 + 1)
    require(len(raw) <= 1024 * 1024, 'control JSON too large')
    value = json_object(raw)
    require(type(value) is dict, 'control JSON object required')
    return value


def atomic(path, value):
    protected(path.parent, directory=True)
    if path.exists() or path.is_symlink(): protected(path)
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


def fingerprint(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def validate_request(request):
    recovery = type(request) is dict and request.get('kind') in ('code-rollback', 'routing-rollback')
    require(type(request) is dict and set(request) == {
        'operation_id', 'kind', 'git_sha', 'image', 'publication', 'authorization_ref'}
        | ({'recovery_authorization'} if recovery else set()),
        'release request fields do not match schema')
    require(type(request['operation_id']) is str and re.fullmatch(IDENTIFIER, request['operation_id']),
            'invalid operation identifier')
    require(request['kind'] in ('standard', 'first-cutover', 'code-rollback', 'routing-rollback'),
            'invalid operation kind')
    require(full_sha(request['git_sha']) and type(request['image']) is str
            and re.fullmatch(IMAGE, request['image']), 'immutable release identity required')
    publication = request['publication']
    require(type(publication) is dict and set(publication) == {
        'schema_version', 'source', 'image', 'image_id', 'archive_sha256',
        'manifest_sha256', 'platform'}, 'Task 4 publication required')
    require(type(publication['schema_version']) is int and publication['schema_version'] == 1
            and publication['image'] == request['image'] and publication['platform'] == 'linux/amd64'
            and type(publication['source']) is dict
            and publication['source'].get('provenance', {}).get('git_sha') == request['git_sha'],
            'publication binding mismatch')
    for field in ('image_id', 'archive_sha256', 'manifest_sha256'):
        require(type(publication[field]) is str and re.fullmatch(
            ('sha256:' if field == 'image_id' else '') + '[0-9a-f]{64}', publication[field]),
            'invalid publication checksum')
    auth = request['authorization_ref']
    require(auth is None if request['kind'] == 'standard' else
            type(auth) is str and re.fullmatch(IDENTIFIER, auth), 'explicit authorization reference required')
    # Detach the caller's object so concurrent callers cannot edit it mid-operation.
    return json_object(json.dumps(request, allow_nan=False))


def _window(request):
    authorization = request['publication']['source'].get('authorization')
    authorization_comment(authorization)
    require(authorization['authorization_id'] == request['authorization_ref']
            and authorization['git_sha'] == request['git_sha'], 'authorization reference mismatch')
    now = datetime.now(timezone.utc)
    require(timestamp(authorization['window_start']) <= now <= timestamp(authorization['window_end']),
            'cutover authorization is outside its actual UTC window')


def _backup(ops, scope, request):
    result = ops.backup(scope, request['operation_id'])
    require(type(result) is dict and result.get('verified') is True
            and result.get('scope') == scope and result.get('operation_id') == request['operation_id']
            and type(result.get('reference')) is str and result['reference']
            and type(result.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', result['sha256']),
            'verified bound off-host backup reference required')
    return result


@contextmanager
def control_lock(state_dir: Path = STATE_ROOT):
    """Hold the shared host lock through all caller mutation AND verification.

    Trusted legacy wrappers may use this context too, but must read mode/state
    only after entering it. Never use it as a check-and-release guard.
    """
    state_dir = protected(state_dir, directory=True)
    lock = state_dir / 'lock'
    if lock.exists() or lock.is_symlink(): protected(lock)
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        protected(lock)
        yield state_dir
    finally:
        os.close(descriptor)


def control_state(root):
    """Read protected state under the caller-held control_lock."""
    protected(root / 'mode')
    mode = (root / 'mode').read_text().strip()
    require(mode in ('off', 'legacy', 'wordpress'), 'missing or invalid deployment mode')
    return {'mode': mode, 'accepted': read_json(root / 'accepted.json', optional=True),
            'operation': read_json(root / 'operation.json', optional=True),
            'incident': read_json(root / 'incident.json', optional=True)}


def execute(request: dict, state_dir: Path, ops) -> dict:
    request = validate_request(request)
    with control_lock(state_dir) as root:
        return _locked(request, root, ops)


def _locked(request, root, ops):
    state = control_state(root)
    mode, accepted, journal, incident = (state[key] for key in ('mode', 'accepted', 'operation', 'incident'))
    recovery = request['kind'] in ('code-rollback', 'routing-rollback')
    require(incident is None or recovery, 'unresolved incident blocks release')
    require(journal is None or journal.get('status') == 'completed'
            or recovery and incident is not None and journal.get('status') == 'failed',
            'interrupted or failed operation blocks release')
    identity = fingerprint(request)
    if journal is not None and journal.get('status') == 'completed' and journal.get('operation_id') == request['operation_id']:
        require(journal.get('fingerprint') == identity, 'operation ID conflicts with recorded identity')
        return journal['result']
    completed = accepted.get('completed', {}) if accepted else {}
    require(type(completed) is dict, 'invalid accepted operation history')
    previous = completed.get(request['operation_id'])
    if previous:
        require(previous.get('fingerprint') == identity, 'operation ID conflicts with recorded identity')
        return previous['result']
    first = request['kind'] == 'first-cutover'
    require(mode == ('off' if first else 'wordpress') or recovery and mode == 'off',
            'mode does not permit operation')
    if first: _window(request)
    if not recovery and ops.current_main_sha() != request['git_sha']:
        return {'status': 'skipped', 'operation_id': request['operation_id'], 'reason': 'superseded-main'}
    ops.preflight(request)
    target = None
    if recovery:
        target = journal.get('recovery_target', journal) if journal is not None else None
        require(journal is not None and type(request['recovery_authorization']) is dict
                and type(target) is dict
                and request['recovery_authorization'].get('target_operation_id') == target.get('operation_id')
                and request['operation_id'] != journal.get('operation_id'),
                'recovery target is not the protected journal operation')
        if request['kind'] == 'code-rollback':
            require(target.get('kind') == 'standard'
                    and target['prior'].get('image') == request['image']
                    and target['prior'].get('git_sha') == request['git_sha'],
                    'code recovery must target the recorded previous image and SHA')
        else:
            require(target.get('kind') == 'first-cutover' and target['image'] == request['image']
                    and target['git_sha'] == request['git_sha'] and target.get('backup'),
                    'routing recovery must target the recorded first cutover')
    prior = ops.current_state()
    require(prior.get('platform') == 'linux/amd64', 'host platform mismatch')
    if first:
        require(accepted is None and prior.get('installed') is False and prior.get('resources') == {}
                and prior.get('namespace', {}) == {},
                'first cutover refuses accepted or partial installation')
    elif request['kind'] != 'routing-rollback':
        require(accepted is not None and accepted.get('schema_version') == 1
                and prior.get('installed') is True and prior.get('resources') == accepted.get('resources')
                and re.fullmatch(IMAGE, accepted.get('image', '')), 'accepted persistent installation required')
        if not recovery:
            require(prior.get('healthy') is True and prior.get('image') == accepted['image'],
                    'accepted application is not healthy or image changed')
            ops.verify(prior['image'])
    if recovery:
        target_resources = target['prior']['resources'] if request['kind'] == 'code-rollback' else (
            target.get('recovery_resources', accepted['resources'] if accepted else None))
        require(prior['resources'] == target_resources, 'recovery target resource identity mismatch')
    if accepted and prior.get('image') == accepted.get('image'):
        prior['git_sha'] = accepted['git_sha']
    elif not first:
        prior['git_sha'] = None
    journal = {'schema_version': 1, 'operation_id': request['operation_id'], 'kind': request['kind'],
               'git_sha': request['git_sha'], 'image': request['image'], 'fingerprint': identity,
               'prior': prior, 'status': 'preparing', 'backup': None}
    if incident is not None: journal['previous_incident'] = incident
    if recovery: journal['recovery_target'] = target
    atomic(root / 'operation.json', journal)
    # Every failure after durable intent, even during backup, remains a barrier.
    mutated = False
    try:
        if not recovery:
            journal['backup'] = _backup(ops, 'legacy' if first else 'wordpress', request)
        require(ops.current_state()['resources'] == prior['resources'], 'persistent resources changed during backup')
        journal['status'] = 'mutating'; atomic(root / 'operation.json', journal)
        mutated = True
        if request['kind'] == 'routing-rollback':
            ops.switch_routing('legacy', request['operation_id'])
            ops.verify('legacy')
        else:
            ops.deploy(request['image'], bootstrap=first)
            if first:
                ops.verify(request['image'], public=False)
                journal['wordpress_backup'] = _backup(ops, 'wordpress', request)
                atomic(root / 'operation.json', journal)
                ops.switch_routing('wordpress', request['operation_id'])
            ops.verify(request['image'])
        current = ops.current_state()
        journal['recovery_resources'] = current['resources']
        if not first:
            require(current['resources'] == prior['resources'], 'persistent resources changed during release')
        result = {'status': 'completed', 'operation_id': request['operation_id']}
        completed[request['operation_id']] = {'fingerprint': identity, 'result': result}
        # Acceptance and completion are separate fsync writes; any crash between
        # them conservatively leaves a blocking journal, never repeatable intent.
        if request['kind'] != 'routing-rollback':
            atomic(root / 'accepted.json', {'schema_version': 1, 'image': request['image'],
                   'git_sha': request['git_sha'], 'resources': current['resources'], 'completed': completed})
        elif accepted is not None:
            accepted['completed'] = completed
            atomic(root / 'accepted.json', accepted)
        journal['status'] = 'completed'; journal['result'] = result
        atomic(root / 'operation.json', journal)
        if recovery:
            barrier = incident or {'schema_version': 1, 'failure': 'ManualRecovery',
                                   'target_operation_id': request['recovery_authorization']['target_operation_id']}
            barrier['manual_recovery'] = result
            atomic(root / 'incident.json', barrier)
        return result
    except Exception as error:
        # Exception strings can contain credentials from a failed subprocess.
        # Record the stable failure class and stage, never raw external output.
        unsafe_cleanup = isinstance(error, OperationCleanupError)
        original_error = error.__cause__ if unsafe_cleanup and error.__cause__ is not None else error
        journal['failure'] = type(original_error).__name__
        journal['failure_phase'] = journal['status']
        journal['recovery'] = 'not-attempted'
        journal['status'] = 'interrupted' if unsafe_cleanup else 'failed'
        if unsafe_cleanup: journal['cleanup_failure'] = type(error).__name__
        if first and not unsafe_cleanup:
            try: journal['recovery_resources'] = ops.current_state()['resources']
            except Exception: pass  # No observation means no permission to invent a target.
        atomic(root / 'operation.json', journal)
        atomic(root / 'incident.json', journal)
        if mutated and not unsafe_cleanup and request['kind'] != 'routing-rollback':
            try:
                if first:
                    ops.switch_routing('legacy', request['operation_id']); ops.verify('legacy')
                elif request['kind'] != 'routing-rollback':
                    require(ops.current_state()['resources'] == prior['resources'], 'recovery resource mismatch')
                    ops.deploy(prior['image'], bootstrap=False); ops.verify(prior['image'])
                    require(ops.current_state()['resources'] == prior['resources'], 'recovery resource mismatch')
                journal['recovery'] = 'recovered'
            except Exception as recovery_error:
                journal['recovery'] = 'failed'
                journal['recovery_failure'] = type(recovery_error).__name__
                if isinstance(recovery_error, OperationCleanupError):
                    journal['status'] = 'interrupted'
                    journal['cleanup_failure'] = type(recovery_error).__name__
        result = {'status': 'failed', 'operation_id': request['operation_id'], 'recovery': journal['recovery']}
        journal['result'] = result
        atomic(root / 'operation.json', journal); atomic(root / 'incident.json', journal)
        return result
