"""Publisher integration tests: actual HTTP reads, ZIP transport and subprocesses."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

from wordpress.release.manifest import ReleaseValidationError
from wordpress.release import transport as transport_boundary
from wordpress.tests.release.test_github_source import HTTPFixture, ROOT, SHA, event, responses, solo_responses
from wordpress.tests.release.test_transport import literal_valid_manifest, TAR_BYTES

try:
    from wordpress.release.promote import validate_transport, publish
    from wordpress.release.github_source import resolve_source
except ModuleNotFoundError:
    validate_transport = publish = resolve_source = None

IMAGE_ID = 'sha256:' + 'a' * 64
REPOSITORY = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress'
DIGEST = 'sha256:' + 'd' * 64


class DockerFixture:
    """Strict external process replacement; real publisher determines all calls."""
    def __init__(self, root, mutation=''):
        self.log = root / 'docker-log.jsonl'
        self.executable = root / 'docker'
        self.executable.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
log = Path(__file__).with_name('docker-log.jsonl')
with log.open('a') as output:
    output.write(json.dumps({'args': args, 'env': sorted(os.environ)}) + '\\n')
image = 'sha256:' + 'a' * 64
repo = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress'
digest = 'sha256:' + 'd' * 64
tag = repo + ':sha-1234567890abcdef1234567890abcdef12345678-987654321-1'
mutation = MUTATION
if args == ['load']:
    if sys.stdin.buffer.read() != b'literal docker image tar bytes\\n':
        sys.exit(21)
elif args == ['image', 'inspect', image] or args == ['image', 'inspect', repo + '@' + digest]:
    pulled = '@' in args[-1]
    result = {'Id': image, 'Os': 'linux', 'Architecture': 'amd64',
              'Config': {'Labels': {'org.opencontainers.image.revision': '1234567890abcdef1234567890abcdef12345678',
                                   'com.gamasoftware.wordpress.release-marker': 'release'}},
              'RootFS': {'Type': 'layers', 'Layers': ['sha256:' + 'e' * 64, 'sha256:' + 'f' * 64]},
              'RepoDigests': [repo + '@' + digest]}
    if mutation == 'wrong_platform': result['Architecture'] = 'arm64'
    if mutation == 'development': result['Config']['Labels']['com.gamasoftware.wordpress.release-marker'] = 'development'
    if mutation == 'wrong_revision': result['Config']['Labels']['org.opencontainers.image.revision'] = 'b' * 40
    if pulled and mutation == 'wrong_layers': result['RootFS']['Layers'].reverse()
    if pulled and mutation == 'wrong_id': result['Id'] = 'sha256:' + 'b' * 64
    print(json.dumps([result]))
elif args == ['tag', image, tag]:
    pass
elif args == ['push', tag]:
    print('sha-123: digest: ' + digest + ' size: 1234')
elif args == ['pull', '--platform', 'linux/amd64', repo + '@' + digest]:
    pass
else:
    sys.exit(22)
'''.replace('MUTATION', repr(mutation)))
        self.executable.chmod(0o700)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []


class PromoteTests(unittest.TestCase):
    def test_solo_report_is_rechecked_before_any_registry_operation(self):
        for mutation in ('none', 'report-edited', 'wrong-merger'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as case:
                self.root = Path(case).resolve()
                docker = DockerFixture(self.root)
                with HTTPFixture(solo_responses()) as http:
                    source = self.transport(http)
                    if mutation == 'report-edited':
                        http.data[ROOT + '/pulls/12/reviews?per_page=100&page=1'][0]['body'] += ' '
                    elif mutation == 'wrong-merger':
                        http.data[ROOT + '/pulls/12']['merged_by'] = {'id': 1, 'login': 'other', 'type': 'User'}
                    with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
                        if mutation == 'none':
                            result = publish(str(self.root / 'unpacked'), source, REPOSITORY,
                                             http.api(), runner_temp=str(self.root))
                            self.assertEqual(result['image'], REPOSITORY + '@' + DIGEST)
                        else:
                            with self.assertRaises(ReleaseValidationError):
                                publish(str(self.root / 'unpacked'), source, REPOSITORY,
                                        http.api(), runner_temp=str(self.root))
                self.assertEqual([call['args'][0] for call in docker.calls()],
                                 ['load', 'image', 'tag', 'push', 'pull', 'image'] if mutation == 'none' else [])

    def test_transport_download_follows_approved_storage_without_api_credential(self):
        import urllib.request
        with HTTPFixture() as http:
            validated = self.transport(http)
            source = resolve_source(event(),http.api(),'wordpress')
            path = ROOT+'/actions/artifacts/555/zip'
            body = http.data[path]
            http.data[path] = (302, {'Location':'https://release.blob.core.windows.net/archive?sig=fixture'}, b'')
            http.data['/storage'] = body
            api = http.api(); real_open = api.opener.open
            def open_request(req, **kwargs):
                if req.full_url.startswith(http.url): return real_open(req, **kwargs)
                self.assertEqual({},dict(req.header_items()))
                return real_open(urllib.request.Request(http.url+'/storage',headers=dict(req.header_items())), **kwargs)
            api.opener.open = open_request
            result = validate_transport(source,api,str(self.root/'redirect-unpacked'),str(self.root))
            self.assertEqual(validated['transport']['manifest_sha256'],result['transport']['manifest_sha256'])
            self.assertNotIn('Authorization',http.request_headers[http.requests.index('/storage')])

    def setUp(self):
        self.assertIsNotNone(publish, 'production publisher is missing')
        environment = {key: value for key, value in os.environ.items()
                       if 'SSH' not in key.upper() and 'SMTP' not in key.upper()}
        patch = mock.patch.dict(os.environ, environment, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def transport(self, http):
        manifest = literal_valid_manifest()
        manifest['workflow_id'] = 351411087
        archive = self.root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('release.json', json.dumps(manifest))
            zipped.writestr('image.tar', TAR_BYTES)
        body = archive.read_bytes()
        metadata = http.data[ROOT + '/actions/runs/987654321/artifacts?per_page=100&page=1']['artifacts'][0]
        metadata.update(digest='sha256:' + hashlib.sha256(body).hexdigest(), size_in_bytes=len(body))
        http.data[ROOT + '/actions/artifacts/555/zip'] = body
        source = resolve_source(event(), http.api(), 'wordpress')
        return validate_transport(source, http.api(), str(self.root / 'unpacked'), str(self.root))

    def test_publish_reads_exact_artifact_and_loads_then_pulls_digest_without_build(self):
        docker = DockerFixture(self.root)
        with HTTPFixture() as http:
            source = self.transport(http)
            with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH'],
                                             'GITHUB_TOKEN': 'must-not-reach-docker'}):
                result = publish(str(self.root / 'unpacked'), source, REPOSITORY, http.api(), runner_temp=str(self.root))
            self.assertIn(ROOT + '/actions/artifacts/555/zip', http.requests)
        self.assertEqual(result['image'], REPOSITORY + '@' + DIGEST)
        self.assertEqual(result['image_id'], IMAGE_ID)
        calls = docker.calls()
        self.assertEqual([c['args'][0] for c in calls], ['load', 'image', 'tag', 'push', 'pull', 'image'])
        self.assertFalse(any('GITHUB_TOKEN' in c['env'] for c in calls))

    def test_wrong_repository_or_modified_tar_refuses_before_docker(self):
        for mutation in ('repository', 'newline', 'tar', 'manifest', 'source_attempt'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as case:
                self.root = Path(case).resolve()
                docker = DockerFixture(self.root)
                with HTTPFixture() as http:
                    source = self.transport(http)
                    repository = REPOSITORY
                    if mutation == 'repository': repository += '-other'
                    if mutation == 'newline': repository += '\noutput=evil'
                    if mutation == 'tar': (self.root / 'unpacked/image.tar').write_bytes(b'altered')
                    if mutation == 'manifest':
                        manifest = self.root / 'unpacked/release.json'
                        manifest.write_text(manifest.read_text() + ' ')
                    if mutation == 'source_attempt':
                        http.data[ROOT + '/actions/runs/987654321']['run_attempt'] = 2
                    with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
                        with self.assertRaises(ReleaseValidationError):
                            publish(str(self.root / 'unpacked'), source, repository, http.api(), runner_temp=str(self.root))
                self.assertEqual(docker.calls(), [])

    def test_loaded_identity_fails_before_tag_and_pulled_identity_before_output(self):
        for mutation in ('wrong_platform', 'development', 'wrong_revision', 'wrong_layers', 'wrong_id'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as case:
                self.root = Path(case).resolve()
                docker = DockerFixture(self.root, mutation)
                with HTTPFixture() as http:
                    source = self.transport(http)
                    with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
                        with self.assertRaises(ReleaseValidationError):
                            publish(str(self.root / 'unpacked'), source, REPOSITORY, http.api(), runner_temp=str(self.root))
                calls = [c['args'][0] for c in docker.calls()]
                self.assertEqual(calls, ['load', 'image'] if mutation in
                                 ('wrong_platform', 'development', 'wrong_revision') else
                                 ['load', 'image', 'tag', 'push', 'pull', 'image'])

    def test_archive_digest_mismatch_never_unpacks(self):
        with HTTPFixture() as http:
            source = resolve_source(event(), http.api(), 'wordpress')
            http.data[ROOT + '/actions/artifacts/555/zip'] = b'bad zip'
            with self.assertRaises(ReleaseValidationError):
                validate_transport(source, http.api(), str(self.root / 'unpacked'), str(self.root))
        self.assertFalse((self.root / 'unpacked').exists())

    def test_cli_disabled_mode_writes_null_without_credential_or_docker(self):
        event_path = self.root / 'event.json'
        event_path.write_text('{}')
        result = subprocess.run([sys.executable, '-m', 'wordpress.release.promote', 'validate-source',
                                 '--event', str(event_path), '--mode', 'off', '--operation', 'standard',
                                 '--output', str(self.root / 'source.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'source.json').read_text()), None)

    def test_publisher_refuses_ssh_secret_before_http_or_docker(self):
        docker = DockerFixture(self.root)
        with HTTPFixture({}) as http, mock.patch.dict(os.environ, {'WORDPRESS_SSH_KEY': 'fixture'}):
            with self.assertRaises(ReleaseValidationError):
                publish(str(self.root / 'unpacked'), {}, REPOSITORY, http.api(), runner_temp=str(self.root))
            self.assertEqual(http.requests, [])
        self.assertEqual(docker.calls(), [])

    def test_source_rerun_after_load_stops_before_registry_tag(self):
        from wordpress.release import promote
        docker = DockerFixture(self.root)
        real_docker = promote._docker
        with HTTPFixture() as http:
            source = self.transport(http)

            def execute(arguments, **kwargs):
                result = real_docker(arguments, **kwargs)
                if arguments == ['load']:
                    http.data[ROOT + '/actions/runs/987654321']['run_attempt'] = 2
                return result

            with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}), \
                    mock.patch.object(promote, '_docker', side_effect=execute):
                with self.assertRaises(ReleaseValidationError):
                    publish(str(self.root / 'unpacked'), source, REPOSITORY, http.api(), runner_temp=str(self.root))
        self.assertEqual([call['args'][0] for call in docker.calls()], ['load', 'image'])

    def test_replaced_tar_after_transport_verification_is_hashed_again(self):
        docker = DockerFixture(self.root)
        real_verify = transport_boundary.verify_archive
        with HTTPFixture() as http:
            source = self.transport(http)

            def verify_then_replace(*args):
                result = real_verify(*args)
                image = self.root / 'unpacked/image.tar'
                image.unlink()
                image.write_bytes(b'replaced after verification')
                return result

            with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}), \
                    mock.patch.object(transport_boundary, 'verify_archive', side_effect=verify_then_replace):
                with self.assertRaises(ReleaseValidationError):
                    publish(str(self.root / 'unpacked'), source, REPOSITORY, http.api(), runner_temp=str(self.root))
        self.assertEqual(docker.calls(), [])

    def test_existing_cli_output_refuses_before_any_docker_operation(self):
        from wordpress.release import promote
        docker = DockerFixture(self.root)
        output = self.root / 'published.json'
        output.write_text('existing result')
        with HTTPFixture() as http:
            source = self.transport(http)
            source_path = self.root / 'source.json'
            source_path.write_text(json.dumps(source))
            api = http.api()
            with mock.patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH'],
                                             'RUNNER_TEMP': str(self.root)}), \
                    mock.patch.object(promote, 'GitHubAPI', return_value=api), \
                    mock.patch('sys.stderr'):
                code = promote.main(['publish', '--release-dir', str(self.root / 'unpacked'),
                                     '--source', str(source_path), '--repository', REPOSITORY,
                                     '--output', str(output)])
        self.assertEqual(code, 1)
        self.assertEqual(output.read_text(), 'existing result')
        self.assertEqual(docker.calls(), [])


if __name__ == '__main__':
    unittest.main()
