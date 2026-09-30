"""Bounded, descriptor-relative transport for WordPress release artifacts."""

import hashlib
import os
import stat
import zipfile
import zlib

from wordpress.release.manifest import (
    ReleaseValidationError,
    parse_manifest,
    validate_manifest,
)


_MANIFEST_NAME = 'release.json'
_IMAGE_NAME = 'image.tar'
_MEMBER_NAMES = frozenset({_MANIFEST_NAME, _IMAGE_NAME})
_PROVENANCE_FIELDS = frozenset(
    {
        'repository',
        'git_sha',
        'workflow_id',
        'workflow_path',
        'run_id',
        'run_attempt',
        'event',
        'ref',
        'platform',
    }
)
_MANIFEST_LIMIT = 64 * 1024
_IMAGE_LIMIT = 4 * 1024 * 1024 * 1024
_EXPANDED_LIMIT = _IMAGE_LIMIT + _MANIFEST_LIMIT
_READ_SIZE = 1024 * 1024


def _fail(message, cause=None):
    if cause is None:
        raise ReleaseValidationError(message)
    raise ReleaseValidationError(message) from cause


def _path_parts(path, label):
    try:
        raw_path = os.fspath(path)
    except TypeError as error:
        _fail('{0} must be an absolute filesystem path'.format(label), error)
    if type(raw_path) is not str or not raw_path.startswith('/'):
        _fail('{0} must be an absolute filesystem path'.format(label))
    if '\x00' in raw_path or raw_path == '/' or raw_path.endswith('/'):
        _fail('{0} is invalid'.format(label))
    if raw_path.startswith('//'):
        _fail('{0} is invalid'.format(label))

    parts = raw_path.split('/')[1:]
    if any(part in {'', '.', '..'} for part in parts):
        _fail('{0} is invalid'.format(label))
    return parts


def _directory_flags():
    required = ('O_DIRECTORY', 'O_NOFOLLOW')
    if any(not hasattr(os, name) for name in required):
        _fail('secure descriptor-relative filesystem operations are unavailable')
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, 'O_CLOEXEC', 0)
    )


def _file_flags(access):
    if not hasattr(os, 'O_NOFOLLOW'):
        _fail('secure no-follow filesystem operations are unavailable')
    return access | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)


def _require_expected(expected):
    if type(expected) is not dict or frozenset(expected) != _PROVENANCE_FIELDS:
        _fail('complete expected provenance is required')


def _require_trusted_directory(descriptor, label, allow_sticky):
    directory_stat = os.fstat(descriptor)
    if not stat.S_ISDIR(directory_stat.st_mode):
        _fail('{0} is not a directory'.format(label))

    trusted_owners = {0, os.geteuid()}
    writable_by_untrusted = directory_stat.st_mode & (
        stat.S_IWGRP | stat.S_IWOTH
    )
    sticky = directory_stat.st_mode & stat.S_ISVTX
    if directory_stat.st_uid not in trusted_owners or (
        writable_by_untrusted and not (allow_sticky and sticky)
    ):
        _fail('{0} is mutable by an untrusted account'.format(label))
    return directory_stat


def _open_parent(path, label):
    parts = _path_parts(path, label)
    flags = _directory_flags()
    descriptor = None
    next_descriptor = None
    try:
        descriptor = os.open('/', flags)
        _require_trusted_directory(descriptor, '{0} ancestor'.format(label), True)
        for part in parts[:-1]:
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            _require_trusted_directory(
                next_descriptor, '{0} ancestor'.format(label), True
            )
            os.close(descriptor)
            descriptor = next_descriptor
            next_descriptor = None
        return descriptor, parts[-1]
    except ReleaseValidationError:
        if next_descriptor is not None:
            os.close(next_descriptor)
        if descriptor is not None:
            os.close(descriptor)
        raise
    except OSError as error:
        if next_descriptor is not None:
            os.close(next_descriptor)
        if descriptor is not None:
            os.close(descriptor)
        _fail('{0} has an unavailable or unsafe ancestor'.format(label), error)


def _same_object(left, right):
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _open_existing_directory(path, label):
    parent_descriptor, name = _open_parent(path, label)
    directory_descriptor = None
    try:
        directory_descriptor = os.open(
            name, _directory_flags(), dir_fd=parent_descriptor
        )
        directory_stat = _require_trusted_directory(
            directory_descriptor, label, False
        )
        return parent_descriptor, name, directory_descriptor, directory_stat
    except ReleaseValidationError:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        os.close(parent_descriptor)
        raise
    except OSError as error:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        os.close(parent_descriptor)
        _fail('{0} is not a safe directory'.format(label), error)


def _assert_directory_binding(parent_descriptor, name, expected_stat):
    try:
        current = os.stat(
            name, dir_fd=parent_descriptor, follow_symlinks=False
        )
    except OSError as error:
        _fail('release directory changed during validation', error)
    if not stat.S_ISDIR(current.st_mode) or not _same_object(
        current, expected_stat
    ):
        _fail('release directory changed during validation')


def _assert_file_binding(directory_descriptor, name, expected_stat):
    try:
        current = os.stat(
            name, dir_fd=directory_descriptor, follow_symlinks=False
        )
    except OSError as error:
        _fail('{0} changed during validation'.format(name), error)
    if not stat.S_ISREG(current.st_mode) or not _same_object(
        current, expected_stat
    ):
        _fail('{0} changed during validation'.format(name))


def _member_is_regular(info):
    if info.is_dir() or info.external_attr & 0x10:
        return False
    if info.create_system != 3:
        return True
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    return file_type in (0, stat.S_IFREG)


def _inspect_members(archive):
    try:
        members = archive.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        _fail('invalid release ZIP', error)

    if len(members) != 2:
        _fail('release ZIP must contain exactly two members')

    by_name = {}
    total_size = 0
    for info in members:
        original_name = info.orig_filename
        if (
            type(original_name) is not str
            or original_name != info.filename
            or original_name not in _MEMBER_NAMES
            or original_name in by_name
        ):
            _fail('release ZIP contains an invalid member name')
        if info.flag_bits & 0x1:
            _fail('encrypted release ZIP members are forbidden')
        if not _member_is_regular(info):
            _fail('release ZIP members must be regular files')
        if type(info.file_size) is not int or info.file_size < 0:
            _fail('release ZIP member has an invalid expanded size')

        limit = (
            _MANIFEST_LIMIT
            if original_name == _MANIFEST_NAME
            else _IMAGE_LIMIT
        )
        if info.file_size > limit:
            _fail('{0} exceeds its expanded-size limit'.format(original_name))
        total_size += info.file_size
        if total_size > _EXPANDED_LIMIT:
            _fail('release ZIP exceeds its total expanded-size limit')
        by_name[original_name] = info

    if frozenset(by_name) != _MEMBER_NAMES:
        _fail('release ZIP members do not match the transport contract')
    return by_name


def _read_zip_member(archive, info, limit):
    chunks = []
    count = 0
    try:
        with archive.open(info, 'r') as source:
            while True:
                chunk = source.read(min(_READ_SIZE, limit - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                if count > limit:
                    _fail('{0} exceeds its streamed-size limit'.format(info.filename))
                chunks.append(chunk)
    except ReleaseValidationError:
        raise
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        NotImplementedError,
        OSError,
        EOFError,
        zlib.error,
    ) as error:
        _fail('could not read {0} safely'.format(info.filename), error)
    if count != info.file_size:
        _fail('{0} size differs from its ZIP declaration'.format(info.filename))
    return b''.join(chunks)


def _write_all(descriptor, payload):
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError('short filesystem write')
        remaining = remaining[written:]


def _create_file(directory_descriptor, name, created_files):
    flags = _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_descriptor)
    created_files[name] = os.fstat(descriptor)
    try:
        os.fchmod(descriptor, 0o600)
    except OSError:
        os.close(descriptor)
        raise
    return descriptor


def _copy_image_member(
    archive, info, directory_descriptor, created_files
):
    digest = hashlib.sha256()
    count = 0
    output = None
    try:
        output = _create_file(
            directory_descriptor, _IMAGE_NAME, created_files
        )
        with archive.open(info, 'r') as source:
            while True:
                chunk = source.read(min(_READ_SIZE, _IMAGE_LIMIT - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                if count > _IMAGE_LIMIT:
                    _fail('image.tar exceeds its streamed-size limit')
                digest.update(chunk)
                _write_all(output, chunk)
        written_stat = os.fstat(output)
    except ReleaseValidationError:
        raise
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        NotImplementedError,
        OSError,
        EOFError,
        zlib.error,
    ) as error:
        _fail('could not extract image.tar safely', error)
    finally:
        if output is not None:
            os.close(output)

    if count != info.file_size or written_stat.st_size != count:
        _fail('image.tar size differs from its ZIP declaration')
    return digest.hexdigest()


def _create_manifest_file(directory_descriptor, payload, created_files):
    output = None
    try:
        output = _create_file(
            directory_descriptor, _MANIFEST_NAME, created_files
        )
        _write_all(output, payload)
        written_stat = os.fstat(output)
    except OSError as error:
        _fail('could not extract release.json safely', error)
    finally:
        if output is not None:
            os.close(output)
    if written_stat.st_size != len(payload):
        _fail('release.json was not written completely')


def _cleanup_created(
    directory_descriptor,
    parent_descriptor,
    directory_name,
    directory_stat,
    created_files,
):
    if directory_descriptor is not None:
        for name, expected_stat in created_files.items():
            try:
                current = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
                if _same_object(current, expected_stat):
                    os.unlink(name, dir_fd=directory_descriptor)
            except OSError:
                pass

    if parent_descriptor is not None and directory_stat is not None:
        try:
            current = os.stat(
                directory_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISDIR(current.st_mode) and _same_object(
                current, directory_stat
            ):
                os.rmdir(directory_name, dir_fd=parent_descriptor)
        except OSError:
            pass


def _validated_manifest(payload, expected):
    try:
        raw_manifest = payload.decode('utf-8')
    except UnicodeDecodeError as error:
        _fail('release.json must be UTF-8 JSON', error)
    parsed = parse_manifest(raw_manifest)
    return validate_manifest(parsed, expected)


def unpack_release(zip_path, new_destination, expected):
    """Unpack a closed release ZIP into a new, safely opened directory."""

    parent_descriptor = None
    directory_descriptor = None
    directory_stat = None
    directory_name = None
    created_files = {}
    created_directory = False

    try:
        _require_expected(expected)
        try:
            archive = zipfile.ZipFile(zip_path, 'r')
        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError) as error:
            _fail('invalid release ZIP', error)

        with archive:
            members = _inspect_members(archive)
            manifest_payload = _read_zip_member(
                archive, members[_MANIFEST_NAME], _MANIFEST_LIMIT
            )
            manifest = _validated_manifest(manifest_payload, expected)

            parent_descriptor, directory_name = _open_parent(
                new_destination, 'new destination'
            )
            try:
                os.mkdir(
                    directory_name, 0o700, dir_fd=parent_descriptor
                )
                created_directory = True
                directory_stat = os.stat(
                    directory_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if not stat.S_ISDIR(directory_stat.st_mode):
                    _fail('new destination changed during creation')
                directory_descriptor = os.open(
                    directory_name,
                    _directory_flags(),
                    dir_fd=parent_descriptor,
                )
                opened_stat = os.fstat(directory_descriptor)
                if not _same_object(opened_stat, directory_stat):
                    _fail('new destination changed during creation')
                _require_trusted_directory(
                    directory_descriptor, 'new destination', False
                )
                directory_stat = opened_stat
                os.fchmod(directory_descriptor, 0o700)
            except OSError as error:
                _fail('new destination already exists or is unsafe', error)

            _create_manifest_file(
                directory_descriptor, manifest_payload, created_files
            )
            archive_digest = _copy_image_member(
                archive,
                members[_IMAGE_NAME],
                directory_descriptor,
                created_files,
            )
            if archive_digest != manifest['archive_sha256']:
                _fail('image.tar SHA-256 does not match release.json')

            for name, expected_stat in created_files.items():
                _assert_file_binding(
                    directory_descriptor, name, expected_stat
                )
            if frozenset(os.listdir(directory_descriptor)) != _MEMBER_NAMES:
                _fail('release directory changed during extraction')
            _assert_directory_binding(
                parent_descriptor, directory_name, directory_stat
            )
            return manifest
    except ReleaseValidationError:
        if created_directory:
            _cleanup_created(
                directory_descriptor,
                parent_descriptor,
                directory_name,
                directory_stat,
                created_files,
            )
        raise
    except (OSError, ValueError) as error:
        if created_directory:
            _cleanup_created(
                directory_descriptor,
                parent_descriptor,
                directory_name,
                directory_stat,
                created_files,
            )
        _fail('release transport failed safely', error)
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


def _read_open_file(descriptor, name, initial_stat, limit, digest=None):
    chunks = []
    count = 0
    while True:
        chunk = os.read(descriptor, min(_READ_SIZE, limit - count + 1))
        if not chunk:
            break
        count += len(chunk)
        if count > limit:
            _fail('{0} exceeds its size limit'.format(name))
        if digest is None:
            chunks.append(chunk)
        else:
            digest.update(chunk)

    final_stat = os.fstat(descriptor)
    unchanged = (
        _same_object(initial_stat, final_stat)
        and initial_stat.st_size == final_stat.st_size
        and initial_stat.st_mtime_ns == final_stat.st_mtime_ns
        and initial_stat.st_ctime_ns == final_stat.st_ctime_ns
    )
    if count != initial_stat.st_size or not unchanged:
        _fail('{0} changed during validation'.format(name))
    if digest is None:
        return b''.join(chunks)
    return digest.hexdigest()


def _open_regular_file(directory_descriptor, name, limit):
    descriptor = None
    try:
        descriptor = os.open(
            name, _file_flags(os.O_RDONLY), dir_fd=directory_descriptor
        )
        file_stat = os.fstat(descriptor)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        _fail('{0} is unavailable or unsafe'.format(name), error)
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > limit:
        os.close(descriptor)
        _fail('{0} is not a bounded regular file'.format(name))
    return descriptor, file_stat


def verify_archive(directory, expected):
    """Validate an unpacked manifest and hash its image TAR without extracting it."""

    parent_descriptor = None
    directory_descriptor = None
    try:
        _require_expected(expected)
        (
            parent_descriptor,
            directory_name,
            directory_descriptor,
            directory_stat,
        ) = _open_existing_directory(directory, 'release directory')
        if frozenset(os.listdir(directory_descriptor)) != _MEMBER_NAMES:
            _fail('release directory must contain exactly the transport files')

        manifest_descriptor, manifest_stat = _open_regular_file(
            directory_descriptor, _MANIFEST_NAME, _MANIFEST_LIMIT
        )
        try:
            manifest_payload = _read_open_file(
                manifest_descriptor,
                _MANIFEST_NAME,
                manifest_stat,
                _MANIFEST_LIMIT,
            )
        finally:
            os.close(manifest_descriptor)
        _assert_file_binding(
            directory_descriptor, _MANIFEST_NAME, manifest_stat
        )
        manifest = _validated_manifest(manifest_payload, expected)

        image_descriptor, image_stat = _open_regular_file(
            directory_descriptor, _IMAGE_NAME, _IMAGE_LIMIT
        )
        try:
            archive_digest = _read_open_file(
                image_descriptor,
                _IMAGE_NAME,
                image_stat,
                _IMAGE_LIMIT,
                hashlib.sha256(),
            )
        finally:
            os.close(image_descriptor)
        _assert_file_binding(directory_descriptor, _IMAGE_NAME, image_stat)
        if archive_digest != manifest['archive_sha256']:
            _fail('image.tar SHA-256 does not match release.json')

        if frozenset(os.listdir(directory_descriptor)) != _MEMBER_NAMES:
            _fail('release directory changed during validation')
        _assert_directory_binding(
            parent_descriptor, directory_name, directory_stat
        )
        return manifest
    except ReleaseValidationError:
        raise
    except OSError as error:
        _fail('release archive verification failed safely', error)
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)
