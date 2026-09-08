import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

import wordpress.release.transport as transport_boundary

try:
    from wordpress.release.manifest import ReleaseValidationError
    from wordpress.release.transport import unpack_release, verify_archive
except ModuleNotFoundError as import_error:
    ReleaseValidationError = None
    unpack_release = None
    verify_archive = None
    TRANSPORT_IMPORT_ERROR = import_error
else:
    TRANSPORT_IMPORT_ERROR = None


TAR_BYTES = b'literal docker image tar bytes\n'
TAR_SHA256 = 'a2a5177c769c3f3734b47a50f12c05bad6470664b9f2905e4942c8cb97f5c57c'


def literal_valid_manifest():
    return {
        'schema_version': 1,
        'repository': 'grzegorzrzeznikiewicz/company-site',
        'git_sha': '1234567890abcdef1234567890abcdef12345678',
        'workflow_id': 123,
        'workflow_path': '.github/workflows/wordpress-ci.yml',
        'run_id': 987654321,
        'run_attempt': 1,
        'event': 'push',
        'ref': 'refs/heads/main',
        'platform': 'linux/amd64',
        'image_id': (
            'sha256:'
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        ),
        'archive_sha256': TAR_SHA256,
        'packages': [
            {'name': 'wordpress', 'version': '7.1.0'},
            {'name': 'theme/gama-software', 'version': '0.4.1'},
            {'name': 'plugin/gama-contact', 'version': '0.3.2'},
            {'name': 'plugin/gama-seo', 'version': '0.1.0'},
            {'name': 'plugin/gama-security', 'version': '0.1.1'},
            {'name': 'plugin/gama-local-mailpit', 'version': '0.1.0'},
            {'name': 'plugin/gama-mail-transport', 'version': '0.1.0'},
        ],
        'evidence': [
            {
                'name': 'release-regression',
                'status': 'passed',
                'image_id': (
                    'sha256:'
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                ),
                'run_id': 987654321,
                'run_attempt': 1,
            },
            {
                'name': 'production-runtime',
                'status': 'passed',
                'image_id': (
                    'sha256:'
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                ),
                'run_id': 987654321,
                'run_attempt': 1,
            },
        ],
    }


def literal_expected_provenance():
    return {
        'repository': 'grzegorzrzeznikiewicz/company-site',
        'git_sha': '1234567890abcdef1234567890abcdef12345678',
        'workflow_id': 123,
        'workflow_path': '.github/workflows/wordpress-ci.yml',
        'run_id': 987654321,
        'run_attempt': 1,
        'event': 'push',
        'ref': 'refs/heads/main',
        'platform': 'linux/amd64',
    }


def manifest_bytes():
    return json.dumps(
        literal_valid_manifest(), separators=(',', ':')
    ).encode('utf-8')


def regular_info(name):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def make_zip(path, members):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', message='Duplicate name:', category=UserWarning
        )
        with zipfile.ZipFile(path, 'w') as archive:
            for member in members:
                if len(member) == 2:
                    name, payload = member
                    info = regular_info(name)
                else:
                    name, payload, info = member
                    self_name = info.orig_filename
                    if self_name != name:
                        raise AssertionError('fixture name does not match ZipInfo')
                archive.writestr(info, payload)
    return path


def make_valid_zip(path):
    return make_zip(
        path,
        (
            ('release.json', manifest_bytes()),
            ('image.tar', TAR_BYTES),
        ),
    )


def replace_member_name_bytes(path, old, new):
    if len(old) != len(new):
        raise AssertionError('replacement fixture names must have equal length')
    raw = path.read_bytes()
    if raw.count(old) != 2:
        raise AssertionError('expected one local and one central member name')
    path.write_bytes(raw.replace(old, new))


def set_central_uncompressed_size(path, member_name, size):
    raw = bytearray(path.read_bytes())
    end_offset = raw.rfind(b'PK\x05\x06')
    if end_offset < 0:
        raise AssertionError('fixture has no end-of-central-directory record')
    central_offset = struct.unpack_from('<I', raw, end_offset + 16)[0]
    offset = central_offset
    while offset < end_offset:
        if raw[offset : offset + 4] != b'PK\x01\x02':
            raise AssertionError('invalid central-directory fixture')
        name_length, extra_length, comment_length = struct.unpack_from(
            '<HHH', raw, offset + 28
        )
        name_start = offset + 46
        name = bytes(raw[name_start : name_start + name_length]).decode('utf-8')
        if name == member_name:
            if size <= 0xFFFFFFFE:
                struct.pack_into('<I', raw, offset + 24, size)
                path.write_bytes(raw)
                return

            zip64_extra = struct.pack('<HHQ', 0x0001, 8, size)
            insert_at = name_start + name_length + extra_length
            raw[insert_at:insert_at] = zip64_extra
            struct.pack_into('<I', raw, offset + 24, 0xFFFFFFFF)
            struct.pack_into('<H', raw, offset + 30, extra_length + len(zip64_extra))
            end_offset += len(zip64_extra)
            central_size = struct.unpack_from('<I', raw, end_offset + 12)[0]
            struct.pack_into(
                '<I', raw, end_offset + 12, central_size + len(zip64_extra)
            )
            path.write_bytes(raw)
            return
        offset += 46 + name_length + extra_length + comment_length
    raise AssertionError('fixture member not found')


def set_encrypted_flag(path, member_name):
    raw = bytearray(path.read_bytes())
    cursor = 0
    changed = 0
    encoded_name = member_name.encode('utf-8')
    while True:
        cursor = raw.find(encoded_name, cursor)
        if cursor < 0:
            break
        if raw[cursor - 30 : cursor - 26] == b'PK\x03\x04':
            flags_offset = cursor - 30 + 6
        elif raw[cursor - 46 : cursor - 42] == b'PK\x01\x02':
            flags_offset = cursor - 46 + 8
        else:
            cursor += len(encoded_name)
            continue
        flags = struct.unpack_from('<H', raw, flags_offset)[0]
        struct.pack_into('<H', raw, flags_offset, flags | 0x1)
        changed += 1
        cursor += len(encoded_name)
    if changed != 2:
        raise AssertionError('expected local and central encryption flags')
    path.write_bytes(raw)


class TransportAvailabilityTest(unittest.TestCase):
    def test_transport_boundary_is_available(self):
        self.assertIsNone(TRANSPORT_IMPORT_ERROR)
        self.assertTrue(callable(unpack_release))
        self.assertTrue(callable(verify_archive))


@unittest.skipIf(
    TRANSPORT_IMPORT_ERROR is not None,
    'transport boundary is not implemented yet',
)
class TransportTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        # macOS exposes /var through a symlink. Resolve only this trusted test
        # fixture so ancestor-rejection cases are testing paths we construct.
        self.root = Path(self.temporary_directory.name).resolve()
        self.archive = self.root / 'release.zip'
        self.destination = self.root / 'unpacked'
        self.outside = self.root / 'outside'
        self.expected = literal_expected_provenance()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_unpacks_exact_bytes_and_returns_bound_manifest(self):
        make_valid_zip(self.archive)

        previous_umask = os.umask(0)
        try:
            validated = unpack_release(self.archive, self.destination, self.expected)
        finally:
            os.umask(previous_umask)

        self.assertEqual(literal_valid_manifest(), validated)
        self.assertEqual(
            {'image.tar', 'release.json'},
            {entry.name for entry in self.destination.iterdir()},
        )
        self.assertEqual(
            TAR_BYTES, (self.destination / 'image.tar').read_bytes()
        )
        self.assertEqual(
            manifest_bytes(),
            (self.destination / 'release.json').read_bytes(),
        )
        self.assertEqual(
            0o600,
            stat.S_IMODE((self.destination / 'image.tar').stat().st_mode),
        )
        self.assertEqual(0o700, stat.S_IMODE(self.destination.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE((self.destination / 'release.json').stat().st_mode))
        self.assertEqual(
            literal_valid_manifest(),
            verify_archive(self.destination, self.expected),
        )

    def test_rejects_unsafe_member_names_without_writing_outside(self):
        for index, unsafe in enumerate(
            ('../outside', '/absolute', 'a/../image.tar', 'a\\image.tar')
        ):
            with self.subTest(unsafe=unsafe):
                archive = self.root / 'unsafe-{0}.zip'.format(index)
                make_zip(
                    archive,
                    (
                        ('release.json', manifest_bytes()),
                        (unsafe, TAR_BYTES),
                    ),
                )
                with self.assertRaises(ReleaseValidationError):
                    unpack_release(archive, self.destination, self.expected)
                self.assertFalse(self.outside.exists())
                self.assertFalse(self.destination.exists())

    def test_rejects_nul_truncated_member_name(self):
        make_zip(
            self.archive,
            (
                ('release.json', manifest_bytes()),
                ('imageXtar', TAR_BYTES),
            ),
        )
        replace_member_name_bytes(
            self.archive, b'imageXtar', b'image\x00tar'
        )

        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)

        self.assertFalse(self.destination.exists())

    def test_rejects_duplicate_missing_and_extra_members(self):
        cases = (
            (
                ('release.json', manifest_bytes()),
                ('image.tar', TAR_BYTES),
                ('image.tar', TAR_BYTES),
            ),
            (('release.json', manifest_bytes()),),
            (
                ('release.json', manifest_bytes()),
                ('image.tar', TAR_BYTES),
                ('extra', b'extra'),
            ),
        )
        for index, members in enumerate(cases):
            with self.subTest(case=index):
                archive = self.root / 'members-{0}.zip'.format(index)
                make_zip(archive, members)
                with self.assertRaises(ReleaseValidationError):
                    unpack_release(archive, self.destination, self.expected)
                self.assertFalse(self.destination.exists())

    def test_rejects_directory_symlink_special_and_encrypted_members(self):
        unsafe_modes = (
            stat.S_IFDIR | 0o700,
            stat.S_IFLNK | 0o777,
            stat.S_IFIFO | 0o600,
        )
        for index, mode in enumerate(unsafe_modes):
            with self.subTest(mode=mode):
                info = regular_info('image.tar')
                info.external_attr = mode << 16
                archive = self.root / 'mode-{0}.zip'.format(index)
                make_zip(
                    archive,
                    (
                        ('release.json', manifest_bytes()),
                        ('image.tar', TAR_BYTES, info),
                    ),
                )
                with self.assertRaises(ReleaseValidationError):
                    unpack_release(archive, self.destination, self.expected)
                self.assertFalse(self.destination.exists())

        make_valid_zip(self.archive)
        set_encrypted_flag(self.archive, 'image.tar')
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_rejects_corrupt_crc(self):
        image_info = regular_info('image.tar')
        image_info.compress_type = zipfile.ZIP_STORED
        make_zip(
            self.archive,
            (
                ('release.json', manifest_bytes()),
                ('image.tar', TAR_BYTES, image_info),
            ),
        )
        raw = self.archive.read_bytes()
        payload_offset = raw.find(TAR_BYTES)
        self.assertGreaterEqual(payload_offset, 0)
        damaged = bytearray(raw)
        damaged[payload_offset] ^= 0x01
        self.archive.write_bytes(damaged)

        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_rejects_stream_size_mismatch(self):
        make_valid_zip(self.archive)
        set_central_uncompressed_size(
            self.archive, 'image.tar', len(TAR_BYTES) - 1
        )
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_rejects_oversized_declared_members(self):
        make_zip(
            self.archive,
            (
                ('release.json', b'x' * (64 * 1024 + 1)),
                ('image.tar', TAR_BYTES),
            ),
        )
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

        make_valid_zip(self.archive)
        set_central_uncompressed_size(
            self.archive, 'image.tar', 4 * 1024 * 1024 * 1024 + 1
        )
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_rejects_invalid_manifest_and_changed_tar_bytes(self):
        make_zip(
            self.archive,
            (
                ('release.json', b'{"schema_version":1}'),
                ('image.tar', TAR_BYTES),
            ),
        )
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

        changed_tar = TAR_BYTES + b'tampered'
        make_zip(
            self.archive,
            (
                ('release.json', manifest_bytes()),
                ('image.tar', changed_tar),
            ),
        )
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_rejects_relative_preexisting_and_symlink_destinations(self):
        make_valid_zip(self.archive)

        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, Path('relative'), self.expected)

        self.destination.mkdir()
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertEqual([], list(self.destination.iterdir()))
        self.destination.rmdir()

        self.outside.mkdir()
        self.destination.symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual([], list(self.outside.iterdir()))

    def test_rejects_symlink_ancestor_without_resolving_it(self):
        make_valid_zip(self.archive)
        real_parent = self.root / 'real-parent'
        real_parent.mkdir()
        linked_parent = self.root / 'linked-parent'
        linked_parent.symlink_to(real_parent, target_is_directory=True)

        with self.assertRaises(ReleaseValidationError):
            unpack_release(
                self.archive, linked_parent / 'unpacked', self.expected
            )

        self.assertFalse((real_parent / 'unpacked').exists())

    def test_rejects_mutable_parent_before_destination_can_be_replaced(self):
        make_valid_zip(self.archive)
        mutable_parent = self.root / 'mutable-parent'
        mutable_parent.mkdir(mode=0o700)
        mutable_parent.chmod(0o777)
        destination = mutable_parent / 'unpacked'
        displaced = mutable_parent / 'displaced-created-directory'
        real_mkdir = os.mkdir

        def replace_new_destination(path, mode=0o777, *, dir_fd=None):
            result = real_mkdir(path, mode, dir_fd=dir_fd)
            if path == destination.name and dir_fd is not None:
                os.rename(
                    destination.name,
                    displaced.name,
                    src_dir_fd=dir_fd,
                    dst_dir_fd=dir_fd,
                )
                real_mkdir(destination.name, 0o777, dir_fd=dir_fd)
            return result

        with mock.patch.object(
            transport_boundary.os, 'mkdir', side_effect=replace_new_destination
        ):
            with self.assertRaises(ReleaseValidationError):
                unpack_release(self.archive, destination, self.expected)

        self.assertFalse(destination.exists())
        self.assertFalse(displaced.exists())

    def test_unpack_requires_complete_matching_expected_provenance(self):
        make_valid_zip(self.archive)
        incomplete = literal_expected_provenance()
        del incomplete['run_attempt']
        mismatch = literal_expected_provenance()
        mismatch['run_attempt'] = 2

        for index, expected in enumerate((None, incomplete, mismatch)):
            with self.subTest(case=index):
                destination = self.root / 'provenance-{0}'.format(index)
                with self.assertRaises(ReleaseValidationError):
                    unpack_release(self.archive, destination, expected)
                self.assertFalse(destination.exists())

    def test_verify_requires_complete_matching_expected_provenance(self):
        make_valid_zip(self.archive)
        unpack_release(self.archive, self.destination, self.expected)
        incomplete = literal_expected_provenance()
        del incomplete['run_attempt']
        mismatch = literal_expected_provenance()
        mismatch['run_attempt'] = 2

        for index, expected in enumerate((None, incomplete, mismatch)):
            with self.subTest(case=index):
                with self.assertRaises(ReleaseValidationError):
                    verify_archive(self.destination, expected)

    def test_rejects_invalid_zip_without_creating_destination(self):
        self.archive.write_bytes(b'not a ZIP archive')

        with self.assertRaises(ReleaseValidationError):
            unpack_release(self.archive, self.destination, self.expected)

        self.assertFalse(self.destination.exists())

    def test_verify_rejects_missing_extra_symlink_and_changed_files(self):
        for case in ('missing', 'extra', 'symlink', 'changed'):
            with self.subTest(case=case):
                destination = self.root / case
                archive = self.root / '{0}.zip'.format(case)
                make_valid_zip(archive)
                unpack_release(archive, destination, self.expected)
                image = destination / 'image.tar'
                if case == 'missing':
                    image.unlink()
                elif case == 'extra':
                    (destination / 'extra').write_bytes(b'extra')
                elif case == 'symlink':
                    image.unlink()
                    self.outside.write_bytes(b'outside')
                    image.symlink_to(self.outside)
                else:
                    image.write_bytes(TAR_BYTES + b'tampered')

                with self.assertRaises(ReleaseValidationError):
                    verify_archive(destination, self.expected)

                if case == 'symlink':
                    self.assertEqual(b'outside', self.outside.read_bytes())

    def test_verify_rejects_symlink_directory_or_ancestor(self):
        make_valid_zip(self.archive)
        real_destination = self.root / 'real-unpacked'
        unpack_release(self.archive, real_destination, self.expected)
        linked_destination = self.root / 'linked-unpacked'
        linked_destination.symlink_to(real_destination, target_is_directory=True)

        with self.assertRaises(ReleaseValidationError):
            verify_archive(linked_destination, self.expected)

        real_parent = self.root / 'verify-real-parent'
        real_parent.mkdir()
        moved_destination = real_parent / 'unpacked'
        os.rename(real_destination, moved_destination)
        linked_parent = self.root / 'verify-linked-parent'
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaises(ReleaseValidationError):
            verify_archive(linked_parent / 'unpacked', self.expected)


if __name__ == '__main__':
    unittest.main()
