"""Real read-only HTTP boundary; literals model documented GitHub REST fields."""

import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

try:
    from wordpress.release.github_source import GitHubAPI, resolve_source
except ModuleNotFoundError:
    GitHubAPI = resolve_source = None
from wordpress.release.manifest import ReleaseValidationError

REPO = 'grzegorzrzeznikiewicz/company-site'
SHA = '1234567890abcdef1234567890abcdef12345678'
ROOT = '/repos/' + REPO
WP = ['WordPress Source and Build', 'WordPress Package Lifecycle',
      'WordPress Runtime and Restore', 'WordPress Release Regression']
LEGACY = ['Backend Quality (Symfony)', 'Backend Tests', 'Frontend Quality',
          'End-to-End Tests']


def responses():
    repo = {'id': 1163583409, 'full_name': REPO, 'fork': False}
    run = {'id': 987654321, 'run_attempt': 1, 'workflow_id': 351411087,
           'path': '.github/workflows/wordpress-ci.yml', 'head_sha': SHA,
           'head_branch': 'main', 'event': 'push', 'status': 'completed',
           'conclusion': 'success', 'repository': repo, 'head_repository': repo}
    jobs = [{'id': i + 1, 'name': name, 'run_id': 987654321,
             'run_attempt': 1, 'head_sha': SHA, 'status': 'completed',
             'conclusion': 'success'} for i, name in enumerate(WP)]
    checks = [{'id': i + 100, 'name': name, 'head_sha': SHA,
               'status': 'completed', 'conclusion': 'success',
               'app': {'id': 15368},
               'details_url': 'https://github.com/' + REPO +
               '/actions/runs/' + ('987654321' if i < 4 else '987654322') + '/job/' + str(i + 1)}
              for i, name in enumerate(WP + LEGACY)]
    result = {
        ROOT: repo,
        ROOT + '/actions/workflows/351411087': {
            'id': 351411087, 'path': '.github/workflows/wordpress-ci.yml',
            'state': 'active'},
        ROOT + '/actions/runs/987654321': run,
        ROOT + '/actions/runs/987654321/attempts/1': copy.deepcopy(run),
        ROOT + '/actions/runs/987654321/attempts/1/jobs?per_page=100&page=1': {
            'total_count': 4, 'jobs': jobs},
        ROOT + '/branches/main/protection': {
            'required_pull_request_reviews': {
                'required_approving_review_count': 1,
                'dismiss_stale_reviews': True,
                'require_code_owner_reviews': False,
                'require_last_push_approval': False},
            'required_status_checks': {
                'strict': True, 'contexts': WP + LEGACY,
                'checks': [{'context': n, 'app_id': 15368} for n in WP + LEGACY]}},
        ROOT + '/rules/branches/main?per_page=100&page=1': [],
        ROOT + '/commits/' + SHA + '/pulls?per_page=100&page=1': [{'number': 12}],
        ROOT + '/pulls/12': {
            'number': 12, 'state': 'closed', 'merged': True, 'merge_commit_sha': SHA,
            'merged_at': '2026-09-07T12:00:00Z',
            'user': {'id': 111, 'login': 'author', 'type': 'User'},
            'base': {'ref': 'main', 'repo': repo},
            'head': {'sha': 'b' * 40, 'repo': repo}},
        ROOT + '/pulls/12/reviews?per_page=100&page=1': [{
            'id': 777, 'state': 'APPROVED', 'commit_id': 'b' * 40,
            'submitted_at': '2026-09-07T11:59:00Z',
            'user': {'id': 222, 'login': 'reviewer', 'type': 'User'}}],
        ROOT + '/collaborators/reviewer/permission': {
            'permission': 'write', 'user': {'id': 222, 'login': 'reviewer', 'type': 'User'}},
        ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1': {
            'total_count': 8, 'check_runs': checks},
        ROOT + '/commits/' + SHA + '/statuses?per_page=100&page=1': [],
        ROOT + '/actions/runs/987654321/artifacts?per_page=100&page=1': {
            'total_count': 1, 'artifacts': [{
                'id': 555, 'name': 'wordpress-release-' + SHA + '-987654321-1',
                'expired': False, 'size_in_bytes': 1234,
                'digest': 'sha256:' + 'c' * 64,
                'workflow_run': {'id': 987654321, 'repository_id': 1163583409,
                                 'head_repository_id': 1163583409,
                                 'head_branch': 'main', 'head_sha': SHA}}]},
    }
    for index, name in enumerate(WP + LEGACY):
        result[ROOT + '/actions/jobs/' + str(index + 1)] = {
            'id': index + 1, 'name': name, 'run_id': 987654321 if index < 4 else 987654322,
            'run_attempt': 1, 'head_sha': SHA, 'status': 'completed', 'conclusion': 'success'}
    result[ROOT + '/actions/workflows/ci.yml'] = {
        'id': 765, 'path': '.github/workflows/ci.yml', 'state': 'active'}
    result[ROOT + '/actions/runs/987654322'] = {
        **copy.deepcopy(run), 'id': 987654322, 'workflow_id': 765, 'path': '.github/workflows/ci.yml'}
    return result


def event():
    return {'action': 'completed', 'repository': responses()[ROOT],
            'workflow_run': copy.deepcopy(responses()[ROOT + '/actions/runs/987654321'])}


def solo_responses():
    """Owner merge plus a SHA-bound, owner-recorded independent AI report."""
    data = responses()
    owner = {'id': 50638878, 'login': 'grzegorzrzeznikiewicz', 'type': 'User'}
    data[ROOT + '/branches/main/protection']['required_pull_request_reviews'][
        'required_approving_review_count'] = 0
    data[ROOT + '/branches/main/protection']['enforce_admins'] = {'enabled': True}
    data[ROOT + '/pulls/12'].update(user=owner, merged_by=owner)
    data[ROOT + '/collaborators/grzegorzrzeznikiewicz/permission'] = {
        'permission': 'admin', 'user': owner}
    data[ROOT + '/pulls/12/reviews?per_page=100&page=1'] = [{
        'id': 778, 'state': 'COMMENTED', 'commit_id': 'b' * 40,
        'submitted_at': '2026-09-07T11:59:00Z', 'user': owner,
        'body': 'GAMA-SOLO-AI-REVIEW-V1\n' + json.dumps({
            'head_sha': 'b' * 40, 'result': 'approved',
            'report': 'Independent AI reviewer: exact PR head inspected; no blocking findings.'})}]
    return data


class HTTPFixture:
    def __init__(self, data=None):
        self.data = responses() if data is None else data
        self.requests = []
        self.request_headers = []

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.requests.append(self.path)
                fixture.request_headers.append(dict(self.headers))
                result = fixture.data.get(self.path)
                if result is None:
                    self.send_error(404)
                    return
                if isinstance(result, tuple):
                    status, headers, result = result
                else:
                    status, headers = 200, {}
                raw = result if isinstance(result, bytes) else json.dumps(result).encode()
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01})
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def api(self):
        return GitHubAPI('fixture-read-only', base_url=self.url)


class SourceTests(unittest.TestCase):
    def test_solo_owner_merge_with_exact_ai_report_allows_same_source(self):
        with HTTPFixture(solo_responses()) as http:
            result = resolve_source(event(), http.api(), 'wordpress')
        self.assertEqual(result['approval']['policy'], 'solo-owner-ai-v1')
        self.assertEqual(result['approval']['owner'], {
            'id': 50638878, 'login': 'grzegorzrzeznikiewicz'})
        self.assertEqual(result['approval']['review_id'], 778)
        self.assertEqual(result['approval']['head_sha'], 'b' * 40)
        self.assertEqual(result['artifact']['id'], 555)

    def test_solo_ruleset_zero_still_requires_actual_owner_merge(self):
        data = solo_responses()
        data[ROOT + '/branches/main/protection']['required_pull_request_reviews'] = None
        data[ROOT + '/rules/branches/main?per_page=100&page=1'] = [{
            'type': 'pull_request', 'parameters': {'required_approving_review_count': 0}}]
        with HTTPFixture(data) as http:
            self.assertEqual(resolve_source(event(), http.api(), 'wordpress')[
                'approval']['policy'], 'solo-owner-ai-v1')

    def test_solo_refuses_missing_pr_foreign_merge_identity_or_permissions(self):
        for change in ('no-pr', 'unmerged', 'wrong-sha', 'foreign-head', 'missing-merger',
                       'wrong-id', 'wrong-login', 'bot', 'permission', 'identity'):
            data = solo_responses()
            pr = data[ROOT + '/pulls/12']
            # Mutations must not alias the review author in this fixture.
            pr['merged_by'] = dict(pr['merged_by'])
            if change == 'no-pr': data[ROOT + '/commits/' + SHA + '/pulls?per_page=100&page=1'] = []
            elif change == 'unmerged': pr['merged'] = False
            elif change == 'wrong-sha': pr['merge_commit_sha'] = 'a' * 40
            elif change == 'foreign-head': pr['head']['repo'] = {'id': 1, 'full_name': 'fork/repo', 'fork': True}
            elif change == 'missing-merger': pr.pop('merged_by')
            elif change == 'wrong-id': pr['merged_by']['id'] = 1
            elif change == 'wrong-login': pr['merged_by']['login'] = 'other'
            elif change == 'bot': pr['merged_by']['type'] = 'Bot'
            elif change == 'permission': data[ROOT + '/collaborators/grzegorzrzeznikiewicz/permission']['permission'] = 'read'
            elif change == 'identity': data[ROOT + '/collaborators/grzegorzrzeznikiewicz/permission']['user'] = {'id': 1, 'login': 'grzegorzrzeznikiewicz', 'type': 'User'}
            with self.subTest(change=change), HTTPFixture(data) as http:
                with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')
                self.assertFalse(any('/artifacts' in path for path in http.requests))

    def test_solo_refuses_stale_missing_untrusted_or_unapproved_ai_report(self):
        for change in ('missing', 'stale-review', 'stale-report', 'foreign-author', 'after-merge',
                       'pending', 'dismissed', 'unapproved', 'empty', 'malformed', 'extra-field'):
            data = solo_responses()
            reviews = data[ROOT + '/pulls/12/reviews?per_page=100&page=1']
            review = reviews[0]
            report = json.loads(review['body'].split('\n', 1)[1])
            if change == 'missing': reviews.clear()
            elif change == 'stale-review': review['commit_id'] = 'a' * 40
            elif change == 'stale-report': report['head_sha'] = 'a' * 40
            elif change == 'foreign-author': review['user'] = {'id': 1, 'login': 'other', 'type': 'User'}
            elif change == 'after-merge': review['submitted_at'] = '2026-09-07T12:01:00Z'
            elif change == 'pending': review['state'] = 'PENDING'
            elif change == 'dismissed': review['state'] = 'DISMISSED'
            elif change == 'unapproved': report['result'] = 'changes-requested'
            elif change == 'empty': report['report'] = ' '
            elif change == 'extra-field': report['skip_checks'] = True
            review['body'] = 'GAMA-SOLO-AI-REVIEW-V1\n' + (json.dumps(report) if change != 'malformed' else '{')
            with self.subTest(change=change), HTTPFixture(data) as http:
                with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')
                self.assertFalse(any('/artifacts' in path for path in http.requests))

    def test_solo_latest_owner_review_can_withdraw_but_plain_comment_does_not(self):
        for state, body, allowed in [
            ('COMMENTED', 'A routine comment, not a new AI verdict.', True),
            ('CHANGES_REQUESTED', 'Needs fixes.', False),
            ('COMMENTED', 'GAMA-SOLO-AI-REVIEW-V1\n' + json.dumps({
                'head_sha': 'b' * 40, 'result': 'changes-requested', 'report': 'Blocking issue found.'}), False)]:
            data = solo_responses()
            reviews = data[ROOT + '/pulls/12/reviews?per_page=100&page=1']
            reviews.append({**reviews[0], 'id': 779, 'state': state, 'body': body,
                            'submitted_at': '2026-09-07T11:59:30Z'})
            with self.subTest(state=state, allowed=allowed), HTTPFixture(data) as http:
                if allowed: self.assertIsNotNone(resolve_source(event(), http.api(), 'wordpress'))
                else:
                    with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')

    def test_solo_new_review_supersedes_report_for_previous_head(self):
        data = solo_responses()
        reviews = data[ROOT + '/pulls/12/reviews?per_page=100&page=1']
        old = copy.deepcopy(reviews[0])
        old.update(id=777, commit_id='a' * 40, submitted_at='2026-09-07T11:58:00Z')
        old['body'] = old['body'].replace('b' * 40, 'a' * 40)
        reviews.insert(0, old)
        with HTTPFixture(data) as http:
            self.assertEqual(resolve_source(event(), http.api(), 'wordpress')[
                'approval']['review_id'], 778)

    def test_solo_uses_submission_time_not_review_creation_id(self):
        for latest_state, verdict, allowed in [('CHANGES_REQUESTED', 'approved', False),
                                               ('COMMENTED', 'changes-requested', False),
                                               ('COMMENTED', 'approved', True)]:
            data = solo_responses()
            reviews = data[ROOT + '/pulls/12/reviews?per_page=100&page=1']
            newer_submission = copy.deepcopy(reviews[0])
            newer_submission.update(id=777, state=latest_state,
                                    submitted_at='2026-09-07T11:59:30Z')
            newer_submission['body'] = newer_submission['body'].replace('"approved"', json.dumps(verdict))
            reviews.insert(0, newer_submission)
            if allowed: reviews[1]['state'] = 'CHANGES_REQUESTED'
            with self.subTest(state=latest_state, verdict=verdict), HTTPFixture(data) as http:
                if allowed:
                    self.assertEqual(resolve_source(event(), http.api(), 'wordpress')['approval']['review_id'], 777)
                else:
                    with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')
                    self.assertFalse(any('/artifacts' in path for path in http.requests))

    def test_solo_ambiguous_submission_time_or_unsubmitted_report_refuses(self):
        for state in ('CHANGES_REQUESTED', 'PENDING'):
            data = solo_responses()
            reviews = data[ROOT + '/pulls/12/reviews?per_page=100&page=1']
            other = {**reviews[0], 'id': 777, 'state': state}
            if state == 'PENDING': other['submitted_at'] = None
            reviews.insert(0, other)
            with self.subTest(state=state), HTTPFixture(data) as http:
                with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')

    def test_solo_never_overrides_stricter_reviews_or_missing_protections_checks(self):
        for change in ('no-pr-policy', 'no-checks', 'stricter-rule', 'failed-check', 'no-enforcement'):
            data = solo_responses()
            protection = data[ROOT + '/branches/main/protection']
            if change == 'no-pr-policy': protection['required_pull_request_reviews'] = None
            elif change == 'no-checks': protection['required_status_checks'] = None
            elif change == 'stricter-rule': data[ROOT + '/rules/branches/main?per_page=100&page=1'] = [
                {'type': 'pull_request', 'parameters': {'required_approving_review_count': 1}}]
            elif change == 'no-enforcement': protection['enforce_admins'] = {'enabled': False}
            else: data[ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1']['check_runs'][-1]['conclusion'] = 'failure'
            with self.subTest(change=change), HTTPFixture(data) as http:
                with self.assertRaises(ReleaseValidationError): resolve_source(event(), http.api(), 'wordpress')
                self.assertFalse(any('/artifacts' in path for path in http.requests))

    def test_terminal_full_page_and_bound_canonical_continuation(self):
        for canonical in (False, True):
            with self.subTest(canonical=canonical), HTTPFixture({}) as http:
                suffix = '/pulls/12/reviews?per_page=100&page='
                first = [{'id': i} for i in range(1, 101)]
                second = [{'id': i} for i in range(101, 201)]
                next_path = ('/repositories/1163583409' if canonical else ROOT) + suffix + '2'
                http.data.update({ROOT: responses()[ROOT], ROOT + suffix + '1':
                    (200, {'Link': '<' + http.url + next_path + '>; rel="next"'}, first),
                    next_path: second})
                self.assertEqual(first + second, http.api().pages(ROOT + '/pulls/12/reviews'))

    def test_canonical_continuation_refuses_wrong_repository_and_endpoint(self):
        for prefix in ('/repositories/1', '/repositories/1163583409/other'):
            with self.subTest(prefix=prefix), HTTPFixture({}) as http:
                http.data.update({ROOT: responses()[ROOT], ROOT + '/pulls?per_page=100&page=1':
                    (200, {'Link': '<' + http.url + prefix + '/pulls?per_page=100&page=2>; rel="next"'}, [{'id': 1}])})
                with self.assertRaises(ReleaseValidationError): http.api().pages(ROOT + '/pulls')

    def test_keyed_canonical_pages_require_stable_total_unique_ids_and_repository_identity(self):
        for mutation in ('none','duplicate','partial','foreign-repository'):
            with self.subTest(mutation=mutation), HTTPFixture({}) as http:
                suffix = '/actions/runs/987654321/jobs?per_page=100&page='
                next_path = '/repositories/1163583409'+suffix+'2'
                repo = copy.deepcopy(responses()[ROOT])
                if mutation == 'foreign-repository': repo['id'] = 1
                http.data.update({ROOT:repo,ROOT+suffix+'1':(200,
                    {'Link':'<'+http.url+next_path+'>; rel="next"'},
                    {'total_count':2,'jobs':[{'id':1}]}),
                    next_path:{'total_count':2,'jobs':[] if mutation=='partial' else [{'id':1 if mutation=='duplicate' else 2}]}})
                if mutation == 'none':
                    self.assertEqual([{'id':1},{'id':2}],http.api().pages(ROOT+'/actions/runs/987654321/jobs','jobs'))
                else:
                    with self.assertRaises(ReleaseValidationError): http.api().pages(ROOT+'/actions/runs/987654321/jobs','jobs')

    def test_artifact_real_redirect_strips_credential_and_refuses_untrusted_storage(self):
        import hashlib
        import tempfile
        from pathlib import Path
        import urllib.request
        path = ROOT + '/actions/artifacts/555/zip'
        payload = b'bounded artifact fixture'
        artifact = {'id':555, 'size_in_bytes':len(payload), 'digest':'sha256:'+hashlib.sha256(payload).hexdigest()}
        for location, allowed in [('https://fixture.blob.core.windows.net/archive?sig=fixture', True),
                                  ('https://fixture.actions.githubusercontent.com/archive', True),
                                  ('https://evil.example/archive', False),
                                  ('https://fixture.blob.core.windows.net.evil.test/archive', False),
                                  ('http://fixture.blob.core.windows.net/archive', False),
                                  ('https://user@fixture.blob.core.windows.net/archive', False),
                                  ('https://fixture.blob.core.windows.net:444/archive', False),
                                  ('https://fixture.blob.core.windows.net/archive#fragment', False)]:
            with self.subTest(location=location), HTTPFixture({path:(302, {'Location':location}, b''), '/storage':payload}) as http, tempfile.TemporaryDirectory() as tmp:
                api = http.api()
                real_open = api.opener.open
                storage_headers = []
                # Only replace external HTTPS transport, after production redirect validation.
                def open_request(req, **kwargs):
                    if req.full_url.startswith(http.url): return real_open(req, **kwargs)
                    storage_headers.append(dict(req.header_items()))
                    return real_open(urllib.request.Request(http.url+'/storage', headers=dict(req.header_items())), **kwargs)
                api.opener.open = open_request
                destination = Path(tmp)/'archive.zip'
                if allowed:
                    api.download(artifact, destination)
                    self.assertEqual(payload, destination.read_bytes())
                    self.assertEqual([{}], storage_headers)
                    self.assertNotIn('Authorization', http.request_headers[-1])
                    self.assertEqual('Bearer fixture-read-only', http.request_headers[0]['Authorization'])
                else:
                    with self.assertRaises(ReleaseValidationError): api.download(artifact, destination)
                    self.assertEqual([], storage_headers)
                    self.assertFalse(destination.exists())

    def setUp(self):
        self.assertIsNotNone(resolve_source, 'production provenance validator is missing')

    def test_exact_source_returns_manifest_provenance_and_immutable_artifact(self):
        with HTTPFixture() as fixture:
            result = resolve_source(event(), fixture.api(), 'wordpress')
        self.assertEqual(result['provenance']['run_attempt'], 1)
        self.assertEqual(result['provenance']['git_sha'], SHA)
        self.assertEqual(result['artifact']['id'], 555)
        self.assertEqual(result['approval']['pull_request'], 12)

    def test_standard_disabled_modes_perform_no_http_reads(self):
        with HTTPFixture({}) as fixture:
            for mode in ('off', 'legacy', '', 'WordPress', None):
                self.assertIsNone(resolve_source({}, fixture.api(), mode))
            self.assertEqual(fixture.requests, [])

    def test_untrusted_event_rejected_before_artifact_access(self):
        for key, value in [('head_sha', 'a' * 40), ('event', 'pull_request'),
                           ('head_branch', 'other'), ('conclusion', 'failure'),
                           ('run_attempt', 2), ('workflow_id', 42),
                           ('repository', {'id': 99, 'full_name': REPO}),
                           ('head_repository', {'id': 99, 'full_name': 'fork/repo'})]:
            with self.subTest(key=key), HTTPFixture() as fixture:
                payload = event()
                payload['workflow_run'][key] = value
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(payload, fixture.api(), 'wordpress')
                self.assertFalse(any('/artifacts' in p for p in fixture.requests))

    def test_failed_mixed_attempt_and_missing_jobs_fail_closed(self):
        path = ROOT + '/actions/runs/987654321/attempts/1/jobs?per_page=100&page=1'
        for key, value in [('conclusion', 'skipped'), ('run_attempt', 2),
                           ('head_sha', 'a' * 40), ('name', 'unrelated')]:
            data = responses()
            data[path]['jobs'][0][key] = value
            with self.subTest(key=key), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(event(), fixture.api(), 'wordpress')
                self.assertFalse(any('/artifacts' in p for p in fixture.requests))

    def test_approval_must_be_current_human_non_author_eligible_and_before_merge(self):
        path = ROOT + '/pulls/12/reviews?per_page=100&page=1'
        for key, value in [('state', 'DISMISSED'), ('commit_id', 'a' * 40),
                           ('submitted_at', '2026-09-07T12:01:00Z'),
                           ('user', {'id': 111, 'login': 'author', 'type': 'User'}),
                           ('user', {'id': 222, 'login': 'reviewer', 'type': 'Bot'})]:
            data = responses()
            data[path][0][key] = value
            with self.subTest(key=key), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(event(), fixture.api(), 'wordpress')

    def test_comments_do_not_withdraw_approval_but_changes_requested_do(self):
        path = ROOT + '/pulls/12/reviews?per_page=100&page=1'
        for state, succeeds in [('COMMENTED', True), ('CHANGES_REQUESTED', False)]:
            data = responses()
            newer = copy.deepcopy(data[path][0])
            newer.update(id=778, state=state, submitted_at='2026-09-07T11:59:30Z')
            data[path].append(newer)
            with self.subTest(state=state), HTTPFixture(data) as fixture:
                if succeeds:
                    self.assertIsNotNone(resolve_source(event(), fixture.api(), 'wordpress'))
                else:
                    with self.assertRaises(ReleaseValidationError):
                        resolve_source(event(), fixture.api(), 'wordpress')

    def test_unprotected_branch_and_higher_approval_count_refuse(self):
        path = ROOT + '/branches/main/protection'
        for mutation in ('empty', 'two', 'read_only', 'pending_legacy', 'wrong_main_sha'):
            data = responses()
            if mutation == 'empty':
                data[path] = {}
            elif mutation == 'two':
                data[path]['required_pull_request_reviews']['required_approving_review_count'] = 2
            elif mutation == 'read_only':
                data[ROOT + '/collaborators/reviewer/permission']['permission'] = 'read'
            else:
                checks = data[ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1']['check_runs']
                checks[-1]['conclusion' if mutation == 'pending_legacy' else 'head_sha'] = None if mutation == 'pending_legacy' else 'a' * 40
            with self.subTest(mutation=mutation), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(event(), fixture.api(), 'wordpress')

    def test_partial_pagination_and_api_redirect_refuse(self):
        path = ROOT + '/actions/runs/987654321/attempts/1/jobs?per_page=100&page=1'
        for mutation in ('partial', 'redirect', 'foreign_next'):
            data = responses()
            if mutation == 'partial':
                data[path]['total_count'] = 5
            elif mutation == 'redirect':
                data[path] = (302, {'Location': 'https://evil.example/'}, {})
            else:
                data[path] = (200, {'Link': '<https://evil.example/>; rel="next"'}, data[path])
            with self.subTest(mutation=mutation), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(event(), fixture.api(), 'wordpress')

    def test_successful_check_from_superseded_attempt_refuses(self):
        data = responses()
        data[ROOT + '/actions/runs/987654321']['run_attempt'] = 2
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError):
                resolve_source(event(), fixture.api(), 'wordpress')

    def test_current_attempt_of_legacy_check_is_verified(self):
        data = responses()
        check_path = ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1'
        data[check_path]['check_runs'][-1]['details_url'] = (
            'https://github.com/' + REPO + '/actions/runs/99/job/88')
        data[ROOT + '/actions/runs/99'] = {
            **data[ROOT + '/actions/runs/987654321'], 'id': 99, 'run_attempt': 2}
        data[ROOT + '/actions/jobs/88'] = {
            'id': 88, 'run_id': 99, 'run_attempt': 1, 'head_sha': SHA,
            'name': 'End-to-End Tests', 'status': 'completed', 'conclusion': 'success'}
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError):
                resolve_source(event(), fixture.api(), 'wordpress')

    def test_effective_rules_cannot_silently_drop_code_owner_or_team_requirements(self):
        for key, value in [('require_code_owner_review', True),
                           ('required_reviewers', [{'minimum_approvals': 1, 'reviewer': {'id': 7, 'type': 'Team'},
                                                    'file_patterns': ['*']}])]:
            data = responses()
            data[ROOT + '/rules/branches/main?per_page=100&page=1'] = [{
                'type': 'pull_request', 'ruleset_id': 66, 'ruleset_source_type': 'Repository',
                'ruleset_source': REPO, 'parameters': {
                    'required_approving_review_count': 1, 'dismiss_stale_reviews_on_push': True,
                    'require_last_push_approval': False, 'require_code_owner_review': False,
                    'required_review_thread_resolution': False, key: value}}]
            with self.subTest(key=key), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(event(), fixture.api(), 'wordpress')

    def test_pending_exact_main_legacy_check_has_distinct_retryable_refusal(self):
        data = responses()
        check = data[ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1']['check_runs'][-1]
        check.update(status='in_progress', conclusion=None)
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError) as refusal:
                resolve_source(event(), fixture.api(), 'wordpress')
            self.assertEqual(type(refusal.exception).__name__, 'SourcePendingError')
            self.assertFalse(any('/artifacts' in path for path in fixture.requests))

    def test_configured_commit_status_uses_exact_sha_endpoint_and_latest_decision(self):
        for state, succeeds in [('success', True), ('failure', False)]:
            data = responses()
            data[ROOT + '/branches/main/protection']['required_status_checks']['contexts'].append('external-audit')
            data[ROOT + '/commits/' + SHA + '/statuses?per_page=100&page=1'] = [{
                'id': 901, 'node_id': 'fixture-status', 'state': state,
                'context': 'external-audit', 'description': 'Completed audit',
                'target_url': 'https://example.com/audit/901',
                'url': 'https://api.github.com' + ROOT + '/statuses/' + SHA,
                'created_at': '2026-09-07T11:59:00Z', 'updated_at': '2026-09-07T11:59:00Z',
                'avatar_url': None, 'creator': {'id': 222, 'login': 'reviewer', 'type': 'User'}}]
            with self.subTest(state=state), HTTPFixture(data) as fixture:
                if succeeds:
                    self.assertIsNotNone(resolve_source(event(), fixture.api(), 'wordpress'))
                else:
                    with self.assertRaises(ReleaseValidationError):
                        resolve_source(event(), fixture.api(), 'wordpress')

    def test_other_workflow_cannot_impersonate_mandatory_legacy_job_names(self):
        data = responses()
        data[ROOT + '/actions/runs/987654322'].update(
            workflow_id=42, path='.github/workflows/imposter.yml')
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError):
                resolve_source(event(), fixture.api(), 'wordpress')
            self.assertFalse(any('/artifacts' in path for path in fixture.requests))

    def test_required_check_and_same_name_commit_status_must_both_succeed(self):
        for state in ('failure', 'pending', 'success'):
            data = responses()
            data[ROOT + '/branches/main/protection']['required_status_checks']['contexts'].append('external-audit')
            checks = data[ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1']
            checks['check_runs'].append({
                'id': 800, 'name': 'external-audit', 'head_sha': SHA,
                'status': 'completed', 'conclusion': 'success', 'app': {'id': 44}})
            checks['total_count'] = 9
            data[ROOT + '/commits/' + SHA + '/statuses?per_page=100&page=1'] = [{
                'id': 901, 'node_id': 'fixture-status', 'state': state,
                'context': 'external-audit', 'description': 'Audit result',
                'target_url': 'https://example.com/audit/901',
                'url': 'https://api.github.com' + ROOT + '/statuses/' + SHA,
                'created_at': '2026-09-07T11:59:00Z', 'updated_at': '2026-09-07T11:59:00Z',
                'avatar_url': None, 'creator': {'id': 222, 'login': 'reviewer', 'type': 'User'}}]
            with self.subTest(state=state), HTTPFixture(data) as fixture:
                if state == 'success':
                    self.assertEqual(resolve_source(event(), fixture.api(), 'wordpress')['artifact']['id'], 555)
                else:
                    with self.assertRaises(ReleaseValidationError) as refusal:
                        resolve_source(event(), fixture.api(), 'wordpress')
                    self.assertEqual(type(refusal.exception).__name__,
                                     'SourcePendingError' if state == 'pending' else 'ReleaseValidationError')
                    self.assertFalse(any('/artifacts' in path for path in fixture.requests))

    def test_same_name_status_cannot_inherit_check_run_app_provenance(self):
        data = responses()
        data[ROOT + '/branches/main/protection']['required_status_checks']['checks'].append(
            {'context': 'external-audit', 'app_id': 44})
        checks = data[ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100&page=1']
        checks['check_runs'].append({
            'id': 800, 'name': 'external-audit', 'head_sha': SHA,
            'status': 'completed', 'conclusion': 'success', 'app': {'id': 44}})
        checks['total_count'] = 9
        data[ROOT + '/commits/' + SHA + '/statuses?per_page=100&page=1'] = [{
            'id': 901, 'node_id': 'fixture-status', 'state': 'success',
            'context': 'external-audit', 'description': 'Audit result',
            'target_url': 'https://example.com/audit/901',
            'url': 'https://api.github.com' + ROOT + '/statuses/' + SHA,
            'created_at': '2026-09-07T11:59:00Z', 'updated_at': '2026-09-07T11:59:00Z',
            'avatar_url': None, 'creator': {'id': 222, 'login': 'reviewer', 'type': 'User'}}]
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError):
                resolve_source(event(), fixture.api(), 'wordpress')
            self.assertFalse(any('/artifacts' in path for path in fixture.requests))


def cutover_fixture():
    data = responses()
    repo = data[ROOT]
    owner = {'id': 222, 'login': 'reviewer', 'type': 'User'}
    authorization = {
        'authorization_id': 'cutover-20260907', 'promotion_run_id': 900,
        'promotion_run_attempt': 1, 'git_sha': SHA, 'source_run_id': 987654321,
        'source_run_attempt': 1, 'artifact_id': 555, 'artifact_digest': 'sha256:' + 'c' * 64,
        'operators': [owner], 'window_start': '2020-01-01T00:00:00Z',
        'window_end': '2099-01-01T00:00:00Z'}
    data[ROOT + '/actions/workflows/wordpress-production.yml'] = {
        'id': 800, 'path': '.github/workflows/wordpress-production.yml', 'state': 'active'}
    data[ROOT + '/actions/runs/900'] = {
        'id': 900, 'run_attempt': 1, 'workflow_id': 800,
        'path': '.github/workflows/wordpress-production.yml', 'event': 'workflow_dispatch',
        'head_branch': 'main', 'head_sha': SHA, 'repository': repo, 'head_repository': repo,
        'created_at': '2026-09-07T12:00:00Z', 'actor': owner, 'triggering_actor': owner,
        'status': 'in_progress', 'conclusion': None}
    data[ROOT + '/environments/wordpress-production-cutover'] = {
        'id': 333, 'name': 'wordpress-production-cutover',
        'protection_rules': [{'id': 444, 'type': 'required_reviewers',
                              'prevent_self_review': False,
                              'reviewers': [{'type': 'User', 'reviewer': owner}]}]}
    data[ROOT + '/actions/runs/900/approvals'] = [{
        'environments': [{'id': 333, 'name': 'wordpress-production-cutover'}],
        'state': 'approved', 'user': owner,
        'comment': json.dumps(authorization, sort_keys=True, separators=(',', ':'))}]
    payload = {'repository': repo, 'ref': 'refs/heads/main',
               'promotion_run_id': 900, 'promotion_run_attempt': 1,
               'authorization': authorization, 'source_event': event()}
    return data, payload


class CutoverTests(unittest.TestCase):
    def test_operator_human_type_must_match_fetched_identity(self):
        data, payload = cutover_fixture()
        data[ROOT + '/collaborators/reviewer/permission']['user']['type'] = 'Bot'
        with HTTPFixture(data) as fixture:
            with self.assertRaises(ReleaseValidationError):
                resolve_source(payload, fixture.api(), 'off', operation='first-cutover')

    def test_configured_owner_approval_binds_explicit_artifact_and_operators(self):
        self.assertIsNotNone(resolve_source, 'provenance validator missing')
        data, payload = cutover_fixture()
        with HTTPFixture(data) as fixture:
            result = resolve_source(payload, fixture.api(), 'off', operation='first-cutover')
        self.assertEqual(result['authorization']['artifact_id'], 555)
        self.assertEqual(result['operation'], 'first-cutover')

    def test_gate_history_cannot_be_reused_or_self_asserted(self):
        for mutation in ('rerun', 'empty_history', 'rejected', 'wrong_digest',
                         'unconfigured', 'self_review', 'expired', 'wrong_workflow'):
            data, payload = cutover_fixture()
            if mutation == 'rerun':
                data[ROOT + '/actions/runs/900']['run_attempt'] = 2
            elif mutation == 'empty_history':
                data[ROOT + '/actions/runs/900/approvals'] = []
            elif mutation == 'rejected':
                data[ROOT + '/actions/runs/900/approvals'][0]['state'] = 'rejected'
            elif mutation == 'wrong_digest':
                payload['authorization']['artifact_digest'] = 'sha256:' + 'd' * 64
            elif mutation == 'unconfigured':
                data[ROOT + '/environments/wordpress-production-cutover']['protection_rules'] = []
            elif mutation == 'self_review':
                data[ROOT + '/environments/wordpress-production-cutover']['protection_rules'][0]['prevent_self_review'] = True
            elif mutation == 'expired':
                payload['authorization']['window_end'] = '2021-01-01T00:00:00Z'
            else:
                data[ROOT + '/actions/runs/900']['workflow_id'] = 42
            with self.subTest(mutation=mutation), HTTPFixture(data) as fixture:
                with self.assertRaises(ReleaseValidationError):
                    resolve_source(payload, fixture.api(), 'off', operation='first-cutover')


if __name__ == '__main__':
    unittest.main()
