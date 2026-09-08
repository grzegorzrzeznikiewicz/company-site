"""Real Linux state/lock tests; Docker and site side effects stop at ops."""
import copy
import fcntl
from datetime import datetime, timedelta, timezone
import json
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import time
import unittest

from wordpress.release.manifest import ReleaseValidationError

try:
    from wordpress.release.host import execute
except ModuleNotFoundError:
    execute = None

SHA = 'a' * 40
OLD = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:' + 'b' * 64
NEW = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:' + 'c' * 64
RESOURCES = {name: {'Name': 'gama-wp-production_' + name, 'CreatedAt': '2026-09-01T00:00:00Z',
                   'Driver': 'local', 'Mountpoint': '/var/lib/docker/volumes/' + name + '/_data',
                   'Scope': 'local', 'Options': None,
                   'Labels': {'com.docker.compose.project': 'gama-wp-production',
                              'com.docker.compose.volume': name}}
             for name in ('database', 'core', 'uploads')}


def request():
    return {'operation_id': 'run-101', 'kind': 'standard', 'git_sha': SHA, 'image': NEW,
            'publication': {'schema_version': 1, 'source': {'provenance': {'git_sha': SHA}},
                            'image': NEW, 'image_id': 'sha256:' + 'd' * 64,
                            'archive_sha256': 'e' * 64, 'manifest_sha256': 'f' * 64,
                            'platform': 'linux/amd64'}, 'authorization_ref': None}


class Ops:
    def __init__(self, root, *, fail=False, delay=0):
        self.root, self.fail, self.delay = root, fail, delay
        self.state = {'installed': True, 'healthy': True, 'image': OLD,
                      'platform': 'linux/amd64', 'resources': copy.deepcopy(RESOURCES)}
        self.main = SHA

    def log(self, action):
        with (self.root / 'effects').open('a') as output:
            output.write(action + '\n')

    def preflight(self, req): self.log('preflight')
    def current_state(self): return copy.deepcopy(self.state)
    def current_main_sha(self): return self.main
    def backup(self, scope, operation_id):
        self.log('backup:' + scope)
        return {'reference': 'offhost:fixture/' + operation_id, 'verified': True,
                'scope': scope, 'operation_id': operation_id, 'sha256': '1' * 64}

    def deploy(self, image, bootstrap=False):
        self.log('deploy:' + image + ':' + str(bootstrap))
        time.sleep(self.delay)
        self.state.update(installed=True, image=image)

    def verify(self, image, public=True):
        self.log('verify:' + str(public))
        if self.fail and image == NEW: raise RuntimeError('new PHP failed')

    def switch_routing(self, target, operation_id): self.log('route:' + target)


def child(root, req, delay=0):
    try:
        execute(req, Path(root), Ops(Path(root), delay=delay))
    except ReleaseValidationError:
        (Path(root) / 'refused').write_text('refused')


@unittest.skipUnless(os.geteuid() == 0 and os.environ.get('GAMA_HOST_TEST_ROOT'),
                     'requires isolated root-owned private Linux test mount')
class HostTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(execute, 'serialized host transaction is missing')
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['GAMA_HOST_TEST_ROOT'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'mode').write_text('wordpress\n')
        self.accepted = {'schema_version': 1, 'image': OLD, 'git_sha': 'b' * 40,
                         'resources': RESOURCES, 'completed': {}}
        (self.root / 'accepted.json').write_text(json.dumps(self.accepted))
        self.ops = Ops(self.root)

    def read(self, name): return json.loads((self.root / name).read_text())
    def effects(self):
        p = self.root / 'effects'
        return p.read_text().splitlines() if p.exists() else []

    def test_standard_backup_then_install_and_durable_idempotent_completion(self):
        result = execute(request(), self.root, self.ops)
        self.assertEqual('completed', result['status'])
        self.assertEqual('completed', self.read('operation.json')['status'])
        journal = self.read('operation.json')
        self.assertEqual(OLD, journal['prior']['image'])
        self.assertEqual(RESOURCES, journal['prior']['resources'])
        self.assertEqual('offhost:fixture/run-101', journal['backup']['reference'])
        before = self.effects()
        self.assertEqual(result, execute(request(), self.root, self.ops))
        self.assertEqual(before, self.effects())
        self.assertLess(before.index('backup:wordpress'), before.index('deploy:' + NEW + ':False'))

    def test_stale_off_partial_and_changed_resources_refuse_before_deploy(self):
        self.ops.main = '9' * 40
        self.assertEqual('skipped', execute(request(), self.root, self.ops)['status'])
        self.ops.main = SHA
        for mutation in ('off', 'partial', 'resources', 'unhealthy'):
            with self.subTest(mutation=mutation):
                self.ops = Ops(self.root)
                (self.root / 'mode').write_text('off' if mutation == 'off' else 'wordpress')
                if mutation == 'partial': self.ops.state['installed'] = False
                if mutation == 'resources': self.ops.state['resources']['database']['CreatedAt'] = 'changed'
                if mutation == 'unhealthy': self.ops.state['healthy'] = False
                with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
        self.assertFalse(any(e.startswith('deploy:') for e in self.effects()))

    def test_recovery_keeps_original_failure_incident_and_uses_no_second_backup(self):
        self.ops.fail = True
        result = execute(request(), self.root, self.ops)
        self.assertEqual('failed', result['status'])
        self.assertEqual('recovered', result['recovery'])
        self.assertEqual('RuntimeError', self.read('incident.json')['failure'])
        self.assertEqual(1, self.effects().count('backup:wordpress'))
        self.assertIn('deploy:' + OLD + ':False', self.effects())
        with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)

    def test_concurrent_duplicate_has_one_mutation_and_conflicting_retry_refuses(self):
        context = multiprocessing.get_context('fork')
        processes = [context.Process(target=child, args=(str(self.root), request(), .15)) for _ in range(2)]
        for process in processes: process.start()
        for process in processes:
            process.join(10)
            self.assertEqual(0, process.exitcode)
        self.assertEqual(1, self.effects().count('deploy:' + NEW + ':False'))
        self.assertFalse((self.root/'refused').exists())
        conflicting = request(); conflicting['image'] = OLD; conflicting['publication']['image'] = OLD
        with self.assertRaises(ReleaseValidationError): execute(conflicting, self.root, self.ops)

    def test_sigkill_lost_response_leaves_blocking_started_journal(self):
        process = multiprocessing.get_context('fork').Process(target=child, args=(str(self.root), request(), 20))
        process.start()
        try:
            deadline = time.monotonic() + 5
            while not any(e.startswith('deploy:') for e in self.effects()) and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(any(e.startswith('deploy:') for e in self.effects()))
            os.kill(process.pid, signal.SIGKILL)
            process.join(5)
            self.assertEqual('mutating', self.read('operation.json')['status'])
            with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
            self.assertEqual(1, self.effects().count('deploy:' + NEW + ':False'))
        finally:
            if process.is_alive(): process.kill(); process.join()

    def test_symlink_writable_parent_and_state_file_refuse(self):
        for name in ('mode', 'accepted.json', 'lock'):
            path = self.root / name
            if path.exists(): path.rename(self.root / (name + '.saved'))
            path.symlink_to(self.root / 'other')
            with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
            path.unlink()
            saved = self.root / (name + '.saved')
            if saved.exists(): saved.rename(path)
        self.root.chmod(0o777)
        with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
        self.root.chmod(0o700)
        self.assertEqual([], self.effects())

    def test_first_cutover_window_rechecked_and_acceptance_does_not_enable_mode(self):
        (self.root / 'mode').write_text('off')
        (self.root / 'accepted.json').unlink()
        self.ops.state = {'installed': False, 'healthy': False, 'image': None,
                          'platform': 'linux/amd64', 'resources': {}}
        req = request(); req['kind'] = 'first-cutover'; req['authorization_ref'] = 'approval-101'
        now = datetime.now(timezone.utc)
        req['publication']['source']['authorization'] = {
            'authorization_id': 'approval-101', 'promotion_run_id': 101, 'promotion_run_attempt': 1,
            'git_sha': SHA, 'source_run_id': 100, 'source_run_attempt': 1, 'artifact_id': 50,
            'artifact_digest': 'sha256:' + '1' * 64, 'operators': [{'id': 1, 'login': 'owner', 'type': 'User'}],
            'window_start': (now - timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'window_end': (now - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')}
        with self.assertRaises(ReleaseValidationError): execute(req, self.root, self.ops)
        self.assertEqual([], self.effects())
        req['publication']['source']['authorization']['window_end'] = (now + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        self.ops.state['namespace'] = {'networks':['existing-network']}
        with self.assertRaises(ReleaseValidationError): execute(req, self.root, self.ops)
        self.assertFalse(any(e.startswith('deploy:') for e in self.effects()))
        self.ops.state.pop('namespace')
        self.assertEqual('completed', execute(req, self.root, self.ops)['status'])
        self.assertEqual('off', (self.root / 'mode').read_text())
        effects = self.effects()
        self.assertLess(effects.index('backup:legacy'), effects.index('deploy:' + NEW + ':True'))
        self.assertLess(effects.index('backup:wordpress'), effects.index('route:wordpress'))

    def test_routing_recovery_never_creates_first_wordpress_acceptance(self):
        (self.root/'mode').write_text('off')
        (self.root/'accepted.json').unlink()
        original = request()
        journal = {'schema_version':1,'operation_id':'first-100','kind':'first-cutover','status':'failed',
                   'image':NEW,'git_sha':SHA,'prior':{'resources':{},'image':None},
                   'backup':{'reference':'offhost:legacy/first-100'}, 'recovery_resources':RESOURCES}
        (self.root/'operation.json').write_text(json.dumps(journal))
        (self.root/'incident.json').write_text(json.dumps(journal))
        original.update(operation_id='route-102',kind='routing-rollback',authorization_ref='recovery-102',
                        recovery_authorization={'target_operation_id':'first-100'})
        result = execute(original,self.root,self.ops)
        self.assertEqual('completed',result['status'])
        self.assertFalse((self.root/'accepted.json').exists())
        self.assertEqual(result,execute(original,self.root,self.ops))
        self.assertEqual(1,self.effects().count('route:legacy'))

    def test_failed_manual_routing_hook_or_verification_never_claims_recovered(self):
        for failure in ('hook', 'verify'):
            with self.subTest(failure=failure):
                journal = {'schema_version':1,'operation_id':'first-100','kind':'first-cutover','status':'failed',
                           'image':NEW,'git_sha':SHA,'prior':{'resources':{},'image':None},
                           'backup':{'reference':'offhost:legacy/first-100'}, 'recovery_resources':RESOURCES}
                (self.root/'operation.json').write_text(json.dumps(journal))
                (self.root/'incident.json').write_text(json.dumps(journal))
                req = request()
                req.update(operation_id='route-'+failure,kind='routing-rollback',authorization_ref='recovery-102',
                           recovery_authorization={'target_operation_id':'first-100'})
                self.ops = Ops(self.root)
                def fail(*args, **kwargs): raise RuntimeError('routing failure fixture')
                if failure == 'hook': self.ops.switch_routing = fail
                else: self.ops.verify = fail
                result = execute(req, self.root, self.ops)
                expected = {'status':'failed','operation_id':'route-'+failure,'recovery':'not-attempted'}
                self.assertEqual(expected, result)
                for name in ('operation.json','incident.json'):
                    recorded = self.read(name)
                    self.assertEqual(expected, recorded['result'])
                    self.assertEqual('failed', recorded['status'])
                    self.assertEqual('RuntimeError', recorded['failure'])
                    self.assertEqual(journal, recorded['previous_incident'])
                with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)

    def test_automatic_recovery_waits_for_exited_leaders_live_descendant(self):
        from wordpress.release.host_ops import run
        fixture = self.root/'deploy-process'
        pids_file = self.root/'deploy-pids'
        fixture.write_text('''#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
child=os.fork()
if child:
    Path(sys.argv[1]).write_text(json.dumps({'group':os.getpid(),'child':child}))
    os._exit(0)
time.sleep(30)
''')
        fixture.chmod(0o700)
        original = self.ops.deploy
        def deploy(image, bootstrap=False):
            if image == NEW: run([str(fixture), str(pids_file)], timeout=.2)
            else:
                child = json.loads(pids_file.read_text())['child']
                proc = Path('/proc')/str(child)/'stat'
                if proc.exists() and proc.read_text().rpartition(')')[2].split()[0] not in ('Z','X'):
                    self.ops.log('recovery-raced-live-descendant')
                original(image, bootstrap)
        self.ops.deploy = deploy
        try:
            result = execute(request(), self.root, self.ops)
            self.assertEqual({'status':'failed','operation_id':'run-101','recovery':'recovered'}, result)
            self.assertNotIn('recovery-raced-live-descendant', self.effects())
            self.assertEqual(result, self.read('incident.json')['result'])
        finally:
            if pids_file.exists():
                try: os.killpg(json.loads(pids_file.read_text())['group'], signal.SIGKILL)
                except ProcessLookupError: pass

    def test_unverifiable_process_cleanup_blocks_automatic_and_manual_recovery(self):
        from wordpress.release import host
        cleanup_error = getattr(host, 'OperationCleanupError', None)
        self.assertIsNotNone(cleanup_error, 'uncertain cleanup must have a blocking host outcome')
        def deploy(image, bootstrap=False):
            self.ops.log('deploy:' + image)
            try: raise ReleaseValidationError('original operation timeout')
            except ReleaseValidationError as original: raise cleanup_error('cleanup unverified') from original
        self.ops.deploy = deploy
        result = execute(request(), self.root, self.ops)
        self.assertEqual({'status':'failed','operation_id':'run-101','recovery':'not-attempted'}, result)
        for name in ('operation.json','incident.json'):
            journal = self.read(name)
            self.assertEqual('interrupted', journal['status'])
            self.assertEqual('ReleaseValidationError', journal['failure'])
            self.assertEqual('OperationCleanupError', journal['cleanup_failure'])
        self.assertEqual(['deploy:' + NEW], [e for e in self.effects() if e.startswith('deploy:')])
        req = request(); req.update(kind='code-rollback', authorization_ref='recovery-102',
                                    recovery_authorization={'target_operation_id':'run-101'})
        with self.assertRaises(ReleaseValidationError): execute(req,self.root,self.ops)

    def test_manual_recovery_binds_failed_journal_target_and_keeps_incident(self):
        self.ops.fail = True
        execute(request(), self.root, self.ops)
        req = request(); req.update(operation_id='rollback-102', kind='code-rollback', image=OLD,
                                    git_sha='b' * 40, authorization_ref='recovery-102')
        req['publication']['image'] = OLD
        req['publication']['source']['provenance']['git_sha'] = 'b' * 40
        req['recovery_authorization'] = {'target_operation_id': 'run-101'}
        self.ops.fail = False
        self.ops.main = '9' * 40
        before = self.effects().count('backup:wordpress')
        failed = self.read('operation.json')
        pending = dict(failed, status='mutating')
        (self.root/'operation.json').write_text(json.dumps(pending))
        with self.assertRaises(ReleaseValidationError): execute(req, self.root, self.ops)
        (self.root/'operation.json').write_text(json.dumps(failed))
        self.assertEqual('completed', execute(req, self.root, self.ops)['status'])
        self.assertEqual(before, self.effects().count('backup:wordpress'))
        self.assertTrue((self.root / 'incident.json').exists())
        with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)

    def test_backup_failure_leaves_barrier_without_code_mutation(self):
        def bad_backup(scope, operation_id):
            return {'verified': True}
        self.ops.backup = bad_backup
        self.assertEqual('failed', execute(request(), self.root, self.ops)['status'])
        self.assertFalse(any(e.startswith('deploy:') for e in self.effects()))
        self.assertEqual('not-attempted', self.read('incident.json')['recovery'])

    def test_fresh_manual_recovery_retries_immutable_original_after_failure(self):
        for kind in ('code-rollback', 'routing-rollback'):
            with self.subTest(kind=kind):
                self.ops = Ops(self.root)
                (self.root/'accepted.json').write_text(json.dumps(self.accepted))
                target = {'schema_version':1, 'operation_id':'original-100',
                          'kind':'standard' if kind == 'code-rollback' else 'first-cutover',
                          'status':'failed', 'image':NEW, 'git_sha':SHA,
                          'prior':{'resources':RESOURCES,'image':OLD,'git_sha':'b'*40},
                          'backup':{'reference':'offhost:original'}, 'recovery_resources':RESOURCES}
                (self.root/'operation.json').write_text(json.dumps(target))
                (self.root/'incident.json').write_text(json.dumps(target))
                req = request(); req.update(operation_id='recovery-201',kind=kind,authorization_ref='approval-201',
                    recovery_authorization={'target_operation_id':'original-100'})
                if kind == 'code-rollback':
                    req.update(image=OLD,git_sha='b'*40)
                    req['publication']['image'] = OLD
                    req['publication']['source']['provenance']['git_sha'] = 'b'*40
                def fail(*args, **kwargs): raise RuntimeError('transient recovery failure')
                if kind == 'routing-rollback': self.ops.switch_routing = fail
                else: self.ops.deploy = fail
                self.assertEqual('failed', execute(req,self.root,self.ops)['status'])
                failed = self.read('operation.json')
                self.ops = Ops(self.root)
                req.update(operation_id='recovery-202',authorization_ref='approval-202')
                self.assertEqual('completed',execute(req,self.root,self.ops)['status'])
                saved = self.read('operation.json')
                self.assertEqual(target,saved['recovery_target'])
                self.assertEqual(failed,saved['previous_incident'])
                self.assertTrue((self.root/'incident.json').exists())

    def test_failed_recovery_is_never_reported_as_success(self):
        def broken_verify(image, public=True): raise RuntimeError('PHP unavailable')
        self.ops.verify = broken_verify
        # Existing accepted verification passes; all checks after mutation fail.
        original = self.ops.deploy
        self.ops.verify = lambda image, public=True: None
        def deploy(image, bootstrap=False):
            original(image, bootstrap)
            self.ops.verify = broken_verify
        self.ops.deploy = deploy
        self.assertEqual({'status':'failed','operation_id':'run-101','recovery':'failed'},
                         execute(request(), self.root, self.ops))
        self.assertEqual('RuntimeError', self.read('incident.json')['recovery_failure'])

    def test_completed_history_does_not_allow_old_id_to_mutate_after_later_release(self):
        execute(request(), self.root, self.ops)
        req = request(); req['operation_id'] = 'run-102'
        self.assertEqual('completed', execute(req, self.root, self.ops)['status'])
        before = self.effects()
        self.assertEqual('completed', execute(request(), self.root, self.ops)['status'])
        self.assertEqual(before, self.effects())

    def test_pending_journal_refuses_before_ops_and_nonroot_owned_file_refuses(self):
        (self.root / 'operation.json').write_text('{"status":"mutating"}')
        with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
        (self.root / 'operation.json').unlink()
        os.chown(self.root / 'mode', 12345, 12345)
        with self.assertRaises(ReleaseValidationError): execute(request(), self.root, self.ops)
        self.assertEqual([], self.effects())

    def test_mode_is_read_after_waiting_on_the_real_lock(self):
        lock = (self.root/'lock').open('w')
        fcntl.flock(lock, fcntl.LOCK_EX)
        process = multiprocessing.get_context('fork').Process(target=child, args=(str(self.root),request()))
        process.start()
        try:
            time.sleep(.1)
            self.assertEqual([], self.effects())
            (self.root/'mode').write_text('off')
            fcntl.flock(lock, fcntl.LOCK_UN)
            process.join(5)
            self.assertEqual(0, process.exitcode)
            self.assertEqual([], self.effects())
            self.assertTrue((self.root/'refused').exists())
        finally:
            lock.close()
            if process.is_alive(): process.kill(); process.join()
