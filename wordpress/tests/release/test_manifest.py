import json
import unittest


try:
    from wordpress.release.manifest import (
        ReleaseValidationError,
        artifact_name,
        parse_manifest,
        validate_manifest,
    )
except ModuleNotFoundError as import_error:
    ReleaseValidationError = None
    artifact_name = None
    parse_manifest = None
    validate_manifest = None
    MANIFEST_IMPORT_ERROR = import_error
else:
    MANIFEST_IMPORT_ERROR = None


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
        'archive_sha256': (
            'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        ),
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


class TrustedStringSubclass(str):
    pass


class EqualitySpoof:
    def __init__(self, trusted_value):
        self.trusted_value = trusted_value

    def __eq__(self, other):
        return other == self.trusted_value


@unittest.skipIf(
    MANIFEST_IMPORT_ERROR is not None,
    'manifest boundary is not implemented yet',
)
class ManifestValidationTest(unittest.TestCase):
    def test_accepts_valid_manifest_and_returns_detached_value(self):
        release = literal_valid_manifest()

        validated = validate_manifest(release)
        release['packages'][0]['version'] = 'tampered'
        release['evidence'][0]['status'] = 'failed'

        self.assertEqual('7.1.0', validated['packages'][0]['version'])
        self.assertEqual('passed', validated['evidence'][0]['status'])

    def test_binds_every_provenance_field_exactly(self):
        expected = literal_expected_provenance()
        self.assertEqual(
            literal_valid_manifest(),
            validate_manifest(literal_valid_manifest(), expected),
        )

        mismatches = {
            'repository': 'other-owner/company-site',
            'git_sha': '2234567890abcdef1234567890abcdef12345678',
            'workflow_id': 124,
            'workflow_path': '.github/workflows/other.yml',
            'run_id': 987654322,
            'run_attempt': 2,
            'event': 'pull_request',
            'ref': 'refs/heads/release',
            'platform': 'linux/arm64',
        }
        for field, mismatched_value in mismatches.items():
            with self.subTest(field=field):
                changed = literal_expected_provenance()
                changed[field] = mismatched_value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(literal_valid_manifest(), changed)

    def test_rejects_evidence_from_another_attempt(self):
        release = literal_valid_manifest()
        release['evidence'][1]['run_attempt'] = 2
        with self.assertRaises(ReleaseValidationError):
            validate_manifest(release)

    def test_rejects_evidence_from_another_run_or_image(self):
        mutations = (
            ('run_id', 987654322),
            (
                'image_id',
                'sha256:'
                'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
            ),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                release = literal_valid_manifest()
                release['evidence'][0][field] = value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_rejects_unknown_or_missing_manifest_controlled_fields(self):
        cases = []

        root_unknown = literal_valid_manifest()
        root_unknown['unexpected'] = 'value'
        cases.append(root_unknown)
        root_missing = literal_valid_manifest()
        del root_missing['archive_sha256']
        cases.append(root_missing)

        package_unknown = literal_valid_manifest()
        package_unknown['packages'][0]['unexpected'] = 'value'
        cases.append(package_unknown)
        package_missing = literal_valid_manifest()
        del package_missing['packages'][0]['version']
        cases.append(package_missing)

        evidence_unknown = literal_valid_manifest()
        evidence_unknown['evidence'][0]['unexpected'] = 'value'
        cases.append(evidence_unknown)
        evidence_missing = literal_valid_manifest()
        del evidence_missing['evidence'][0]['status']
        cases.append(evidence_missing)

        for index, release in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_rejects_booleans_zero_and_negative_values_as_ids(self):
        for field in ('workflow_id', 'run_id', 'run_attempt'):
            for value in (True, 0, -1):
                with self.subTest(field=field, value=value):
                    release = literal_valid_manifest()
                    release[field] = value
                    with self.assertRaises(ReleaseValidationError):
                        validate_manifest(release)

        for field in ('run_id', 'run_attempt'):
            for value in (True, 0, -1):
                with self.subTest(evidence_field=field, value=value):
                    release = literal_valid_manifest()
                    release['evidence'][0][field] = value
                    with self.assertRaises(ReleaseValidationError):
                        validate_manifest(release)

    def test_rejects_malformed_hashes(self):
        malformed = {
            'git_sha': (
                '1234567890ABCDEF1234567890ABCDEF12345678',
                '1234567890abcdef',
            ),
            'image_id': (
                'sha256:'
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                'sha256:aaaaaaaaaaaaaaaa',
            ),
            'archive_sha256': (
                'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB',
                'bbbbbbbbbbbbbbbb',
            ),
        }
        for field, values in malformed.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    release = literal_valid_manifest()
                    release[field] = value
                    with self.assertRaises(ReleaseValidationError):
                        validate_manifest(release)

    def test_rejects_unsafe_provenance_values_and_wrong_platform(self):
        unsafe_values = {
            'repository': (
                '../company-site',
                'owner/repository/extra',
                'owner/.',
            ),
            'workflow_path': (
                '../wordpress-ci.yml',
                '.github/workflows/../secrets.yml',
                '/.github/workflows/wordpress-ci.yml',
            ),
            'ref': (
                'main',
                'refs/heads/../main',
                'refs/heads/main.lock',
            ),
            'platform': ('linux/arm64',),
        }
        for field, values in unsafe_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    release = literal_valid_manifest()
                    release[field] = value
                    with self.assertRaises(ReleaseValidationError):
                        validate_manifest(release)

    def test_accepts_well_formed_pull_request_provenance(self):
        release = literal_valid_manifest()
        release['event'] = 'pull_request'
        release['ref'] = 'refs/pull/42/merge'
        self.assertEqual(release, validate_manifest(release))

    def test_rejects_non_exact_string_enum_values(self):
        cases = (
            ('event', TrustedStringSubclass('push')),
            ('event', EqualitySpoof('push')),
            ('platform', TrustedStringSubclass('linux/amd64')),
            ('platform', EqualitySpoof('linux/amd64')),
            ('status', TrustedStringSubclass('passed')),
            ('status', EqualitySpoof('passed')),
        )
        for field, value in cases:
            with self.subTest(field=field, value_type=type(value).__name__):
                release = literal_valid_manifest()
                if field == 'status':
                    release['evidence'][0][field] = value
                else:
                    release[field] = value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_rejects_non_exact_string_enum_values_in_expected_provenance(self):
        cases = (
            ('event', TrustedStringSubclass('push')),
            ('event', EqualitySpoof('push')),
            ('platform', TrustedStringSubclass('linux/amd64')),
            ('platform', EqualitySpoof('linux/amd64')),
        )
        for field, value in cases:
            with self.subTest(field=field, value_type=type(value).__name__):
                expected = literal_expected_provenance()
                expected[field] = value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(literal_valid_manifest(), expected)

    def test_returns_a_canonical_event_value(self):
        release = literal_valid_manifest()
        release['event'] = ''.join(('pu', 'sh'))

        validated = validate_manifest(release)

        self.assertEqual('push', validated['event'])
        self.assertIs(str, type(validated['event']))

    def test_rejects_incompatible_event_and_ref(self):
        pairs = (
            ('pull_request', 'refs/heads/main'),
            ('push', 'refs/pull/42/merge'),
            ('pull_request', 'refs/pull/0/merge'),
            ('pull_request', 'refs/pull/-1/merge'),
            ('workflow_dispatch', 'refs/heads/main'),
        )
        for event, ref in pairs:
            with self.subTest(event=event, ref=ref):
                release = literal_valid_manifest()
                release['event'] = event
                release['ref'] = ref
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_requires_exact_package_names_without_duplicates(self):
        duplicate = literal_valid_manifest()
        duplicate['packages'][-1]['name'] = 'wordpress'
        missing = literal_valid_manifest()
        missing['packages'].pop()
        extra = literal_valid_manifest()
        extra['packages'].append({'name': 'plugin/other', 'version': '1.0.0'})

        for release in (duplicate, missing, extra):
            with self.subTest(packages=release['packages']):
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_rejects_invalid_package_versions(self):
        for value in ('', '../1.0.0', True, 1):
            with self.subTest(value=value):
                release = literal_valid_manifest()
                release['packages'][0]['version'] = value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_requires_exact_evidence_names_without_duplicates(self):
        duplicate = literal_valid_manifest()
        duplicate['evidence'][1]['name'] = 'release-regression'
        missing = literal_valid_manifest()
        missing['evidence'].pop()
        extra = literal_valid_manifest()
        extra['evidence'].append(dict(extra['evidence'][0], name='other'))

        for release in (duplicate, missing, extra):
            with self.subTest(evidence=release['evidence']):
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(release)

    def test_rejects_failed_evidence(self):
        release = literal_valid_manifest()
        release['evidence'][0]['status'] = 'failed'
        with self.assertRaises(ReleaseValidationError):
            validate_manifest(release)

    def test_rejects_partial_or_extended_expected_provenance(self):
        missing = literal_expected_provenance()
        del missing['run_attempt']
        extended = literal_expected_provenance()
        extended['conclusion'] = 'success'

        for expected in (missing, extended):
            with self.subTest(expected=expected):
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(literal_valid_manifest(), expected)

    def test_rejects_invalid_expected_provenance_types(self):
        invalid_values = {
            'repository': 123,
            'git_sha': True,
            'workflow_id': True,
            'workflow_path': ['.github/workflows/wordpress-ci.yml'],
            'run_id': '987654321',
            'run_attempt': 1.0,
            'event': None,
            'ref': {'name': 'refs/heads/main'},
            'platform': False,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                expected = literal_expected_provenance()
                expected[field] = value
                with self.assertRaises(ReleaseValidationError):
                    validate_manifest(literal_valid_manifest(), expected)

    def test_returns_exact_artifact_name_after_validation(self):
        self.assertEqual(
            'wordpress-release-1234567890abcdef1234567890abcdef12345678-987654321-1',
            artifact_name(literal_valid_manifest()),
        )

        invalid = literal_valid_manifest()
        invalid['run_attempt'] = True
        with self.assertRaises(ReleaseValidationError):
            artifact_name(invalid)


class ManifestParsingTest(unittest.TestCase):
    def test_manifest_boundary_is_available(self):
        self.assertIsNone(
            MANIFEST_IMPORT_ERROR,
            'wordpress.release.manifest must provide the release boundary',
        )

    @unittest.skipIf(
        MANIFEST_IMPORT_ERROR is not None,
        'manifest boundary is not implemented yet',
    )
    def test_parses_valid_json_and_returns_detached_value(self):
        source = literal_valid_manifest()
        parsed = parse_manifest(json.dumps(source))
        source['packages'][0]['version'] = 'tampered'
        self.assertEqual('7.1.0', parsed['packages'][0]['version'])

    @unittest.skipIf(
        MANIFEST_IMPORT_ERROR is not None,
        'manifest boundary is not implemented yet',
    )
    def test_rejects_duplicate_json_keys_at_any_depth(self):
        duplicate_root = '{"schema_version":1,"schema_version":1}'
        duplicate_nested = (
            '{"schema_version":1,"nested":{"name":"first","name":"second"}}'
        )
        for raw in (duplicate_root, duplicate_nested):
            with self.subTest(raw=raw):
                with self.assertRaises(ReleaseValidationError):
                    parse_manifest(raw)

    @unittest.skipIf(
        MANIFEST_IMPORT_ERROR is not None,
        'manifest boundary is not implemented yet',
    )
    def test_rejects_non_finite_json_numbers(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value):
                raw = json.dumps(literal_valid_manifest()).replace('987654321', value, 1)
                with self.assertRaises(ReleaseValidationError):
                    parse_manifest(raw)

    @unittest.skipIf(
        MANIFEST_IMPORT_ERROR is not None,
        'manifest boundary is not implemented yet',
    )
    def test_rejects_invalid_json_and_non_object_json(self):
        for raw in ('{', '[]', 'null'):
            with self.subTest(raw=raw):
                with self.assertRaises(ReleaseValidationError):
                    parse_manifest(raw)


if __name__ == '__main__':
    unittest.main()
