"""Production adapter boundary tests using executable Docker fixtures."""
import json
import os
import signal
import shutil
from pathlib import Path
import tempfile
import unittest
import time
from datetime import datetime, timedelta, timezone
from unittest import mock

from wordpress.release.manifest import ReleaseValidationError
from wordpress.tests.release.test_host import RESOURCES, OLD, NEW, SHA, request

try:
    from wordpress.release.host_ops import HostOps
except ModuleNotFoundError:
    HostOps = None


class ProductionPortTests(unittest.TestCase):
    def test_deploy_only_passes_smtp_deferral_for_the_bound_bootstrap(self):
        ops = HostOps({'env_file': '/private/production.env'})
        ops.request = request()
        ops.request.update(kind='first-cutover', authorization_ref='owner-approval')
        record = {key: ops.request[key] for key in ('operation_id', 'git_sha', 'image', 'authorization_ref')}
        record['accept_contact_delivery_unavailable'] = True
        ops.smtp_deferral = record
        with mock.patch.object(ops, '_docker'), mock.patch.object(ops, '_image'), \
                mock.patch.object(ops, '_repo', return_value=Path('/tools')), \
                mock.patch.object(ops, '_helper_env', return_value={}), \
                mock.patch.object(ops, 'current_state', return_value={'healthy': True}), \
                mock.patch('wordpress.release.host_ops.run') as run:
            ops.deploy(ops.request['image'], bootstrap=True)
            self.assertIn('--defer-smtp', run.call_args.args[0])
            with self.assertRaises(ReleaseValidationError):
                ops.deploy(ops.request['image'], bootstrap=False)

    def test_deploy_and_routing_use_the_reviewed_port(self):
        ops = HostOps({'env_file': '/private/production.env'})
        ops.request = request()
        with mock.patch.object(ops, '_docker'), mock.patch.object(ops, '_image'), \
                mock.patch.object(ops, '_repo', return_value=Path('/tools')), \
                mock.patch.object(ops, '_helper_env', return_value={}), \
                mock.patch.object(ops, 'current_state', return_value={'healthy': True}), \
                mock.patch('wordpress.release.host_ops.run') as run:
            ops.deploy(ops.request['image'])
            argv = run.call_args.args[0]
            self.assertEqual('8000', argv[argv.index('--http-port') + 1])
            ops.switch_routing('wordpress', ops.request['operation_id'])
            argv = run.call_args.args[0]
            self.assertEqual('8000', argv[argv.index('--port') + 1])

    def test_private_probe_uses_loopback_port_8000(self):
        ops = HostOps({})
        with mock.patch('wordpress.release.host_ops.urllib.request.build_opener') as build:
            response = build.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b'ok'
            ops._http('/', public=False)
            probe = build.return_value.open.call_args.args[0]
            self.assertEqual('http://127.0.0.1:8000/', probe.full_url)
            self.assertEqual('gama-software.com', probe.get_header('Host'))
            self.assertEqual('https', probe.get_header('X-forwarded-proto'))


@unittest.skipUnless(os.geteuid() == 0 and os.environ.get('GAMA_HOST_TEST_ROOT'),
                     'requires private root-owned Linux fixture')
class HostOpsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(HostOps, 'production host adapter is missing')
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['GAMA_HOST_TEST_ROOT'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docker = self.root / 'docker'
        self.data = {'image': OLD, 'resources': json.loads(json.dumps(RESOURCES)), 'healthy': True, 'architecture': 'amd64'}
        self.write_data()
        self.docker.write_text('''#!/usr/bin/python3
import json, sys
from pathlib import Path
root = Path(__file__).parent
data = json.loads((root / 'data.json').read_text())
a = sys.argv[1:]
with (root / 'calls').open('a') as log: log.write(json.dumps(a) + '\\n')
if a == ['info', '--format', '{{.OSType}}/{{.Architecture}}']: print('linux/' + data['architecture'])
elif a == ['ps', '-aq', '--filter', 'label=com.docker.compose.project=gama-wp-production', '--filter', 'label=com.docker.compose.service=wordpress']: print('wp')
elif a == ['ps', '-aq', '--filter', 'label=com.docker.compose.project=gama-wp-production', '--filter', 'label=com.docker.compose.service=db']: print('db')
elif a == ['volume', 'ls', '-q', '--filter', 'label=com.docker.compose.project=gama-wp-production']: print('\\n'.join(x['Name'] for x in data['resources'].values()))
elif a[:2] == ['volume', 'inspect'] and len(a) == 3:
    print(json.dumps([next(x for x in data['resources'].values() if x['Name'] == a[2])]))
elif a in [['inspect', 'wp'], ['inspect', 'db']]:
    db = a[1] == 'db'
    mounts = [{'Type':'volume', 'Name': data['resources'][n]['Name'], 'Source':data['resources'][n]['Mountpoint'], 'Destination':dest, 'RW':True} for n,dest in ([('database','/var/lib/mysql')] if db else [('core','/var/www/html'),('uploads','/var/www/html/wp-content/uploads')])]
    print(json.dumps([{'Id': '1'*64 if db else '2'*64, 'Image':'sha256:'+'d'*64, 'Config': {'Image':data['image'], 'Labels': {'com.docker.compose.project':'gama-wp-production','com.docker.compose.service':'db' if db else 'wordpress'}}, 'Mounts':mounts, 'State': {'Running':True,'Health':{'Status':'healthy' if data['healthy'] else 'unhealthy'}}}]))
elif a == ['image', 'inspect', data['image']]:
    print(json.dumps([{'Id':'sha256:'+'d'*64,'Os':'linux','Architecture':data['architecture'],'Config':{'Labels':{'org.opencontainers.image.revision':'a'*40,'com.gamasoftware.wordpress.release-marker':'release'}},'RepoDigests':[data['image']]}]))
elif a == ['exec', 'wp', 'php', '-r', 'require "/var/www/html/wp-load.php"; exit(wp_mail($argv[1], "Gama release verification", "Controlled release SMTP transport probe") ? 0 : 1);', 'controlled@example.test']: pass
elif a == ['exec', 'wp', 'php', '-r', 'require "/var/www/html/wp-load.php"; exit(wp_get_environment_type() === "production" && function_exists("gama_mail_transport_config") && gama_mail_transport_config() === null && wp_mail($argv[1], "Gama deferred SMTP check", "Delivery must fail closed") === false ? 0 : 1);', 'controlled@example.test']:
    sys.exit(0 if data.get('mail_fail_closed', True) else 1)
elif a in [['ps','--filter','label=com.docker.compose.project=gama-wp-production','--filter','label=com.docker.compose.service='+service,'--format','{{.ID}}'] for service in ('db','wordpress')]: print('db' if 'label=com.docker.compose.service=db' in a else 'wp')
elif a in [['inspect','--format','{{.State.Health.Status}}',c] for c in ('wp','db')]: print('healthy')
elif a == ['inspect','--format',r'{{range .Mounts}}{{if eq .Destination "/var/www/html/wp-content/uploads"}}{{.Name}}{{"\\n"}}{{end}}{{end}}','wp']: print('gama-wp-production_uploads')
elif a == ['exec','db','sh','-ec','exec mariadb-dump --host=127.0.0.1 --user="$MARIADB_USER" --password="$MARIADB_PASSWORD" --single-transaction --quick --skip-lock-tables --default-character-set=utf8mb4 "$MARIADB_DATABASE"']: print('CREATE TABLE fixture (id INT);')
elif a == ['run','--rm','--network','none','--volume','gama-wp-production_uploads:/source:ro','--entrypoint','tar','wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d','-C','/source','-cf','-','.']:
    import io,tarfile
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        info=tarfile.TarInfo('fixture.txt'); info.size=5; archive.addfile(info,io.BytesIO(b'media'))
    sys.stdout.buffer.write(stream.getvalue())
elif a == ['exec','wp','php','-r','include "/var/www/html/wp-includes/version.php"; echo $wp_version;']: print('7.1.0')
elif a == ['inspect','--format','{{.Config.Image}}','db']: print('mariadb:10.11.18-jammy@sha256:'+'9'*64)
elif a == ['inspect','--format','{{.Config.Image}}','wp']: print(data['image'])
elif a == ['inspect','--format','{{.Image}}','wp']: print('sha256:'+'d'*64)
elif a == ['inspect','--format','{{index .Config.Labels "org.opencontainers.image.revision"}}','wp']: print('a'*40)
elif a == ['ps', '-aq', '--filter', 'label=com.docker.compose.project=gama-wp-production']:
    print('\\n'.join(data.get('namespace_containers', ['wp','db'])))
elif a[:4] == ['ps', '-aq', '--filter', 'name=^/?gama-wp-production[-_]']:
    print('\\n'.join(data.get('reserved_containers', [])))
elif a[:3] == ['network', 'ls', '-q']:
    print('\\n'.join(data.get('namespace_networks', [])))
elif a[:4] == ['volume', 'ls', '-q', '--filter'] and a[4].startswith('name='):
    print('\\n'.join(data.get('reserved_volumes', [])))
else: raise SystemExit('unexpected argv: '+repr(a))
''')
        self.docker.chmod(0o700)
        self.config = {'docker': str(self.docker)}
        self.ops = HostOps(self.config)

    def write_data(self): (self.root / 'data.json').write_text(json.dumps(self.data))

    def test_actual_mounts_are_bound_to_named_volume_metadata_not_invented_ids(self):
        result = self.ops.current_state()
        self.assertEqual(RESOURCES, result['resources'])
        self.assertEqual(OLD, result['image'])
        self.assertTrue(result['healthy'])

    def test_namespace_remnants_are_not_reported_as_absent(self):
        for field, values in [('namespace_networks',['leftover-network']),
                              ('namespace_containers',['install-oneoff']),
                              ('reserved_volumes',['gama-wp-production_uploads']),
                              ('reserved_containers',['foreign-reserved-container'])]:
            with self.subTest(field=field):
                self.data.update(resources={}, namespace_containers=[], namespace_networks=[], reserved_volumes=[], reserved_containers=[])
                self.data[field] = values
                self.write_data()
                source = self.docker.read_text().replace("print('wp')", "None").replace("print('db')", "None")
                source = source.replace("print('\\n'.join(x['Name'] for x in data['resources'].values()))", "sys.stdout.write('\\n'.join(x['Name'] for x in data['resources'].values()))")
                self.docker.write_text(source)
                result = self.ops.current_state()
                self.assertFalse(result['installed'])
                self.assertTrue(result.get('namespace'), 'existing Docker namespace must prevent first installation')

    def test_failed_external_client_does_not_prove_daemon_work_stopped(self):
        from wordpress.release.host import OperationCleanupError
        from wordpress.release.host_ops import run
        import subprocess
        worker = subprocess.Popen(['/usr/bin/python3', '-c', 'import time; time.sleep(30)'], start_new_session=True)
        self.addCleanup(lambda: (worker.kill(), worker.wait()) if worker.poll() is None else None)
        client = self.root/'daemon-client'
        client.write_text('#!/usr/bin/python3\nraise SystemExit(7)\n')
        client.chmod(0o700)
        with self.assertRaises(OperationCleanupError):
            run([str(client)], external_mutation=True)
        self.assertIsNone(worker.poll(), 'fixture must retain independent daemon work after client exit')

    def test_host_deploy_client_failure_keeps_daemon_barrier_and_no_recovery(self):
        import subprocess
        from wordpress.release.host import execute
        from wordpress.tests.release.test_host import Ops
        for name, value in [('mode','wordpress'), ('accepted.json',json.dumps({
                'schema_version':1,'image':OLD,'git_sha':'b'*40,'resources':RESOURCES,'completed':{}}))]:
            (self.root/name).write_text(value)
        started, active = self.root/'accepted-work', self.root/'daemon-active'
        daemon = subprocess.Popen(['/usr/bin/python3','-c',
            'import sys,time; from pathlib import Path; p=Path(sys.argv[1]); '
            'exec("while not p.exists(): time.sleep(.01)"); '
            'Path(sys.argv[2]).write_text("active"); time.sleep(30)',str(started),str(active)],start_new_session=True)
        self.addCleanup(lambda: (daemon.kill(),daemon.wait()) if daemon.poll() is None else None)
        (self.root/'bin').mkdir()
        helper = self.root/'bin/deploy-production'
        helper.write_text('''#!/usr/bin/python3
import sys,time
from pathlib import Path
assert sys.argv[-1] == '--mutation-only'
root=Path(__file__).parents[1]
(root/'accepted-work').write_text('mutation accepted by daemon')
while not (root/'daemon-active').exists(): time.sleep(.01)
print('GAMA_MUTATION_COMPLETE (untrusted child output)')
raise SystemExit(7)
''')
        helper.chmod(0o700)
        self.ops.request = request()
        self.config['env_file'] = str(self.root/'unused-env')
        self.ops._repo = lambda: self.root
        self.ops._docker = lambda *a, **kw: ''
        self.ops._image = lambda *a: None
        self.ops._helper_env = lambda: {}
        transaction = Ops(self.root)
        transaction.deploy = self.ops.deploy
        result = execute(request(),self.root,transaction)
        self.assertEqual('not-attempted',result['recovery'])
        self.assertEqual('interrupted',json.loads((self.root/'operation.json').read_text())['status'])
        self.assertTrue(active.exists())
        self.assertIsNone(daemon.poll())
        recovery = request(); recovery.update(operation_id='fresh-102',kind='code-rollback',
            authorization_ref='approved-102',recovery_authorization={'target_operation_id':'run-101'})
        with self.assertRaises(ReleaseValidationError): execute(recovery,self.root,transaction)

    def test_broken_php_does_not_prevent_current_resource_observation(self):
        self.data['healthy'] = False; self.write_data()
        result = self.ops.current_state()
        self.assertFalse(result['healthy'])
        self.assertEqual(RESOURCES, result['resources'])
        self.assertNotIn('exec', (self.root / 'calls').read_text())

    def test_foreign_volume_labels_and_native_platform_refuse(self):
        self.data['architecture'] = 'arm64'; self.write_data()
        with self.assertRaises(ReleaseValidationError): self.ops.current_state()
        self.data['architecture'] = 'amd64'
        self.data['resources']['uploads']['Labels']['com.docker.compose.project'] = 'other'
        self.write_data()
        with self.assertRaises(ReleaseValidationError): self.ops.current_state()

    def test_untrusted_tool_refuses_without_subprocess(self):
        self.docker.chmod(0o777)
        with self.assertRaises(ReleaseValidationError): self.ops.current_state()
        self.assertFalse((self.root / 'calls').exists())

    def test_routing_hook_binds_original_cutover_and_current_recovery_ids(self):
        hook = self.root / 'routing-hook'
        hook.write_text('''#!/usr/bin/python3
import json,sys
from pathlib import Path
with Path(__file__).with_name('routing-argv').open('a') as log:
    log.write(json.dumps(sys.argv[1:])+'\\n')
''')
        hook.chmod(0o700)
        self.ops.request = request()
        self.ops.request.update(kind='routing-rollback', operation_id='recovery-102',
                                recovery_authorization={'target_operation_id':'cutover-100'})
        with mock.patch('wordpress.release.host_ops.ROUTING', str(hook)):
            self.ops.switch_routing('legacy', 'recovery-102')
            self.ops.request = request()
            self.ops.request.update(kind='first-cutover', operation_id='cutover-100')
            self.ops.switch_routing('legacy', 'cutover-100')
        self.assertEqual([
            ['--target','legacy','--deployment-run-id','cutover-100','--rollback-run-id','recovery-102'],
            ['--target','legacy','--deployment-run-id','cutover-100','--rollback-run-id','cutover-100'],
        ], [json.loads(line) for line in (self.root/'routing-argv').read_text().splitlines()])

    def test_exited_leader_descendant_is_dead_before_timeout_or_error_returns(self):
        from wordpress.release.host_ops import run
        for mode in ('timeout', 'output-error', 'exit-error'):
            with self.subTest(mode=mode):
                fixture = self.root / ('descendant-' + mode)
                state_file = self.root / (mode + '-pids.json')
                fixture.write_text('''#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
mode=sys.argv[1]
child=os.fork()
if child:
    Path(sys.argv[2]).write_text(json.dumps({'group':os.getpid(),'child':child}))
    os._exit(7 if mode == 'exit-error' else 0)
time.sleep(.05)
if mode == 'output-error': os.write(1,b'x'*1048577)
if mode == 'exit-error': os.close(1); os.close(2)
time.sleep(30)
''')
                fixture.chmod(0o700)
                try:
                    with self.assertRaises(ReleaseValidationError):
                        run([str(fixture), mode, str(state_file)], timeout=.2)
                    pids = json.loads(state_file.read_text())
                    child_state = Path('/proc') / str(pids['child']) / 'stat'
                    if child_state.exists():
                        self.assertIn(child_state.read_text().rpartition(')')[2].split()[0], ('Z', 'X'),
                                      'run returned while its operational descendant could still mutate')
                finally:
                    if state_file.exists():
                        pids = json.loads(state_file.read_text())
                        try: os.killpg(pids['group'], signal.SIGKILL)
                        except ProcessLookupError: pass

    def test_unavailable_process_inspection_is_not_reported_as_verified_cleanup(self):
        from wordpress.release.host import OperationCleanupError
        from wordpress.release.host_ops import run
        fixture = self.root/'uninspectable-process'
        fixture.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(30)\n')
        fixture.chmod(0o700)
        with mock.patch('wordpress.release.host_ops.Path.iterdir', side_effect=PermissionError('procfs unavailable')):
            with self.assertRaises(OperationCleanupError) as failure:
                run([str(fixture)], timeout=.1)
        self.assertIsInstance(failure.exception.__cause__, ReleaseValidationError)
        self.assertEqual('operational tool timed out', str(failure.exception.__cause__))

    def test_missing_operational_configuration_fails_closed(self):
        with self.assertRaises(ReleaseValidationError): self.ops.preflight(request())
        self.assertFalse((self.root / 'calls').exists())

    def test_first_cutover_waiver_prepares_routing_without_fake_backup_evidence(self):
        req = request(); req.update(kind='first-cutover', authorization_ref='approval-101')
        waiver = {key: req[key] for key in ('operation_id', 'git_sha', 'image', 'authorization_ref')}
        waiver['accept_data_loss_without_backup'] = True
        env = self.root / 'production.env'; env.write_text(''); env.chmod(0o600)
        adapter = self.root / 'legacy-adapter'
        adapter.write_text('''#!/usr/bin/python3
import hashlib,json,sys
from pathlib import Path
value=json.load(sys.stdin)
with Path(__file__).with_name('routing-calls').open('a') as log: log.write(sys.argv[1]+'\\n')
assert sys.argv[1] in ('prepare-routing','verify-routing')
assert set(value) == {'operation_id','git_sha','image','deployment_operation_id'}
assert value['deployment_operation_id'] == 'run-101'
digest=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps({'binding_sha256':digest,'routing_recovery_reference':'routing:run-101'}))
''')
        adapter.chmod(0o700)
        self.config.update(wordpress_root=str(self.root), env_file=str(env), github_token_file=str(env),
                           smtp_recipient='controlled@example.test', legacy_adapter=str(adapter),
                           first_cutover_without_backup=waiver)
        with mock.patch.object(self.ops, '_repo', return_value=self.root), \
                mock.patch.object(self.ops, '_api', return_value=None), \
                mock.patch('wordpress.release.host_ops._recheck', return_value={'operation':'first-cutover'}), \
                mock.patch('wordpress.release.host_ops.CUTOVER', str(adapter)), \
                mock.patch('wordpress.release.host_ops.ROUTING', str(adapter)):
            self.assertEqual(waiver, self.ops.preflight(req))
            deferred = {key: req[key] for key in ('operation_id', 'git_sha', 'image', 'authorization_ref')}
            deferred['accept_contact_delivery_unavailable'] = True
            self.config['first_cutover_without_smtp'] = deferred
            self.ops.preflight(req)
            self.assertEqual(deferred, getattr(self.ops, 'smtp_deferral', None))
            self.config['first_cutover_without_smtp'] = {**deferred, 'git_sha': 'f'*40}
            with self.assertRaises(ReleaseValidationError): self.ops.preflight(req)
            self.config.pop('first_cutover_without_smtp')
            self.ops.preflight(req)
            self.assertIsNone(self.ops.smtp_deferral)
            with mock.patch.object(self.ops, '_http', return_value=(b'legacy', {})):
                self.ops.verify('legacy')
                self.ops.request = {**req, 'kind':'routing-rollback', 'operation_id':'route-102',
                                    'authorization_ref':'recovery-102',
                                    'recovery_authorization':{'target_operation_id':'run-101'}}
                self.ops.verify('legacy')
                self.ops.request['image'] = OLD
                with self.assertRaises(ReleaseValidationError): self.ops.verify('legacy')
                self.ops.request = req
                adapter.write_text(adapter.read_text().replace("'binding_sha256':digest", "'binding_sha256':'0'*64"))
                with self.assertRaises(ReleaseValidationError): self.ops.verify('legacy')
            self.assertEqual(['prepare-routing','prepare-routing','prepare-routing','verify-routing','verify-routing','verify-routing'],
                             (self.root/'routing-calls').read_text().splitlines())
            with self.assertRaises(ReleaseValidationError): self.ops.preflight(request())
            self.config['first_cutover_without_backup'] = {**waiver, 'git_sha': 'f'*40}
            with self.assertRaises(ReleaseValidationError): self.ops.preflight(req)

    def test_manual_gate_requires_actual_exact_configured_owner_history(self):
        from wordpress.release import host_ops
        formatter = getattr(host_ops, 'recovery_comment', None)
        self.assertIsNotNone(formatter, 'recovery authorization formatter is missing')
        now = datetime.now(timezone.utc)
        auth = {'authorization_id':'recovery-102','promotion_run_id':102,'promotion_run_attempt':1,
                'operation_id':'rollback-102','target_operation_id':'run-101','kind':'code-rollback',
                'git_sha':'b'*40,'image':OLD,'operators':[{'id':1,'login':'owner','type':'User'}],
                'window_start':(now-timedelta(hours=1)).isoformat().replace('+00:00','Z'),
                'window_end':(now+timedelta(hours=1)).isoformat().replace('+00:00','Z')}
        from wordpress.tests.release.test_github_source import HTTPFixture
        from wordpress.release.github_source import ROOT, REPOSITORY, REPOSITORY_ID
        repo = {'id':REPOSITORY_ID,'full_name':REPOSITORY,'fork':False}
        workflow = {'id':123,'path':'.github/workflows/wordpress-production-rollback.yml','state':'active'}
        run = {'id':102,'repository':repo,'head_repository':repo,'workflow_id':123,
               'path':workflow['path'],'event':'workflow_dispatch','head_branch':'main','head_sha':SHA,
               'run_attempt':1,'status':'in_progress','conclusion':None,'created_at':now.isoformat().replace('+00:00','Z'),
               'actor':{'id':1},'triggering_actor':{'id':1}}
        environment = {'id':10,'name':'wordpress-production-rollback','protection_rules':[
            {'type':'required_reviewers','prevent_self_review':False,'reviewers':[
                {'type':'User','reviewer':{'id':1,'login':'owner','type':'User'}}]}]}
        history = [{'state':'approved','comment':formatter(auth),'user':{'id':1,'login':'owner','type':'User'},
                    'environments':[{'id':10,'name':'wordpress-production-rollback'}]}]
        responses = {ROOT+'/actions/runs/102':run,
                     ROOT+'/actions/workflows/wordpress-production-rollback.yml':workflow,
                     ROOT+'/collaborators/owner/permission':{'permission':'admin','user':{'id':1,'login':'owner','type':'User'}},
                     ROOT+'/environments/wordpress-production-rollback':environment,
                     ROOT+'/actions/runs/102/approvals':history}
        req = request(); req.update(operation_id='rollback-102',kind='code-rollback',git_sha='b'*40,image=OLD,
                                   authorization_ref='recovery-102',recovery_authorization=auth)
        with HTTPFixture(responses) as http:
            self.ops.api = http.api()
            self.ops._recovery_gate(req)
            history[0]['comment'] = '{}'
            with self.assertRaises(ReleaseValidationError): self.ops._recovery_gate(req)

    def test_public_pages_logo_and_smtp_are_real_probes_and_missing_contact_refuses(self):
        from wordpress.tests.release.test_github_source import HTTPFixture
        self.config['smtp_recipient'] = 'controlled@example.test'
        home = b'<nav><a href="/blog/">Blog</a><a href="/#contact">Contact</a></nav><img src="https://gama-software.com/logo.svg" class="custom-logo"><form class="gama-contact-form"><input name="name"><input name="email"><input name="phone"><textarea name="message"></textarea><input name="gama_contact_nonce" value="fixture-nonce"></form>'
        pages = {'/': (200, {'Content-Type':'text/html'}, home),
                 '/blog/':(200, {'Content-Type':'text/html'}, b'<h1>Blog</h1>'),
                 '/wp-login.php':(200, {'Content-Type':'text/html'}, b'<form id="loginform"><input name="log"><input name="pwd"></form>'),
                 '/wp-json/':(200, {'Content-Type':'application/json'}, b'{"routes":{"/gama-contact/v1/messages":{"methods":["POST"]}}}'),
                 '/logo.svg':(200, {'Content-Type':'image/svg+xml'}, b'<svg></svg>')}
        with HTTPFixture(pages) as http, mock.patch('wordpress.release.host_ops.ORIGIN', http.url):
            self.ops.verify(OLD)
            self.assertEqual(['/', '/blog/', '/wp-login.php', '/logo.svg', '/wp-json/'], http.requests)
            calls = [json.loads(line) for line in (self.root/'calls').read_text().splitlines()]
            self.assertEqual('controlled@example.test', calls[-1][-1])
            req = request()
            req.update(kind='first-cutover', image=OLD, authorization_ref='owner-approval')
            self.ops.request = req
            self.ops.smtp_deferral = {key: req[key] for key in ('operation_id', 'git_sha', 'image', 'authorization_ref')}
            self.ops.smtp_deferral['accept_contact_delivery_unavailable'] = True
            # The real adapter must execute the runtime fail-closed check, not a send.
            with mock.patch.object(self.ops, '_docker', wraps=self.ops._docker) as docker:
                self.ops.verify(OLD)
                last = docker.call_args.args
                self.assertIn('gama_mail_transport_config', last[-2])
                self.assertIn('=== false', last[-2])
                self.data['mail_fail_closed'] = False
                self.write_data()
                with self.assertRaises(ReleaseValidationError): self.ops.verify(OLD)
            self.ops.smtp_deferral = None
            pages['/'] = (200, {'Content-Type':'text/html'}, home.replace(b'gama-contact-form', b'missing-contact'))
            with self.assertRaises(ReleaseValidationError): self.ops.verify(OLD)
            pages['/'] = (200, {'Content-Type':'text/html'}, home)
            pages['/blog/'] = (200, {'Content-Type':'text/html','X-Robots-Tag':'noindex'}, b'<h1>Blog</h1>')
            with self.assertRaises(ReleaseValidationError): self.ops.verify(OLD)

    def test_infrastructure_proof_binds_operation_resources_and_fresh_offhost_restore(self):
        adapter = self.root / 'proof'
        adapter.write_text('''#!/usr/bin/python3
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
assert sys.argv[1:] == ['verify-backup']
binding=json.load(sys.stdin)
now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
out={'binding_sha256':hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
     'reference':'offhost:operation/run-101','sha256':'1'*64,'offhost_uri':'s3://fixture-backup/run-101',
     'encrypted':True,'retention_days':30,'created_utc':now,'restore_verified_utc':now,'routing_recovery_reference':None}
mutation=json.loads(Path(__file__).with_name('proof-mutation.json').read_text())
out.update(mutation)
print(json.dumps(out))
''')
        adapter.chmod(0o700)
        mutation_path = self.root / 'proof-mutation.json'; mutation_path.write_text('{}')
        self.ops.request = request()
        self.config.update(backup_adapter=str(adapter),backup_source='fixture:/backup',
                           minimum_retention_days=14,restore_max_age_seconds=3600)
        evidence = self.ops._evidence('backup_adapter','verify-backup',{'scope':'wordpress','checksums':{'database.sql':'a'*64}})
        self.assertEqual('offhost:operation/run-101', evidence['reference'])
        for mutation in ({'binding_sha256':'0'*64}, {'encrypted':False}, {'retention_days':1},
                         {'created_utc':'2020-01-01T00:00:00Z'}, {'restore_verified_utc':'2020-01-01T00:00:00Z'},
                         {'offhost_uri':'https://secret:password@example.test/backup'}, {'unexpected':True}):
            with self.subTest(mutation=mutation):
                mutation_path.write_text(json.dumps(mutation))
                with self.assertRaises(ReleaseValidationError):
                    self.ops._evidence('backup_adapter','verify-backup',{'scope':'wordpress','checksums':{'database.sql':'a'*64}})

    def test_process_output_is_bounded_and_inherited_secrets_are_not_forwarded(self):
        from wordpress.release.host_ops import run
        tool = self.root/'environment'
        tool.write_text('#!/usr/bin/python3\nimport json,os\nprint(json.dumps(sorted(os.environ)))\n')
        tool.chmod(0o700)
        with mock.patch.dict(os.environ, {'GITHUB_READ_TOKEN':'secret','SMTP_PASSWORD':'secret','SSH_AUTH_SOCK':'secret'}):
            self.assertEqual(['HOME','LANG','PATH'], json.loads(run([str(tool)])))
        tool.write_text('#!/usr/bin/python3\nimport sys\nsys.stdout.write("x"*1048577)\n')
        with self.assertRaises(ReleaseValidationError): run([str(tool)])

    def test_nonreading_adapter_cannot_block_timeout_while_stdin_is_written(self):
        from wordpress.release.host_ops import run
        tool = self.root/'nonreading'
        tool.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(2)\n')
        tool.chmod(0o700)
        started = time.monotonic()
        with self.assertRaises(ReleaseValidationError): run([str(tool)], data={'input':'x'*500000}, timeout=.1)
        self.assertLess(time.monotonic()-started, 1)

    def test_real_backup_helper_and_findmnt_boundary_produce_verified_checksum_inventory(self):
        # A CI checkout belongs to the runner, not the production root account.
        # Install exact helper bytes into this test's private root-owned tree;
        # never chown the checkout or bypass HostOps' real protection checks.
        source_root = Path(__file__).resolve().parents[2]
        installed_root = self.root/'installed-wordpress'
        for name in ('bin/deploy-production', 'bin/rollback-production',
                     'bin/backup', 'deploy/compose.yaml'):
            target = installed_root/name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(source_root/name, target)
            target.chmod(0o700 if name.startswith('bin/') else 0o600)
        self.config['wordpress_root'] = str(installed_root)
        helper = installed_root/'bin/backup'
        for owner, mode in ((1001, 0o700), (0, 0o720)):
            with self.subTest(untrusted_owner=owner, mode=oct(mode)):
                os.chown(helper, owner, 0)
                helper.chmod(mode)
                with self.assertRaises(ReleaseValidationError):
                    self.ops._repo()
        os.chown(helper, 0, 0)
        helper.chmod(0o700)
        backup_root = self.root/'backup'; backup_root.mkdir()
        findmnt = self.root/'findmnt'
        findmnt.write_text('#!/usr/bin/python3\nimport sys\na=sys.argv[1:]\n'
                          + 'assert a in '+repr([['-n','-o',field,'--target',str(backup_root)] for field in ('SOURCE','TARGET')])+'\n'
                          + 'print("fixture:/backup" if a[2] == "SOURCE" else '+repr(str(backup_root))+')\n')
        findmnt.chmod(0o700)
        proof = self.root/'backup-proof'
        proof.write_text('''#!/usr/bin/python3
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
assert sys.argv[1:] == ['verify-backup']
b=json.load(sys.stdin)
assert set(b['checksums']) == {'database.sql','uploads.tar','manifest.txt'}
assert b['operation_id'] == 'run-101' and b['scope'] == 'wordpress'
for name,digest in b['checksums'].items(): assert hashlib.sha256((Path(b['directory'])/name).read_bytes()).hexdigest() == digest
now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
print(json.dumps({'binding_sha256':hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'reference':'offhost:verified/run-101','sha256':'1'*64,'offhost_uri':'s3://fixture-backup/run-101',
 'encrypted':True,'retention_days':30,'created_utc':now,'restore_verified_utc':now,'routing_recovery_reference':None}))
''')
        proof.chmod(0o700)
        self.config.update(findmnt=str(findmnt),backup_root=str(backup_root),backup_source='fixture:/backup',
                           backup_adapter=str(proof),
                           minimum_retention_days=14,restore_max_age_seconds=3600)
        self.ops.request = request()
        result = self.ops.backup('wordpress','run-101')
        self.assertEqual('offhost:verified/run-101', result['reference'])
        self.assertIn('CREATE TABLE fixture', (backup_root/'run-101/database.sql').read_text())
        calls = [json.loads(line) for line in (self.root/'calls').read_text().splitlines()]
        self.assertTrue(any(c[:2] == ['exec','db'] for c in calls))
        self.assertFalse(any('stop' in c or 'bootstrap' in c for c in calls))
        self.config['backup_source'] = 'different:/mount'
        with self.assertRaises(ReleaseValidationError): self.ops._mount()
