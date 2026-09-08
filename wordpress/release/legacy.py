"""Allowlisted legacy operations sharing WordPress's durable host barrier."""
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

from wordpress.release.github_source import require, full_sha, json_object, REPOSITORY
from wordpress.release.host import (STATE_ROOT, OperationCleanupError, atomic, control_lock,
                                    control_state, fingerprint, protected, read_json)
from wordpress.release.host_ops import run

COMPOSE = Path('/srv/magento-devops/vm2/docker-compose.yml')
ENV_FILE = Path('/srv/magento-devops/vm2/.env')
IMAGE_ROOT = 'ghcr.io/grzegorzrzeznikiewicz/'
ENV_KEYS = {'MAILER_DSN', 'CONTACT_RECIPIENT', 'CONTACT_SENDER', 'COMPANY_API_APP_SECRET',
            'COMPANY_DB_PASSWORD', 'ADMIN_PASSWORD_HASH'}


def guard_entry(payload, environment, operation):
    """Read-only CI guard shared by trusted-main deploy and rollback callers."""
    require(operation in ('deploy', 'rollback'), 'unsupported legacy entry')
    source = payload.get('repository', {})
    allowed = (environment.get('GAMA_DEPLOYMENT_MODE') == 'legacy'
               and environment.get('GITHUB_REPOSITORY') == REPOSITORY
               and source.get('full_name') == REPOSITORY and source.get('fork') is False
               and source.get('default_branch') == 'main'
               and environment.get('GITHUB_REF') == 'refs/heads/main')
    event_name = environment.get('GITHUB_EVENT_NAME')
    sha = environment.get('GITHUB_SHA')
    if operation == 'deploy' and event_name == 'workflow_run':
        source_run = payload.get('workflow_run', {})
        allowed = (allowed and source_run.get('event') == 'push'
                   and source_run.get('head_branch') == 'main'
                   and source_run.get('conclusion') == 'success'
                   and source_run.get('head_repository', {}).get('full_name') == REPOSITORY
                   and source_run.get('head_repository', {}).get('fork') is False)
        sha = source_run.get('head_sha')
    else:
        allowed = allowed and event_name == 'workflow_dispatch'
    allowed = allowed and full_sha(sha)
    return {'allowed': bool(allowed), 'sha': sha if allowed else None}


def guard_main(arguments):
    require(len(arguments) == 2 and arguments[0] == 'guard', 'legacy guard command required')
    payload = {}
    if os.environ.get('GAMA_DEPLOYMENT_MODE') == 'legacy':
        payload = json_object(Path(os.environ['GITHUB_EVENT_PATH']).read_bytes())
    result = guard_entry(payload, os.environ, arguments[1])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('allowed=' + str(result['allowed']).lower() + '\n')
        if result['allowed']: output.write('sha=' + result['sha'] + '\n')


def _completion_history(root):
    history = read_json(root / 'legacy-completed.json', optional=True)
    if history is None: return {'schema_version': 1, 'operations': {}}
    require(type(history) is dict and set(history) == {'schema_version', 'operations'}
            and type(history['schema_version']) is int and history['schema_version'] == 1
            and type(history['operations']) is dict, 'invalid legacy completion history')
    for identifier, record in history['operations'].items():
        require(type(identifier) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', identifier)
                and type(record) is dict and set(record) == {'fingerprint', 'result'}
                and type(record['fingerprint']) is str and re.fullmatch('[a-f0-9]{64}', record['fingerprint'])
                and record['result'] == {'status': 'completed', 'operation_id': identifier},
                'invalid legacy completion record')
    return history


def validate(request):
    require(type(request) is dict and set(request) == {'operation_id', 'kind', 'git_sha', 'image_tag'},
            'closed legacy request required')
    require(type(request['operation_id']) is str
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', request['operation_id'])
            and request['kind'] in ('deploy', 'rollback') and full_sha(request['git_sha']),
            'invalid legacy operation')
    tag = request['image_tag']
    require(type(tag) is str and re.fullmatch(r'(?:sha-[a-f0-9]{40}|main-latest)', tag), 'invalid legacy tag')
    require(request['kind'] != 'deploy' or tag == 'sha-' + request['git_sha'], 'deploy source mismatch')
    return request


def execute(request, state_dir=STATE_ROOT, ops=None):
    request = validate(request)
    with control_lock(state_dir) as root:
        state = control_state(root)
        require(state['mode'] == 'legacy', 'legacy mode required under lock')
        require(state['incident'] is None, 'unresolved incident blocks legacy')
        previous = state['operation']
        require(previous is None or previous.get('status') == 'completed', 'unresolved operation blocks legacy')
        identity = fingerprint(request)
        history = _completion_history(root)
        completed = history['operations']
        # Preserve a completed pre-ledger legacy journal before a later request
        # can replace it. No missing older history is inferred or manufactured.
        if previous and previous.get('kind') in ('legacy-deploy', 'legacy-rollback'):
            prior_id, prior_identity = previous.get('operation_id'), previous.get('fingerprint')
            require(type(prior_id) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', prior_id)
                    and type(prior_identity) is str and re.fullmatch('[a-f0-9]{64}', prior_identity),
                    'invalid previous legacy identity')
            record = {'fingerprint': prior_identity, 'result': {'status': 'completed', 'operation_id': prior_id}}
            require(prior_id not in completed or completed[prior_id] == record, 'legacy journal/history conflict')
            if prior_id not in completed:
                completed[prior_id] = record
                atomic(root / 'legacy-completed.json', history)
        if request['operation_id'] in completed:
            record = completed[request['operation_id']]
            require(record['fingerprint'] == identity, 'operation identity conflicts with legacy history')
            return record['result']
        if previous and previous.get('operation_id') == request['operation_id']:
            require(previous.get('fingerprint') == identity, 'operation identity conflict')
            return {'status': 'completed', 'operation_id': request['operation_id']}
        journal = {'status': 'mutating', 'operation_id': request['operation_id'],
                   'fingerprint': identity, 'kind': 'legacy-' + request['kind'],
                   'request': request, 'phase': 'mutation',
                   'previous_operation_id': previous.get('operation_id') if previous else None}
        atomic(root / 'operation.json', journal)
        try:
            ops.mutate(request)
            journal['phase'] = 'verification'; atomic(root / 'operation.json', journal)
            ops.verify(request)
            completed[request['operation_id']] = {
                'fingerprint': identity, 'result': {'status': 'completed', 'operation_id': request['operation_id']}}
            # Keep the current journal blocking until the completion is durable.
            atomic(root / 'legacy-completed.json', history)
            journal['status'] = 'completed'; atomic(root / 'operation.json', journal)
        except BaseException as error:
            interrupted = isinstance(error, (OperationCleanupError, KeyboardInterrupt, SystemExit))
            journal['status'] = 'interrupted' if interrupted else 'failed'
            journal['failure'] = type(error.__cause__ or error).__name__
            if isinstance(error, OperationCleanupError): journal['cleanup_failure'] = type(error).__name__
            atomic(root / 'operation.json', journal)
            atomic(root / 'incident.json', journal)
        return {'status': journal['status'], 'operation_id': request['operation_id']}


class LegacyOps:
    """Fixed VM2 Compose service commands; config is installed outside releases."""
    def __init__(self, config):
        require(type(config) is dict and set(config) == {'docker', 'environment'}, 'closed legacy config required')
        docker = protected(Path(config['docker']))
        require(docker.name == 'docker' and os.access(docker, os.X_OK), 'trusted Docker executable required')
        protected(COMPOSE); protected(ENV_FILE)
        require(ENV_FILE.stat().st_mode & 0o077 == 0, 'legacy env must be root-private')
        environment = config['environment']
        require(type(environment) is dict and set(environment) == ENV_KEYS
                and all(type(value) is str and value for value in environment.values()), 'complete legacy secret configuration required')
        self.docker, self.environment = str(docker), dict(environment)
        # Registry authentication must already be installed in root's Docker config.
        credentials = Path('/root/.docker/config.json')
        if credentials.exists():
            protected(credentials)
            require(credentials.stat().st_mode & 0o077 == 0, 'Docker credentials must be root-private')

    def _images(self, request):
        return {name: IMAGE_ROOT + repo + ':' + request['image_tag']
                for name, repo in [('personal-site', 'company-site'), ('company-api', 'company-site-backend')]}

    def _compose(self, *args):
        return [self.docker, 'compose', '--project-name', 'vm2', '--env-file', str(ENV_FILE),
                '--file', str(COMPOSE), *args]

    def _environment(self, request, *, raw_password=False):
        images = self._images(request)
        environment = dict(self.environment)
        if not raw_password:
            environment['COMPANY_DB_PASSWORD'] = urllib.parse.quote(environment['COMPANY_DB_PASSWORD'], safe='')
        if environment['MAILER_DSN'].startswith('MAILER_DSN='):
            environment['MAILER_DSN'] = environment['MAILER_DSN'][len('MAILER_DSN='):]
        environment.update(PERSONAL_APP_IMAGE=images['personal-site'], COMPANY_API_IMAGE=images['company-api'])
        return environment

    def mutate(self, request):
        for image in self._images(request).values(): run([self.docker, 'pull', image])
        run(self._compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '120', 'company-db'),
            env=self._environment(request, raw_password=True))
        run(self._compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '120', 'company-api', 'personal-site'),
            env=self._environment(request))

    def verify(self, request):
        environment = self._environment(request)
        for service, image in self._images(request).items():
            container = run(self._compose('ps', '-q', service), env=environment).strip()
            require(re.fullmatch('[a-f0-9]{12,64}', container), 'one running legacy container required')
            observed = json.loads(run([self.docker, 'inspect', container]))
            expected = json.loads(run([self.docker, 'image', 'inspect', image]))
            require(type(observed) is list and len(observed) == 1 and type(expected) is list and len(expected) == 1,
                    'unambiguous legacy image observations required')
            actual = observed[0]
            state = actual.get('State', {})
            require(actual.get('Config', {}).get('Image') == image and actual.get('Image') == expected[0].get('Id')
                    and state.get('Running') is True
                    and ('Health' not in state or isinstance(state['Health'], dict)
                         and state['Health'].get('Status') == 'healthy'),
                    'legacy image or health verification failed')


if __name__ == '__main__':
    try:
        guard_main(sys.argv[1:])
    except Exception as error:
        print('Legacy guard refused: ' + type(error).__name__, file=sys.stderr)
        sys.exit(1)
