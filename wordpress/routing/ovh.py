"""Root-installed, routing-only OVH adapters for the first WordPress cutover."""
import argparse
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


PROJECT = 'gama-wp-production'
IMAGE = r'ghcr\.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:[0-9a-f]{64}'
IDENTIFIER = r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}'
LEGACY = 'proxy_pass http://127.0.0.1:8090;'
WORDPRESS = 'proxy_pass http://127.0.0.1:8000;'


class RoutingError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise RoutingError(message)


def protected(path, uid, directory=False):
    try:
        info = path.lstat()
    except OSError as error:
        raise RoutingError('protected path unavailable') from error
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid == uid and not info.st_mode & 0o022, 'untrusted protected path')
    return path


def changed(original):
    """Replace the sole root-location upstream without touching API or TLS bytes."""
    try:
        source = original.decode('utf-8')
    except UnicodeDecodeError as error:
        raise RoutingError('site configuration is not UTF-8') from error
    locations = list(re.finditer(r'(?m)^([ \t]*)location[ \t]+/[ \t]*\{', source))
    require(len(locations) == 1, 'one root location required')
    start = locations[0].end()
    indent = locations[0].group(1)
    close = re.search(r'(?m)^' + re.escape(indent) + r'\}', source[start:])
    require(close is not None, 'root location is incomplete')
    end = start + close.start()
    body = source[start:end]
    directive = re.findall(r'(?m)^[ \t]*' + re.escape(LEGACY) + r'[ \t]*(?:#.*)?$', body)
    require(len(directive) == 1 and body.count(LEGACY) == 1 and source.count(LEGACY) == 1
            and WORDPRESS not in source, 'legacy upstream is ambiguous')
    return (source[:start] + body.replace(LEGACY, WORDPRESS, 1) + source[end:]).encode()


class Routing:
    def __init__(self, site, control, docker, nginx, systemctl, owner_uid=0,
                 enabled_site='/etc/nginx/sites-enabled/gama-software.com'):
        self.site, self.control = Path(site), Path(control)
        self.enabled_site = Path(enabled_site)
        self.docker, self.nginx, self.systemctl = map(str, (docker, nginx, systemctl))
        self.uid = owner_uid

    def _active_site(self):
        protected(self.enabled_site.parent, self.uid, directory=True)
        try:
            link = self.enabled_site.lstat()
            target = os.readlink(self.enabled_site)
        except OSError as error:
            raise RoutingError('active site link unavailable') from error
        require(stat.S_ISLNK(link.st_mode) and link.st_uid == self.uid
                and target == str(self.site), 'active site link does not target reviewed config')

    def _paths(self):
        self._active_site()
        protected(self.control.parent, self.uid, directory=True)
        protected(self.control, self.uid, directory=True)
        protected(self.site.parent, self.uid, directory=True)
        protected(self.site, self.uid)

    def _state_path(self, operation):
        require(type(operation) is str and re.fullmatch(IDENTIFIER, operation), 'invalid operation ID')
        return self.control / ('routing-' + operation + '.json')

    def _site_bytes(self):
        self._paths()
        return self.site.read_bytes()

    def _state(self, operation):
        protected(self.control.parent, self.uid, directory=True)
        protected(self.control, self.uid, directory=True)
        path = self._state_path(operation)
        protected(path, self.uid)
        require(not path.stat().st_mode & 0o077, 'routing record must be private')
        try:
            state = json.loads(path.read_text())
            require(type(state) is dict and set(state) == {'operation_id', 'git_sha', 'image',
                    'original_b64', 'original_sha256'}, 'invalid routing record')
            original = base64.b64decode(state['original_b64'], validate=True)
            require(state['operation_id'] == operation and
                    hashlib.sha256(original).hexdigest() == state['original_sha256'], 'routing record mismatch')
            changed(original)
            return path, state, original
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            raise RoutingError('invalid routing record') from error

    def _binding(self, binding, prepare=False):
        require(type(binding) is dict and set(binding) == {'operation_id', 'git_sha', 'image',
                'deployment_operation_id'}, 'malformed routing request')
        for key in ('operation_id', 'deployment_operation_id'):
            self._state_path(binding[key])
        require(type(binding['git_sha']) is str and re.fullmatch(r'[0-9a-f]{40}', binding['git_sha'])
                and type(binding['image']) is str and re.fullmatch(IMAGE, binding['image']),
                'invalid routing identity')
        if prepare:
            require(binding['operation_id'] == binding['deployment_operation_id'],
                    'prepare must bind the deployment operation')
        return hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def _proof(self, binding, path, digest):
        return {'binding_sha256': digest, 'routing_recovery_reference': str(path)}

    def prepare(self, binding):
        digest = self._binding(binding, prepare=True)
        original = self._site_bytes()
        path = self._state_path(binding['operation_id'])
        if path.exists() or path.is_symlink():
            _, state, saved = self._state(binding['operation_id'])
            require(state['git_sha'] == binding['git_sha'] and state['image'] == binding['image']
                    and original in (saved, changed(saved)), 'routing snapshot identity or site drift')
        else:
            changed(original)
            state = {'operation_id': binding['operation_id'], 'git_sha': binding['git_sha'],
                     'image': binding['image'], 'original_b64': base64.b64encode(original).decode(),
                     'original_sha256': hashlib.sha256(original).hexdigest()}
            raw = json.dumps(state, sort_keys=True, separators=(',', ':')).encode()
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            except OSError as error:
                raise RoutingError('cannot create routing snapshot') from error
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush(); os.fsync(stream.fileno())
            self._sync(self.control)
        return self._proof(binding, path, digest)

    def verify(self, binding):
        digest = self._binding(binding)
        path, state, original = self._state(binding['deployment_operation_id'])
        require(state['git_sha'] == binding['git_sha'] and state['image'] == binding['image'],
                'routing snapshot identity mismatch')
        require(self._site_bytes() == original, 'legacy route was not restored')
        self._command([self.nginx, '-t'])
        return self._proof(binding, path, digest)

    @staticmethod
    def _command(argv):
        try:
            subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=30)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise RoutingError('operator command failed: ' + Path(argv[0]).name) from error

    @staticmethod
    def _sync(path):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def _write_site(self, content):
        self._paths()
        mode = stat.S_IMODE(self.site.stat().st_mode)
        fd, name = tempfile.mkstemp(prefix='.gama-routing-', dir=self.site.parent)
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.site)
            self._sync(self.site.parent)
        finally:
            if os.path.exists(name): os.unlink(name)

    @contextmanager
    def lock(self):
        protected(self.control.parent, self.uid, directory=True)
        protected(self.control, self.uid, directory=True)
        path = self.control / 'routing.lock'
        try:
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            protected(path, self.uid)
            require(not path.stat().st_mode & 0o077, 'routing lock must be private')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            if 'fd' in locals(): os.close(fd)

    def _activate(self):
        self._command([self.nginx, '-t'])
        self._command([self.systemctl, 'reload', 'nginx'])

    def _container(self, image, sha):
        def docker(*args):
            try:
                return subprocess.run([self.docker, *args], check=True, capture_output=True,
                                      text=True, timeout=30).stdout
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise RoutingError('Docker inspection failed') from error
        ids = docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                     '--filter', 'label=com.docker.compose.service=wordpress').splitlines()
        require(len(ids) == 1 and re.fullmatch(r'[A-Za-z0-9]+', ids[0]), 'stable WordPress container is ambiguous')
        try:
            objects = json.loads(docker('inspect', ids[0]))
            require(type(objects) is list and len(objects) == 1, 'ambiguous Docker inspection')
            container = objects[0]
            labels = container['Config']['Labels']
            require(labels.get('com.docker.compose.project') == PROJECT
                    and labels.get('com.docker.compose.service') == 'wordpress'
                    and container['Config']['Image'] == image
                    and container['State']['Running'] is True
                    and container['State']['Health']['Status'] == 'healthy',
                    'WordPress image or readiness mismatch')
            images = json.loads(docker('image', 'inspect', image))
            require(type(images) is list and len(images) == 1
                    and images[0]['Id'] == container['Image']
                    and image in images[0]['RepoDigests']
                    and images[0]['Config']['Labels']['org.opencontainers.image.revision'] == sha,
                    'running image identity or revision mismatch')
        except (ValueError, TypeError, KeyError, IndexError) as error:
            raise RoutingError('invalid Docker inspection') from error

    def cutover(self, project, port, image, deployment_id):
        require(project == PROJECT and port == '8000' and type(image) is str
                and re.fullmatch(IMAGE, image), 'invalid cutover target')
        _, state, original = self._state(deployment_id)
        require(state['image'] == image, 'cutover image differs from snapshot')
        target = changed(original)
        current = self._site_bytes()
        require(current in (original, target), 'site configuration drift')
        self._container(image, state['git_sha'])
        try:
            if current != target: self._write_site(target)
            self._activate()
        except RoutingError as error:
            try:
                self._write_site(original)
                self._activate()
            except RoutingError as restore_error:
                raise RoutingError('cutover failed; legacy reload also failed') from restore_error
            raise RoutingError('cutover failed; legacy route restored') from error

    def rollback(self, target, deployment_id, rollback_id):
        require(target == 'legacy', 'invalid rollback target')
        self._state_path(rollback_id)
        _, _, original = self._state(deployment_id)
        current = self._site_bytes()
        require(current in (original, changed(original)), 'site configuration drift')
        if current != original: self._write_site(original)
        self._activate()


def main(kind):
    routing = Routing('/etc/nginx/sites-available/gama-software.com',
                      '/srv/gama-wordpress-production/control', '/usr/bin/docker',
                      '/usr/sbin/nginx', '/usr/bin/systemctl')
    try:
        with routing.lock():
            if kind == 'legacy':
                require(sys.argv[1:] in (['prepare-routing'], ['verify-routing']), 'invalid evidence action')
                raw = sys.stdin.read(1024 * 1024 + 1)
                require(len(raw) <= 1024 * 1024, 'routing request too large')
                def unique(pairs):
                    value = dict(pairs)
                    require(len(value) == len(pairs), 'duplicate routing request fields')
                    return value
                binding = json.loads(raw, object_pairs_hook=unique)
                result = routing.prepare(binding) if sys.argv[1] == 'prepare-routing' else routing.verify(binding)
                print(json.dumps(result, sort_keys=True, separators=(',', ':')))
            else:
                parser = argparse.ArgumentParser(allow_abbrev=False)
                if kind == 'cutover':
                    parser.add_argument('--project', required=True)
                    parser.add_argument('--port', required=True)
                    parser.add_argument('--image', required=True)
                    parser.add_argument('--deployment-run-id', required=True)
                    args = parser.parse_args()
                    routing.cutover(args.project, args.port, args.image, args.deployment_run_id)
                else:
                    parser.add_argument('--target', required=True)
                    parser.add_argument('--deployment-run-id', required=True)
                    parser.add_argument('--rollback-run-id', required=True)
                    args = parser.parse_args()
                    routing.rollback(args.target, args.deployment_run_id, args.rollback_run_id)
    except (RoutingError, ValueError, TypeError) as error:
        print('routing adapter refused: ' + str(error), file=sys.stderr)
        return 1
    return 0
