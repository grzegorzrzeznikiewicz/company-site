"""Production operations: fixed argv, observed resources and explicit site probes.

Only off-host storage/restore and legacy infrastructure evidence are delegated
to operator-installed adapters. No adapter or configuration is installed here.
"""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
import urllib.parse
import urllib.request

from wordpress.release.github_source import (GitHubAPI, ROOT, json_object, require,
                                             timestamp, full_sha, positive, _repo)
from wordpress.release.promote import _recheck
from wordpress.release.host import (IMAGE, OperationCleanupError, fingerprint, protected,
                                    read_json, validate_backup_waiver, validate_smtp_deferral)
from wordpress.release.manifest import ReleaseValidationError

PROJECT = 'gama-wp-production'
ORIGIN = 'https://gama-software.com'
CUTOVER = '/usr/local/sbin/gama-wordpress-cutover'
ROUTING = '/usr/local/sbin/gama-wordpress-rollback-routing'
MAX_OUTPUT = 1024 * 1024


def recovery_comment(authorization):
    fields = {'authorization_id', 'promotion_run_id', 'promotion_run_attempt', 'operation_id',
              'target_operation_id', 'kind', 'git_sha', 'image', 'operators', 'window_start', 'window_end'}
    require(type(authorization) is dict and set(authorization) == fields, 'closed recovery authorization required')
    for field in ('authorization_id', 'operation_id', 'target_operation_id'):
        require(type(authorization[field]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', authorization[field]),
                'invalid recovery identifier')
    require(positive(authorization['promotion_run_id']) and type(authorization['promotion_run_attempt']) is int
            and authorization['promotion_run_attempt'] == 1
            and authorization['kind'] in ('code-rollback', 'routing-rollback')
            and full_sha(authorization['git_sha']) and type(authorization['image']) is str
            and re.fullmatch(IMAGE, authorization['image']), 'invalid recovery identity')
    operators = authorization['operators']
    require(type(operators) is list and operators, 'explicit recovery operators required')
    ids, logins = set(), set()
    for operator in operators:
        require(type(operator) is dict and set(operator) == {'id', 'login', 'type'}
                and positive(operator['id']) and operator['type'] == 'User'
                and type(operator['login']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', operator['login'])
                and operator['id'] not in ids and operator['login'] not in logins, 'distinct human recovery operators required')
        ids.add(operator['id']); logins.add(operator['login'])
    require(timestamp(authorization['window_start']) < timestamp(authorization['window_end']), 'invalid recovery window')
    return json.dumps(authorization, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _live_group_members(group):
    """Linux observation, including descendants after the group leader exits.

    Exited zombies cannot mutate; their reaping belongs to their parent/init.
    Missing/inaccessible procfs is uncertainty, never proof of quiescence.
    """
    members = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            fields = (entry / 'stat').read_text().rpartition(')')[2].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        require(len(fields) >= 4, 'process-group inspection is incomplete')
        if int(fields[2]) == group and int(fields[3]) == group and fields[0] not in ('Z', 'X'):
            members.append(int(entry.name))
    return members


def _terminate_group(process):
    """Stop only this run's new session/group and prove no member can mutate."""
    deadline = time.monotonic() + 5
    while True:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if not _live_group_members(process.pid):
            # Reaping the leader is separate from observing its descendants.
            process.wait(timeout=max(.1, deadline - time.monotonic()))
            return
        require(time.monotonic() < deadline, 'operational group did not terminate')
        time.sleep(.01)


def run(argv, *, data=None, timeout=600, env=None, external_mutation=False):
    protected(Path(argv[0]))
    require(os.access(argv[0], os.X_OK), 'operational tool is not executable')
    environment = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin',
                   'LANG': 'C.UTF-8', 'HOME': '/root'}
    if env: environment.update(env)
    process = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=environment, start_new_session=True)
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        raw = json.dumps(data, sort_keys=True, separators=(',', ':')).encode() if data is not None else b''
        require(len(raw) <= MAX_OUTPUT, 'adapter request too large')
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            sent = 0
            if data is not None:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'operational tool timed out')
                for key, events in selector.select(min(remaining, 1)):
                    if key.fileobj == process.stdin:
                        try:
                            sent += os.write(process.stdin.fileno(), raw[sent:sent+4096])
                        except BrokenPipeError as error:
                            raise ReleaseValidationError('adapter did not consume its bound input') from error
                        if sent == len(raw):
                            selector.unregister(process.stdin); process.stdin.close()
                    else:
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            selector.unregister(process.stdout)
                        else:
                            output.extend(chunk)
                            require(len(output) <= MAX_OUTPUT, 'operational tool output exceeds bound')
            # Observe without reaping: retain the leader PID until all error
            # cleanup is finished, so its process-group identity cannot be reused.
            while True:
                ended = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if ended is not None: break
                require(time.monotonic() < deadline, 'operational tool timed out')
                time.sleep(.01)
            require(ended.si_code == os.CLD_EXITED and ended.si_status == 0,
                    'operational tool failed (output withheld)')
        result = output.decode('utf-8')
        process.wait()
        return result
    except BaseException as error:
        try:
            _terminate_group(process)
        except Exception:
            # Reap our killed leader if possible, but do not confuse this with
            # proof about descendants when group inspection/termination failed.
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: pass
            # Do not let a host transaction start rollback against an ambiguous
            # surviving group. Preserve the original error as the explicit cause.
            raise OperationCleanupError('operational process cleanup could not be verified') from error
        if external_mutation:
            # A stopped client is not evidence that a daemon or external routing
            # operation completed. Only a successful synchronous invocation is.
            raise OperationCleanupError('external mutation completion is unknown') from error
        raise
    finally:
        if process.stdin and not process.stdin.closed: process.stdin.close()
        process.stdout.close()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(); self.links = []; self.images = []; self.forms = []; self.robots = []
        self.nav = False; self.inputs = {}; self.logo = None
        self.feed(raw)

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if tag == 'img' and a.get('src'): self.images.append(a['src'])
        if tag == 'img' and 'custom-logo' in a.get('class', '').split(): self.logo = a.get('src')
        if tag in ('input', 'textarea') and a.get('name'): self.inputs[a['name']] = a
        if tag == 'nav' or a.get('role') == 'navigation': self.nav = True
        if tag == 'form': self.forms.append(a)
        if tag == 'meta' and a.get('name', '').lower() == 'robots': self.robots.append(a.get('content', ''))


class HostOps:
    def __init__(self, config, *, api=None):
        self.config, self.api = config, api
        self.request = None
        self.smtp_deferral = None

    def _tool(self, key):
        require(type(self.config.get(key)) is str, 'missing protected operational configuration: ' + key)
        return str(protected(Path(self.config[key])))

    def _docker(self, *args, external_mutation=False):
        return run([self._tool('docker'), *args], external_mutation=external_mutation)

    def _object(self, *args):
        value = json_object(self._docker(*args))
        require(type(value) is list and len(value) == 1 and type(value[0]) is dict,
                'Docker inspection must identify exactly one object')
        return value[0]

    def _api(self):
        if self.api is None:
            path = protected(Path(self._tool('github_token_file')))
            require(not path.stat().st_mode & 0o077, 'read credential file must be private')
            token = path.read_text().strip()
            require(0 < len(token) <= 4096, 'invalid read credential file')
            self.api = GitHubAPI(token)
        return self.api

    def current_main_sha(self):
        value = self._api().get(ROOT + '/git/ref/heads/main')
        sha = value.get('object', {}).get('sha')
        require(full_sha(sha), 'current main SHA unavailable')
        return sha

    def current_state(self):
        platform = self._docker('info', '--format', '{{.OSType}}/{{.Architecture}}').strip()
        require(platform in ('linux/amd64', 'linux/x86_64'), 'production host must be native linux/amd64')
        namespace = {}
        for kind, base, reserved in (
            ('containers', ('ps', '-aq'), 'name=^/?' + PROJECT + '[-_]'),
            ('networks', ('network', 'ls', '-q'), 'name=^' + PROJECT + '_default$'),
            ('volumes', ('volume', 'ls', '-q'), 'name=^' + PROJECT + '_(database|core|uploads)$'),
        ):
            labelled = self._docker(*base, '--filter', 'label=com.docker.compose.project=' + PROJECT).splitlines()
            named = self._docker(*base, '--filter', reserved).splitlines()
            identities = sorted(set(labelled + named) - {''})
            if identities: namespace[kind] = identities
        containers = {}
        for service in ('wordpress', 'db'):
            rows = self._docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                                '--filter', 'label=com.docker.compose.service=' + service).splitlines()
            require(len(rows) <= 1, 'ambiguous stable service containers')
            if rows:
                container = self._object('inspect', rows[0])
                labels = container.get('Config', {}).get('Labels', {})
                require(labels.get('com.docker.compose.project') == PROJECT
                        and labels.get('com.docker.compose.service') == service, 'foreign container')
                containers[service] = container
        names = self._docker('volume', 'ls', '-q', '--filter',
                             'label=com.docker.compose.project=' + PROJECT).splitlines()
        require(len(names) == len(set(names)), 'ambiguous persistent volumes')
        resources = {}
        for name in names:
            volume = self._object('volume', 'inspect', name)
            labels = volume.get('Labels') or {}
            logical = labels.get('com.docker.compose.volume')
            require(logical in ('database', 'core', 'uploads') and logical not in resources
                    and labels.get('com.docker.compose.project') == PROJECT
                    and volume.get('Name') == PROJECT + '_' + logical and volume['Name'] == name
                    and volume.get('Driver') == 'local' and volume.get('Scope') == 'local'
                    and type(volume.get('CreatedAt')) is str and volume['CreatedAt']
                    and type(volume.get('Mountpoint')) is str and volume['Mountpoint'].startswith('/'),
                    'foreign or ambiguous persistent volume')
            resources[logical] = {key: volume.get(key) for key in
                                 ('Name', 'CreatedAt', 'Driver', 'Mountpoint', 'Scope', 'Labels', 'Options')}
        if not resources and not containers:
            return {'installed': False, 'healthy': False, 'image': None,
                    'platform': 'linux/amd64', 'resources': {}, 'namespace': namespace}
        if set(resources) != {'database', 'core', 'uploads'} or set(containers) != {'wordpress', 'db'}:
            # Observation must remain possible after a failed first installation:
            # routing recovery does not require a working/full WordPress stack.
            return {'installed': False, 'healthy': False, 'image': None,
                    'platform': 'linux/amd64', 'resources': resources, 'namespace': namespace}
        for service, expected in [('db', {'/var/lib/mysql': 'database'}),
                                  ('wordpress', {'/var/www/html': 'core', '/var/www/html/wp-content/uploads': 'uploads'})]:
            mounts = containers[service].get('Mounts', [])
            require(type(mounts) is list and len(mounts) == len(expected), 'unexpected production mounts')
            for mount in mounts:
                logical = expected.get(mount.get('Destination'))
                require(logical is not None and mount.get('Type') == 'volume' and mount.get('RW') is True
                        and mount.get('Name') == resources[logical]['Name']
                        and mount.get('Source') == resources[logical]['Mountpoint'], 'persistent mount identity mismatch')
        wp = containers['wordpress']
        image = wp.get('Config', {}).get('Image')
        require(type(image) is str and re.fullmatch(IMAGE, image), 'current immutable image missing')
        healthy = all(c.get('State', {}).get('Running') is True
                      and c['State'].get('Health', {}).get('Status') == 'healthy' for c in containers.values())
        return {'installed': True, 'healthy': healthy, 'image': image,
                'platform': 'linux/amd64', 'resources': resources, 'namespace': namespace}

    def _repo(self):
        root = protected(Path(self.config['wordpress_root']), directory=True)
        # Helpers source no request-controlled shell. Validate their repository
        # dependencies and every executable they invoke through the fixed PATH.
        for name in ('bin/deploy-production', 'bin/rollback-production', 'bin/backup', 'deploy/compose.yaml'):
            protected(root / name)
        for executable in ('bash', 'env', 'sed', 'tail', 'tr', 'dirname', 'cat', 'mkdir',
                           'find', 'rmdir', 'date', 'chmod', 'sha256sum'):
            protected(Path('/usr/bin') / executable)
        return root

    def preflight(self, request):
        require(type(self.config) is dict, 'host integration is not configured')
        waiver = None
        if request['kind'] == 'first-cutover' and 'first_cutover_without_backup' in self.config:
            waiver = validate_backup_waiver(self.config['first_cutover_without_backup'], request)
        self.smtp_deferral = None
        if request['kind'] == 'first-cutover' and 'first_cutover_without_smtp' in self.config:
            self.smtp_deferral = validate_smtp_deferral(self.config['first_cutover_without_smtp'], request)
        required = {'docker', 'wordpress_root', 'env_file', 'github_token_file', 'smtp_recipient'}
        needs_backup = waiver is None and request['kind'] in ('standard', 'first-cutover')
        if needs_backup:
            required |= {'findmnt', 'backup_root', 'backup_source', 'backup_adapter',
                         'restore_max_age_seconds', 'minimum_retention_days'}
        require(type(self.config) is dict and required <= set(self.config), 'host integration is not configured')
        self.request = request
        self._repo()
        protected(Path(self.config['env_file']))
        require(not Path(self.config['env_file']).stat().st_mode & 0o077, 'production env must be private')
        self._tool('docker')
        require(type(self.config['smtp_recipient']) is str and re.fullmatch(
            r'[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+', self.config['smtp_recipient']),
            'explicit controlled SMTP recipient required')
        if needs_backup:
            require(type(self.config['minimum_retention_days']) is int and self.config['minimum_retention_days'] > 0
                    and type(self.config['restore_max_age_seconds']) is int and self.config['restore_max_age_seconds'] > 0,
                    'retention and restore freshness policy required')
        if request['kind'] in ('standard', 'first-cutover'):
            source = _recheck(request['publication']['source'], self._api())
            require(source['operation'] == request['kind'], 'source operation mismatch')
        else:
            self._recovery_gate(request)
        if needs_backup:
            self._mount()
            self._evidence('backup_adapter', 'preflight', {'scope': 'wordpress', 'checksums': {}})
        if request['kind'] == 'first-cutover':
            self._tool('legacy_adapter'); protected(Path(CUTOVER)); protected(Path(ROUTING))
            if waiver is not None: self._routing_evidence('prepare-routing')
        return waiver

    def _routing_evidence(self, action):
        """Routing-only proof is not evidence of a data backup or restore."""
        require(action in ('prepare-routing', 'verify-routing'), 'invalid routing evidence action')
        original = (self.request['recovery_authorization']['target_operation_id']
                    if self.request['kind'] == 'routing-rollback' else self.request['operation_id'])
        binding = {key: self.request[key] for key in ('operation_id', 'git_sha', 'image')}
        binding['deployment_operation_id'] = original
        result = json_object(run([self._tool('legacy_adapter'), action], data=binding))
        require(type(result) is dict and set(result) == {'binding_sha256', 'routing_recovery_reference'}
                and result['binding_sha256'] == fingerprint(binding)
                and type(result['routing_recovery_reference']) is str
                and 0 < len(result['routing_recovery_reference']) <= 2048
                and not any(ord(c) < 32 for c in result['routing_recovery_reference']),
                'bound legacy routing recovery proof required')
        return result

    def _recovery_gate(self, request):
        authorization = request['recovery_authorization']
        comment = recovery_comment(authorization)
        require(authorization['authorization_id'] == request['authorization_ref']
                and all(authorization[key] == request[key] for key in ('operation_id', 'kind', 'git_sha', 'image')),
                'recovery authorization request mismatch')
        api = self._api()
        run = api.get(ROOT + '/actions/runs/' + str(authorization['promotion_run_id']))
        workflow = api.get(ROOT + '/actions/workflows/wordpress-production-rollback.yml')
        _repo(run.get('repository')); _repo(run.get('head_repository'))
        require(positive(workflow.get('id')) and workflow.get('path') == '.github/workflows/wordpress-production-rollback.yml'
                and workflow.get('state') == 'active' and run.get('workflow_id') == workflow['id']
                and run.get('path') == workflow['path'] and run.get('event') == 'workflow_dispatch'
                and run.get('head_branch') == 'main' and full_sha(run.get('head_sha'))
                and run.get('id') == authorization['promotion_run_id'] and type(run.get('run_attempt')) is int
                and run['run_attempt'] == 1 and run.get('status') == 'in_progress' and run.get('conclusion') is None,
                'untrusted or reused recovery dispatch')
        require(timestamp(authorization['window_start']) <= timestamp(run.get('created_at'))
                <= datetime.now(timezone.utc) <= timestamp(authorization['window_end']), 'recovery window expired')
        ids = set()
        for operator in authorization['operators']:
            permission = api.get(ROOT + '/collaborators/' + operator['login'] + '/permission')
            require(permission.get('permission') in ('write', 'admin')
                    and permission.get('user', {}).get('id') == operator['id']
                    and permission.get('user', {}).get('login') == operator['login']
                    and permission.get('user', {}).get('type') == 'User', 'recovery operator is not eligible')
            ids.add(operator['id'])
        require(run.get('actor', {}).get('id') in ids and run.get('triggering_actor', {}).get('id') in ids,
                'unapproved recovery dispatch actor')
        name = 'wordpress-production-rollback'
        environment = api.get(ROOT + '/environments/' + name)
        require(positive(environment.get('id')) and environment.get('name') == name, 'recovery environment unavailable')
        policies = [p for p in environment.get('protection_rules', []) if p.get('type') == 'required_reviewers']
        require(len(policies) == 1 and type(policies[0].get('prevent_self_review')) is bool,
                'configured recovery review policy required')
        reviewers = policies[0].get('reviewers')
        require(type(reviewers) is list and reviewers, 'configured recovery reviewers required')
        owners = set()
        for entry in reviewers:
            user = entry.get('reviewer', {})
            require(entry.get('type') == 'User' and user.get('type') == 'User' and positive(user.get('id'))
                    and type(user.get('login')) is str, 'explicit human recovery reviewers required')
            owners.add((user['id'], user['login']))
        history = api.get(ROOT + '/actions/runs/' + str(run['id']) + '/approvals')
        require(type(history) is list, 'recovery approval history missing')
        relevant = [entry for entry in history if any(e.get('id') == environment['id'] and e.get('name') == name
                    for e in entry.get('environments', []))]
        require(len(relevant) == 1, 'ambiguous or missing recovery approval')
        approved = relevant[0]; owner = approved.get('user', {})
        require(approved.get('state') == 'approved' and owner.get('type') == 'User'
                and (owner.get('id'), owner.get('login')) in owners and approved.get('comment') == comment,
                'configured owner did not approve this exact recovery')
        if policies[0]['prevent_self_review']:
            require(owner['id'] not in (run['actor']['id'], run['triggering_actor']['id']),
                    'configured recovery self-review prevention violated')

    def _image(self, image, image_id=None, sha=None):
        result = self._object('image', 'inspect', image)
        labels = result.get('Config', {}).get('Labels', {})
        require(result.get('Os') == 'linux' and result.get('Architecture') == 'amd64'
                and labels.get('com.gamasoftware.wordpress.release-marker') == 'release'
                and full_sha(labels.get('org.opencontainers.image.revision'))
                and image in result.get('RepoDigests', [])
                and (image_id is None or result.get('Id') == image_id)
                and (sha is None or labels.get('org.opencontainers.image.revision') == sha),
                'published image identity/platform/revision mismatch')
        return result

    def _mount(self):
        root = protected(Path(self.config['backup_root']), directory=True)
        require(type(self.config['backup_source']) is str and self.config['backup_source'], 'backup source is required')
        observed = run([self._tool('findmnt'), '-n', '-o', 'SOURCE', '--target', str(root)]).strip()
        target = run([self._tool('findmnt'), '-n', '-o', 'TARGET', '--target', str(root)]).strip()
        require(observed == self.config['backup_source'] and target == str(root), 'backup mount/source mismatch')
        return root

    def _evidence(self, tool, action, extra):
        binding = {'operation_id': self.request['operation_id'], 'git_sha': self.request['git_sha'],
                   'image': self.request['image'], 'resources': self.current_state()['resources'],
                   'backup_source': self.config['backup_source'], **extra}
        result = json_object(run([self._tool(tool), action], data=binding))
        fields = {'binding_sha256', 'reference', 'sha256', 'offhost_uri', 'encrypted',
                  'retention_days', 'created_utc', 'restore_verified_utc', 'routing_recovery_reference'}
        require(type(result) is dict and set(result) == fields
                and result['binding_sha256'] == fingerprint(binding), 'unbound infrastructure evidence')
        for name in ('reference', 'offhost_uri'):
            require(type(result[name]) is str and 0 < len(result[name]) <= 2048
                    and not any(ord(c) < 32 for c in result[name]), 'invalid off-host reference')
        uri = urllib.parse.urlsplit(result['offhost_uri'])
        require(uri.scheme in ('s3', 'https', 'ssh') and uri.hostname and not uri.username
                and not uri.password and not uri.query and not uri.fragment,
                'off-host evidence must have a credential-free remote URI')
        require(type(result['sha256']) is str and re.fullmatch('[0-9a-f]{64}', result['sha256'])
                and result['encrypted'] is True and type(result['retention_days']) is int
                and result['retention_days'] >= self.config['minimum_retention_days'],
                'encrypted retention/checksum proof missing')
        now = datetime.now(timezone.utc)
        require(0 <= (now-timestamp(result['created_utc'])).total_seconds() <= 300
                and 0 <= (now-timestamp(result['restore_verified_utc'])).total_seconds()
                <= self.config['restore_max_age_seconds'], 'stale backup or restore evidence')
        require(result['routing_recovery_reference'] is None if extra['scope'] != 'legacy' else
                type(result['routing_recovery_reference']) is str and result['routing_recovery_reference'],
                'legacy routing recovery record required')
        return {**result, 'verified': True, 'scope': extra['scope'], 'operation_id': self.request['operation_id']}

    def backup(self, scope, operation_id):
        require(operation_id == self.request['operation_id'], 'backup operation mismatch')
        if scope == 'legacy': return self._evidence('legacy_adapter', 'backup', {'scope': scope, 'checksums': {}})
        root = self._mount()
        destination = root / operation_id
        require(not destination.exists() and not destination.is_symlink(), 'backup destination already exists')
        state = self.current_state()
        require(state['healthy'], 'backup requires healthy existing WordPress')
        run([str(self._repo() / 'bin/backup'), '--project', PROJECT, str(destination)], env=self._helper_env())
        checksums = {}
        for name in ('database.sql', 'uploads.tar', 'manifest.txt'):
            path = protected(destination / name)
            digest = hashlib.sha256()
            with path.open('rb') as source:
                while chunk := source.read(1024*1024): digest.update(chunk)
            require(path.stat().st_size > 0, 'empty backup member')
            checksums[name] = digest.hexdigest()
        lines = protected(destination / 'SHA256SUMS').read_text().splitlines()
        require(set(lines) == {digest + '  ' + name for name, digest in checksums.items()}
                and len(lines) == 3, 'backup checksum inventory mismatch')
        manifest = {}
        for line in (destination / 'manifest.txt').read_text().splitlines():
            key, separator, value = line.partition('=')
            require(separator and key not in manifest, 'invalid backup manifest')
            manifest[key] = value
        require(manifest.get('source_project') == PROJECT
                and manifest.get('source_wordpress_image_ref') == state['image'], 'backup source image mismatch')
        require(self.current_state()['resources'] == state['resources'], 'backup resource identity changed')
        return self._evidence('backup_adapter', 'verify-backup', {'scope': scope,
                              'directory': str(destination), 'checksums': checksums})

    def deploy(self, image, bootstrap=False):
        require(type(image) is str and re.fullmatch(IMAGE, image), 'immutable deploy image required')
        if self.smtp_deferral is not None:
            validate_smtp_deferral(self.smtp_deferral, self.request)
            require(bootstrap and image == self.request['image'], 'SMTP deferral requires exact first bootstrap')
        self._docker('pull', '--platform', 'linux/amd64', image, external_mutation=True)
        self._image(image, self.request['publication']['image_id'] if image == self.request['image'] else None,
                    self.request['git_sha'] if image == self.request['image'] else None)
        root = self._repo()
        argv = [str(root / 'bin/deploy-production'), '--project', PROJECT,
                '--env-file', self.config['env_file'], '--image', image, '--http-port', '8000',
                '--confirm-image', image]
        if bootstrap: argv.append('--bootstrap')
        if self.smtp_deferral is not None: argv.append('--defer-smtp')
        argv.append('--mutation-only')
        run(argv, env=self._helper_env(), external_mutation=True)
        # The synchronous mutation returned successfully. Read-only health
        # timeout is now an ordinary verification failure eligible for recovery.
        deadline = time.monotonic() + 120
        while not self.current_state()['healthy']:
            require(time.monotonic() < deadline, 'deployed application did not become healthy')
            time.sleep(1)

    def _helper_env(self):
        docker = Path(self._tool('docker'))
        require(docker.name == 'docker', 'helper Docker executable must be named docker')
        paths = [str(docker.parent), '/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin']
        for path in paths: protected(Path(path), directory=True)
        path_value = ':'.join(paths)
        for name in ('docker', 'bash', 'env', 'sed', 'tail', 'tr', 'dirname', 'cat', 'mkdir',
                     'find', 'rmdir', 'date', 'chmod', 'sha256sum'):
            selected = shutil.which(name, path=path_value)
            require(selected is not None, 'required helper executable missing')
            protected(Path(selected))
        for name in ('shasum', 'git'):
            selected = shutil.which(name, path=path_value)
            if selected: protected(Path(selected))
        return {'PATH': path_value}

    def switch_routing(self, target, operation_id):
        require(operation_id == self.request['operation_id'], 'routing operation mismatch')
        if target == 'wordpress':
            run([CUTOVER, '--project', PROJECT, '--port', '8000', '--image', self.request['image'],
                 '--deployment-run-id', operation_id], external_mutation=True)
        else:
            require(target == 'legacy', 'invalid routing target')
            deployment_id = (self.request['recovery_authorization']['target_operation_id']
                             if self.request['kind'] == 'routing-rollback' else operation_id)
            run([ROUTING, '--target', 'legacy', '--deployment-run-id', deployment_id,
                 '--rollback-run-id', operation_id], external_mutation=True)

    def _http(self, path, public=True):
        require(path.startswith('/') and not path.startswith('//'), 'same-origin probe path required')
        origin = ORIGIN if public else 'http://127.0.0.1:8000'
        headers = {'Host': 'gama-software.com', 'X-Forwarded-Proto': 'https'} if not public else {}
        try:
            with urllib.request.build_opener(_NoRedirect()).open(
                    urllib.request.Request(origin + path, headers=headers), timeout=30) as response:
                body = response.read(MAX_OUTPUT+1)
                require(response.status == 200 and len(body) <= MAX_OUTPUT, 'site probe failed')
                return body, response.headers
        except OSError as error:
            if hasattr(error, 'close'): error.close()
            raise ReleaseValidationError('site HTTPS/content probe failed') from error

    def verify(self, image, public=True):
        if image == 'legacy':
            waiver = self.config.get('first_cutover_without_backup')
            if waiver is not None and self.request['kind'] in ('first-cutover', 'routing-rollback'):
                original = dict(self.request)
                if original['kind'] == 'routing-rollback':
                    original.update(kind='first-cutover',
                                    operation_id=original['recovery_authorization']['target_operation_id'],
                                    authorization_ref=waiver.get('authorization_ref') if type(waiver) is dict else None)
                validate_backup_waiver(waiver, original)
                self._routing_evidence('verify-routing')
            else:
                self._evidence('legacy_adapter', 'verify-routing', {'scope': 'legacy', 'checksums': {}})
            self._http('/', public=True)
            return
        state = self.current_state()
        require(state['installed'] and state['healthy'] and state['image'] == image, 'running image/health mismatch')
        info = self._image(image)
        container_ids = self._docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                                     '--filter', 'label=com.docker.compose.service=wordpress').splitlines()
        require(len(container_ids) == 1, 'ambiguous WordPress verification container')
        container = self._object('inspect', container_ids[0])
        require(container.get('Image') == info['Id'], 'running config ID mismatch')
        pages = {}
        for path in ('/', '/blog/', '/wp-login.php'):
            body, headers = self._http(path, public)
            text = body.decode('utf-8')
            require('text/html' in headers.get('Content-Type', '').lower(), 'HTML page required')
            require('noindex' not in headers.get('X-Robots-Tag', '').lower() if path != '/wp-login.php' else True,
                    'public page is not indexable')
            page = Page(text); pages[path] = page
            if path != '/wp-login.php': require(not any('noindex' in m.lower() for m in page.robots), 'page noindex')
        homepage = pages['/']
        require(homepage.nav and homepage.logo and any('/blog' in url for url in homepage.links)
                and any(urllib.parse.urlsplit(url).fragment == 'contact' for url in homepage.links),
                'homepage logo/navigation missing')
        require(any(form.get('id') == 'loginform' for form in pages['/wp-login.php'].forms)
                and {'log', 'pwd'} <= set(pages['/wp-login.php'].inputs)
                and any('gama-contact-form' in form.get('class', '').split() for form in homepage.forms)
                and {'name', 'email', 'phone', 'message', 'gama_contact_nonce'} <= set(homepage.inputs)
                and homepage.inputs['gama_contact_nonce'].get('value'), 'login/contact form missing')
        logo = urllib.parse.urlsplit(urllib.parse.urljoin(ORIGIN, homepage.logo))
        require(logo.scheme == 'https' and logo.netloc == 'gama-software.com', 'same-origin logo required')
        logo_body, logo_headers = self._http(logo.path, public)
        require(logo_body and logo_headers.get('Content-Type', '').startswith('image/'), 'logo image probe failed')
        rest_body, rest_headers = self._http('/wp-json/', public)
        require('application/json' in rest_headers.get('Content-Type', ''), 'contact REST index unavailable')
        route = json_object(rest_body).get('routes', {}).get('/gama-contact/v1/messages', {})
        require('POST' in route.get('methods', []), 'contact submission route missing')
        if self.smtp_deferral is not None:
            validate_smtp_deferral(self.smtp_deferral, self.request)
            require(image == self.request['image'], 'SMTP deferral image mismatch')
            # Keep the form, but prove the production transport rejects mail.
            # Short-circuit before wp_mail if config is present or plugin missing.
            self._docker('exec', container_ids[0], 'php', '-r',
                         'require "/var/www/html/wp-load.php"; exit(wp_get_environment_type() === "production" && function_exists("gama_mail_transport_config") && gama_mail_transport_config() === null && wp_mail($argv[1], "Gama deferred SMTP check", "Delivery must fail closed") === false ? 0 : 1);',
                         self.config['smtp_recipient'])
            return
        # PHP program text is constant; the approved mailbox is passed as argv.
        self._docker('exec', container_ids[0], 'php', '-r',
                     'require "/var/www/html/wp-load.php"; exit(wp_mail($argv[1], "Gama release verification", "Controlled release SMTP transport probe") ? 0 : 1);',
                     self.config['smtp_recipient'])
