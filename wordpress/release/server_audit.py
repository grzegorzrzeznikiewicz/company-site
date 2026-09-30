"""One-shot owner-dispatched audit; pinned SSH, fixed probe, closed public report."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REPOSITORY = 'grzegorzrzeznikiewicz/company-site'
REF = 'refs/heads/feature/GSWEB-9'
FACTS = {'linux', 'amd64', 'python_compatible'}
PATH_FACTS = {'docker_cli', 'legacy_compose', 'wordpress_tools', 'control_directory',
              'host_config', 'cutover_adapter', 'rollback_adapter'}


class AuditError(Exception):
    """Only fixed, non-sensitive messages may cross the public log boundary."""


def allowed(env):
    expected = {
        'GITHUB_EVENT_NAME': 'workflow_dispatch', 'INPUT_OPERATION': 'read-only-audit',
        'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_REF': REF,
        'GITHUB_WORKFLOW_REF': REPOSITORY + '/.github/workflows/deploy.yml@' + REF,
        'GITHUB_ACTOR_ID': '50638878', 'GITHUB_TRIGGERING_ACTOR': 'grzegorzrzeznikiewicz',
        'GITHUB_RUN_ATTEMPT': '1', 'GAMA_DEPLOYMENT_MODE': 'off',
    }
    return (all(env.get(key) == value for key, value in expected.items())
            and re.fullmatch('[a-f0-9]{40}', env.get('GITHUB_SHA', '')) is not None)


def validate_report(raw):
    try:
        if len(raw) > 4096: raise ValueError()
        value = json.loads(raw)
        if (type(value) is not dict or set(value) != {'schema_version', 'checks'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1):
            raise ValueError()
        checks = value['checks']
        if type(checks) is not dict or set(checks) != FACTS | PATH_FACTS: raise ValueError()
        for key, state in checks.items():
            states = ('yes', 'no') if key in FACTS else ('file', 'directory', 'symlink', 'missing', 'unreadable', 'other')
            if type(state) is not str or state not in states: raise ValueError()
        return value
    except (ValueError, TypeError, KeyError):
        raise AuditError('Remote audit report rejected; raw output suppressed.') from None


def ssh_failure_category(returncode, stderr):
    """Classify observed diagnostics, never return any part of remote/client text.

    Categories are hints, not proof of a root cause. Keep LC_ALL=C on the child.
    Unknown diagnostics remain unknown rather than disclosing raw output.
    """
    error = stderr.lower()
    if 'load key ' in error and any(message in error for message in (
            'invalid format', 'error in libcrypto', 'incorrect passphrase', 'bad permissions')):
        return 'private_key_load'
    for message, category in (
        ('host key verification failed', 'host_key_verification'),
        ('remote host identification has changed', 'host_key_verification'),
        ('permission denied (', 'authentication_rejected'),
        ('connection timed out', 'connection_timeout'),
        ('connection refused', 'connection_refused'),
        ('could not resolve hostname', 'dns_resolution'),
        ('unable to negotiate with', 'algorithm_negotiation'),
        ('connection closed', 'connection_closed'),
        ('connection reset', 'connection_closed'),
    ):
        if message in error: return category
    if (returncode == 127 and '/usr/bin/python3' in error
            and ('not found' in error or 'no such file or directory' in error)):
        return 'remote_python_unavailable'
    if 0 < returncode < 255: return 'remote_command_failed'
    return 'unknown_ssh_failure'


def execute(env):
    if not allowed(env): raise AuditError('Audit dispatch is not authorized.')
    host, user = env.get('SERVER_HOST', ''), env.get('SERVER_USER', '')
    port, pin = env.get('SSH_PORT', ''), env.get('SERVER_SSH_FINGERPRINT', '')
    key = env.get('SSH_PRIVATE_KEY', '')
    if not re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}', pin):
        raise AuditError('A trusted SERVER_SSH_FINGERPRINT is required before connecting.')
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', host)
            or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,63}', user)
            or not re.fullmatch(r'[0-9]{1,5}', port) or not 1 <= int(port) <= 65535 or not key):
        raise AuditError('SSH connection configuration is missing or invalid.')
    # Child processes do not inherit GitHub/SSH secrets, custom SSH config or agents.
    child_env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
    stage = 'host_key_scan'
    try:
        # The owner pinned ED25519. Avoid extra key-type connections that can
        # exhaust the server's SSH rate limit before the authenticated probe.
        scan = subprocess.run(['/usr/bin/ssh-keyscan', '-T', '10', '-t', 'ed25519', '-p', port, host],
                              capture_output=True, text=True, timeout=40, env=child_env)
        verified = None
        for line in scan.stdout.splitlines():
            fields = line.split()
            if len(fields) != 3 or fields[1] not in ('ssh-ed25519', 'ecdsa-sha2-nistp256', 'ssh-rsa'): continue
            try:
                digest = hashlib.sha256(base64.b64decode(fields[2], validate=True)).digest()
            except ValueError:
                continue
            observed = 'SHA256:' + base64.b64encode(digest).decode().rstrip('=')
            if observed == pin:
                verified = fields[1] + ' ' + fields[2]
                break
        if verified is None: raise AuditError('SSH host key could not be verified; no authentication attempted.')
        with tempfile.TemporaryDirectory(prefix='gama-read-only-audit-') as directory:
            private = Path(directory) / 'identity'
            with open(private, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
                stream.write(key.rstrip('\n') + '\n')
            known = Path(directory) / 'known_hosts'
            target = host if int(port) == 22 else '[' + host + ']:' + port
            known.write_text(target + ' ' + verified + '\n')
            stage = 'ssh_command'
            result = subprocess.run([
                '/usr/bin/ssh', '-F', '/dev/null', '-T', '-p', port, '-i', str(private),
                '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(known),
                '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UpdateHostKeys=no',
                '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
                '-o', 'ConnectTimeout=10', '-o', 'ConnectionAttempts=1',
                '-o', 'LogLevel=ERROR', user + '@' + host, '/usr/bin/python3 -I -B -'],
                input=Path(__file__).with_name('server_probe.py').read_text(),
                capture_output=True, text=True, timeout=60, env=child_env)
            if result.returncode != 0:
                category = ssh_failure_category(result.returncode, result.stderr)
                raise AuditError('SSH audit failed [category=' + category + ', exit='
                                 + str(result.returncode) + ']; raw connection output suppressed.')
            return validate_report(result.stdout)
    except subprocess.TimeoutExpired:
        raise AuditError('SSH audit transport failed [stage=' + stage
                         + ', category=process_timeout]; raw connection output suppressed.') from None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise AuditError('SSH audit transport failed; raw connection output suppressed.') from None


def main():
    try:
        if sys.argv[1:] == ['guard']:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('allowed=' + str(allowed(os.environ)).lower() + '\n')
        elif sys.argv[1:] == ['run']:
            report = execute(os.environ)
            safe = json.dumps(report, sort_keys=True, indent=2)
            print(safe)
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
                output.write('## Read-only host inventory — not release approval\n\n```json\n' + safe + '\n```\n\n'
                             'Presence only. Services, routing, SMTP, backup retention and restore are not verified.\n')
        else:
            raise AuditError('Expected guard or run.')
        return 0
    except AuditError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
