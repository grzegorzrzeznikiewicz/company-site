"""OVH routing contract at a temporary filesystem and command boundary."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from wordpress.routing.ovh import Routing, RoutingError


IMAGE = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:' + 'a' * 64
SHA = 'b' * 40
ORIGINAL = '''server {
    listen 443 ssl;
    ssl_certificate /etc/cert.pem;
    location / {
        proxy_pass http://127.0.0.1:8090;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:18080;
    }
}
'''


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / 'gama-software.com'
        self.site.write_text(ORIGINAL)
        self.enabled = self.root / 'sites-enabled' / 'gama-software.com'
        self.enabled.parent.mkdir()
        self.enabled.symlink_to(self.site)
        self.control = self.root / 'control'
        self.control.mkdir()
        self.fake = self.root / 'fake-command'
        self.fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
root=Path(__file__).parent
with (root/'calls').open('a') as out: out.write(json.dumps([Path(sys.argv[0]).name,*sys.argv[1:]])+'\\n')
if (root/('fail-'+Path(sys.argv[0]).name)).exists(): sys.exit(1)
if Path(sys.argv[0]).name == 'docker':
    image='ghcr.io/grzegorzrzeznikiewicz/gama-wordpress@sha256:'+'a'*64
    if sys.argv[1:3] == ['ps','-aq']: print('abcd1234')
    elif sys.argv[1:] == ['inspect','abcd1234']:
        print(json.dumps([{'Image':'sha256:'+'c'*64,'Config':{'Image':image,'Labels':{'com.docker.compose.project':'gama-wp-production','com.docker.compose.service':'wordpress'}},'State':{'Running':True,'Health':{'Status':'healthy'}}}]))
    elif sys.argv[1:] == ['image','inspect',image]:
        revision='d'*40 if (root/'wrong-revision').exists() else 'b'*40
        print(json.dumps([{'Id':'sha256:'+'c'*64,'RepoDigests':[image],'Config':{'Labels':{'org.opencontainers.image.revision':revision}}}]))
    else: sys.exit(2)
''')
        self.fake.chmod(0o700)
        for name in ('docker', 'nginx', 'systemctl'):
            (self.root / name).symlink_to(self.fake)
        self.routing = Routing(self.site, self.control, self.root/'docker', self.root/'nginx',
                               self.root/'systemctl', owner_uid=os.geteuid(),
                               enabled_site=self.enabled)
        self.binding = dict(operation_id='cutover-100', deployment_operation_id='cutover-100',
                            git_sha=SHA, image=IMAGE)

    def calls(self):
        path = self.root / 'calls'
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def prepare(self):
        return self.routing.prepare(self.binding)

    def test_prepare_is_durable_idempotent_and_bound(self):
        proof = self.prepare()
        want = hashlib.sha256(json.dumps(self.binding, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(want, proof['binding_sha256'])
        self.assertEqual(proof, self.prepare())
        self.assertEqual(ORIGINAL, self.site.read_text())
        with self.assertRaises(RoutingError):
            self.routing.prepare({**self.binding, 'image': IMAGE[:-1] + 'b'})

    def test_cutover_changes_only_root_port_then_rollback_restores_exact_bytes(self):
        self.prepare()
        self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL.replace('127.0.0.1:8090', '127.0.0.1:8000'), self.site.read_text())
        self.assertIn(['nginx', '-t'], self.calls())
        self.assertIn(['systemctl', 'reload', 'nginx'], self.calls())
        self.routing.rollback('legacy', 'cutover-100', 'recovery-200')
        self.assertEqual(ORIGINAL, self.site.read_text())
        self.routing.rollback('legacy', 'cutover-100', 'recovery-200')
        self.assertEqual(ORIGINAL, self.site.read_text())
        self.assertEqual(self.routing.verify({**self.binding, 'operation_id': 'recovery-200'})['routing_recovery_reference'],
                         self.prepare()['routing_recovery_reference'])

    def test_drift_refused_without_overwrite(self):
        self.prepare()
        self.site.write_text(ORIGINAL.replace('/etc/cert.pem', '/etc/changed.pem'))
        with self.assertRaises(RoutingError): self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertIn('/etc/changed.pem', self.site.read_text())
        self.assertNotIn(['systemctl', 'reload', 'nginx'], self.calls())

    def test_missing_or_redirected_active_link_refuses_all_routing_operations(self):
        for replacement in (None, self.root / 'other-site'):
            with self.subTest(replacement=replacement):
                self.enabled.unlink(missing_ok=True)
                if replacement is not None:
                    replacement.write_text(ORIGINAL)
                    self.enabled.symlink_to(replacement)
                with self.assertRaises(RoutingError): self.prepare()
                self.assertFalse((self.control/'routing-cutover-100.json').exists())

                self.enabled.unlink(missing_ok=True)
                self.enabled.symlink_to(self.site)
                self.prepare()
                self.enabled.unlink()
                if replacement is not None: self.enabled.symlink_to(replacement)
                before = self.site.read_bytes()
                with self.assertRaises(RoutingError):
                    self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
                with self.assertRaises(RoutingError): self.routing.verify(self.binding)
                with self.assertRaises(RoutingError):
                    self.routing.rollback('legacy', 'cutover-100', 'rollback-200')
                self.assertEqual(before, self.site.read_bytes())
                self.assertNotIn(['systemctl', 'reload', 'nginx'], self.calls())
                (self.control/'routing-cutover-100.json').unlink()

    def test_commented_legacy_directive_is_not_a_switchable_route(self):
        self.site.write_text(ORIGINAL.replace('        proxy_pass http://127.0.0.1:8090;',
                                              '        # proxy_pass http://127.0.0.1:8090;'))
        with self.assertRaises(RoutingError): self.prepare()

    def test_validation_failure_restores_legacy(self):
        self.prepare()
        (self.root/'fail-nginx').touch()
        with self.assertRaises(RoutingError): self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL, self.site.read_text())

    def test_reload_failure_restores_legacy(self):
        self.prepare()
        (self.root/'fail-systemctl').touch()
        with self.assertRaises(RoutingError): self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL, self.site.read_text())

    def test_retry_reload_failure_restores_legacy(self):
        self.prepare()
        self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        (self.root/'fail-systemctl').touch()
        with self.assertRaises(RoutingError):
            self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL, self.site.read_text())

    def test_foreign_image_and_bad_ids_refuse_before_edit(self):
        self.prepare()
        with self.assertRaises(RoutingError): self.routing.cutover('foreign', '8000', IMAGE, 'cutover-100')
        with self.assertRaises(RoutingError): self.routing.rollback('legacy', '../cutover-100', 'recovery-200')
        with self.assertRaises(RoutingError): self.routing.prepare({**self.binding, 'operation_id': '../x'})
        self.assertEqual(ORIGINAL, self.site.read_text())

    def test_actual_container_image_revision_must_match_saved_sha(self):
        self.prepare()
        (self.root/'wrong-revision').touch()
        with self.assertRaises(RoutingError):
            self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL, self.site.read_text())

    def test_symlinked_snapshot_refused(self):
        self.prepare()
        state = self.control/'routing-cutover-100.json'
        state.unlink()
        state.symlink_to(self.site)
        with self.assertRaises(RoutingError): self.routing.cutover('gama-wp-production', '8000', IMAGE, 'cutover-100')
        self.assertEqual(ORIGINAL, self.site.read_text())


if __name__ == '__main__': unittest.main()
