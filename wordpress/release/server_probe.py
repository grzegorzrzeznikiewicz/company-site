"""Fixed, unprivileged metadata probe sent through SSH stdin, never installed.

No application/configuration contents, database access, service commands, sudo,
network probes or directory enumeration. Presence is NOT operational readiness.
"""
import json
from pathlib import Path
import platform
import stat
import sys

PATHS = {
    'docker_cli': '/usr/bin/docker',
    'legacy_compose': '/srv/magento-devops/vm2/docker-compose.yml',
    'wordpress_tools': '/srv/gama-wordpress-production/tools/wordpress',
    'control_directory': '/srv/gama-wordpress-production/control',
    'host_config': '/srv/gama-wordpress-production/control/host-config.json',
    'cutover_adapter': '/usr/local/sbin/gama-wordpress-cutover',
    'rollback_adapter': '/usr/local/sbin/gama-wordpress-rollback-routing',
}


def path_state(path):
    try:
        mode = Path(path).lstat().st_mode
    except FileNotFoundError:
        return 'missing'
    except OSError:
        return 'unreadable'
    if stat.S_ISLNK(mode): return 'symlink'
    if stat.S_ISREG(mode): return 'file'
    if stat.S_ISDIR(mode): return 'directory'
    return 'other'


def collect():
    checks = {
        'linux': 'yes' if platform.system() == 'Linux' else 'no',
        'amd64': 'yes' if platform.machine().lower() in ('x86_64', 'amd64') else 'no',
        'python_compatible': 'yes' if sys.version_info >= (3, 10) else 'no',
    }
    checks.update({name: path_state(path) for name, path in PATHS.items()})
    return {'schema_version': 1, 'checks': checks}


if __name__ == '__main__':
    print(json.dumps(collect(), sort_keys=True))
