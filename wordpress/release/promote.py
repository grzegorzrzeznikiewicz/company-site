#!/usr/bin/env python3
"""Read provenance, validate transport, then publish only the sealed candidate.

Invoke from trusted main code. Never execute anything in the downloaded artifact.
Registry credentials belong in an isolated Docker config; GitHub provenance uses
GITHUB_READ_TOKEN. Docker receives an explicit minimal environment, no API token.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wordpress.release import transport
from wordpress.release.github_source import (
    GitHubAPI, SourcePendingError, authorization_comment, json_object, require, resolve_source,
)
from wordpress.release.manifest import ReleaseValidationError

IMAGE_REPOSITORY = 'ghcr.io/grzegorzrzeznikiewicz/gama-wordpress'
SOURCE_FIELDS = frozenset({'schema_version', 'operation', 'mode', 'event_payload',
                           'provenance', 'artifact', 'approval'})
TRANSPORT_FIELDS = frozenset({'artifact_id', 'artifact_digest', 'manifest_sha256', 'release_dir'})


def _read_json(path):
    parent, name = transport._open_parent(path, 'JSON input')
    try:
        descriptor, info = transport._open_regular_file(parent, name, 2 * 1024 * 1024)
        try:
            raw = transport._read_open_file(descriptor, name, info, 2 * 1024 * 1024)
        finally:
            os.close(descriptor)
        transport._assert_file_binding(parent, name, info)
    finally:
        os.close(parent)
    return json_object(raw)


def _new_output(path, value):
    parent, name = transport._open_parent(path, 'new JSON output')
    try:
        descriptor = os.open(name, transport._file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, 'w') as output:
            json.dump(value, output, sort_keys=True, separators=(',', ':'), allow_nan=False)
            output.write('\n')
    finally:
        os.close(parent)


def _preflight_output(path):
    parent, name = transport._open_parent(path, 'new JSON output')
    try:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise ReleaseValidationError('new JSON output already exists')
    finally:
        os.close(parent)


def _source(source, *, receipt=False):
    require(type(source) is dict, 'validated source object required')
    fields = SOURCE_FIELDS | ({'authorization'} if source.get('operation') == 'first-cutover' else set())
    if receipt:
        fields = fields | {'transport'}
    require(frozenset(source) == fields and type(source.get('schema_version')) is int
            and source['schema_version'] == 1, 'source fields do not match schema')
    require(source.get('operation') in ('standard', 'first-cutover'), 'invalid trusted operation')
    require(source.get('mode') == ('wordpress' if source['operation'] == 'standard' else 'off'),
            'source mode does not permit this operation')
    return {key: value for key, value in source.items() if key != 'transport'}


def _recheck(source, api, *, receipt=False):
    expected = _source(source, receipt=receipt)
    fresh = resolve_source(expected['event_payload'], api, expected['mode'], operation=expected['operation'])
    require(fresh == expected, 'source provenance changed before promotion')
    return expected


def _runner_path(path, runner_temp):
    require(type(runner_temp) is str and runner_temp.startswith('/'), 'absolute RUNNER_TEMP required')
    parts = transport._path_parts(path, 'release directory')
    root_parts = transport._path_parts(runner_temp, 'runner temp')
    require(parts[:len(root_parts)] == root_parts and len(parts) > len(root_parts),
            'release directory must be beneath protected runner temp')
    parent, _, directory, _ = transport._open_existing_directory(runner_temp, 'runner temp')
    os.close(directory)
    os.close(parent)


def _manifest_digest(directory):
    parent, name, descriptor, initial = transport._open_existing_directory(directory, 'release directory')
    try:
        manifest, info = transport._open_regular_file(descriptor, 'release.json', 64 * 1024)
        try:
            digest = transport._read_open_file(manifest, 'release.json', info, 64 * 1024, hashlib.sha256())
        finally:
            os.close(manifest)
        transport._assert_file_binding(descriptor, 'release.json', info)
        transport._assert_directory_binding(parent, name, initial)
        return digest
    finally:
        os.close(descriptor)
        os.close(parent)


def validate_transport(source, api, destination, runner_temp):
    """Download immutable ID and bind ZIP digest to a runner-local manifest hash.

    A separate publishing runner must perform its own validation/download. The
    release_dir receipt is local data, not a portable path attestation.
    """
    trusted = _recheck(source, api)
    _runner_path(destination, runner_temp)
    with tempfile.TemporaryDirectory(prefix='wordpress-transport-', dir=runner_temp) as temporary:
        archive = str(Path(temporary) / 'release.zip')
        api.download(trusted['artifact'], archive)
        transport.unpack_release(archive, destination, trusted['provenance'])
    return {**trusted, 'transport': {
        'artifact_id': trusted['artifact']['id'], 'artifact_digest': trusted['artifact']['digest'],
        'manifest_sha256': _manifest_digest(destination), 'release_dir': destination}}


def _docker(arguments, *, stdin=None):
    allowed = ('PATH', 'HOME', 'DOCKER_CONFIG', 'DOCKER_HOST', 'DOCKER_TLS_VERIFY',
               'DOCKER_CERT_PATH', 'XDG_RUNTIME_DIR', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR')
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment['LC_ALL'] = 'C'
    try:
        return subprocess.run(['docker'] + arguments, stdin=stdin, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True, timeout=1800,
                              env=environment).stdout.decode('utf-8')
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise ReleaseValidationError('Docker publication boundary failed') from error


def _inspect(reference, manifest):
    value = json_object(_docker(['image', 'inspect', reference]))
    require(type(value) is list and len(value) == 1 and type(value[0]) is dict,
            'invalid Docker inspection')
    image = value[0]
    labels = image.get('Config', {}).get('Labels', {})
    layers = image.get('RootFS', {}).get('Layers')
    require(image.get('Id') == manifest['image_id'] and image.get('Os') == 'linux'
            and image.get('Architecture') == 'amd64' and image.get('Variant') in (None, '')
            and labels.get('org.opencontainers.image.revision') == manifest['git_sha']
            and labels.get('com.gamasoftware.wordpress.release-marker') == 'release'
            and image.get('RootFS', {}).get('Type') == 'layers'
            and type(layers) is list and layers
            and all(type(layer) is str and re.fullmatch('sha256:[0-9a-f]{64}', layer) for layer in layers),
            'registry image identity does not match release candidate')
    if '@' in reference:
        require(reference in image.get('RepoDigests', []), 'digest readback does not identify pulled image')
    return layers


def _load_same_archive(directory, manifest):
    parent, name, descriptor, initial = transport._open_existing_directory(directory, 'release directory')
    try:
        image, info = transport._open_regular_file(descriptor, 'image.tar', transport._IMAGE_LIMIT)
        with os.fdopen(image, 'rb') as stream:
            digest = transport._read_open_file(stream.fileno(), 'image.tar', info,
                                               transport._IMAGE_LIMIT, hashlib.sha256())
            require(digest == manifest['archive_sha256'], 'image TAR changed immediately before Docker load')
            transport._assert_file_binding(descriptor, 'image.tar', info)
            transport._assert_directory_binding(parent, name, initial)
            stream.seek(0)
            _docker(['load'], stdin=stream)
    finally:
        os.close(descriptor)
        os.close(parent)


def publish(release_dir, source, repository, api, *, runner_temp):
    """Registry is the only write boundary. Revalidate all source before Docker."""
    require(repository == IMAGE_REPOSITORY, 'image repository is not the allowed destination')
    require(not any('SSH' in name.upper() or 'SMTP' in name.upper() for name in os.environ),
            'publisher must not receive SSH or SMTP secrets/environment')
    trusted = _recheck(source, api, receipt=True)
    _runner_path(release_dir, runner_temp)
    receipt = source['transport']
    require(type(receipt) is dict and frozenset(receipt) == TRANSPORT_FIELDS
            and receipt['artifact_id'] == trusted['artifact']['id']
            and receipt['artifact_digest'] == trusted['artifact']['digest']
            and receipt['release_dir'] == release_dir, 'transport receipt does not bind selected artifact')
    manifest = transport.verify_archive(release_dir, trusted['provenance'])
    require(receipt['manifest_sha256'] == _manifest_digest(release_dir),
            'local manifest differs from verified GitHub transport')
    _load_same_archive(release_dir, manifest)
    layers = _inspect(manifest['image_id'], manifest)
    _recheck(source, api, receipt=True)
    tag = '{0}:sha-{1}-{2}-{3}'.format(repository, manifest['git_sha'], manifest['run_id'], manifest['run_attempt'])
    _docker(['tag', manifest['image_id'], tag])
    pushed = _docker(['push', tag])
    digests = re.findall(r'\bdigest: (sha256:[0-9a-f]{64})\b', pushed)
    require(len(digests) == 1, 'registry push did not return one immutable digest')
    image = repository + '@' + digests[0]
    _docker(['pull', '--platform', 'linux/amd64', image])
    require(_inspect(image, manifest) == layers, 'registry changed ordered RootFS identity')
    return {'schema_version': 1, 'source': trusted, 'image': image,
            'image_id': manifest['image_id'], 'archive_sha256': manifest['archive_sha256'],
            'manifest_sha256': receipt['manifest_sha256'], 'platform': 'linux/amd64'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate-source')
    validate.add_argument('--event', required=True)
    validate.add_argument('--mode', required=True)
    validate.add_argument('--operation', choices=('standard', 'first-cutover'), required=True)
    validate.add_argument('--output', required=True)
    unpack = commands.add_parser('validate-transport')
    unpack.add_argument('--source', required=True)
    unpack.add_argument('--destination', required=True)
    unpack.add_argument('--output', required=True)
    publisher = commands.add_parser('publish')
    publisher.add_argument('--release-dir', required=True)
    publisher.add_argument('--source', required=True)
    publisher.add_argument('--repository', required=True)
    publisher.add_argument('--output', required=True)
    formatter = commands.add_parser('authorization-comment')
    formatter.add_argument('--authorization', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'authorization-comment':
            print(authorization_comment(_read_json(args.authorization)))
            return 0
        _preflight_output(args.output)
        # Disabled standard mode does not even require an API credential.
        if args.command == 'validate-source' and args.operation == 'standard' and args.mode != 'wordpress':
            _new_output(args.output, None)
            return 0
        api = GitHubAPI(os.environ.get('GITHUB_READ_TOKEN', ''))
        if args.command == 'validate-source':
            result = resolve_source(_read_json(args.event), api, args.mode, operation=args.operation)
        elif args.command == 'validate-transport':
            result = validate_transport(_read_json(args.source), api, args.destination, os.environ.get('RUNNER_TEMP'))
        else:
            result = publish(args.release_dir, _read_json(args.source), args.repository, api,
                             runner_temp=os.environ.get('RUNNER_TEMP'))
        _new_output(args.output, result)
        return 0
    except SourcePendingError as error:
        print('Release waiting: ' + str(error), file=sys.stderr)
        return 3
    except (ReleaseValidationError, OSError, TypeError, AttributeError, KeyError) as error:
        print('Release refused: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
