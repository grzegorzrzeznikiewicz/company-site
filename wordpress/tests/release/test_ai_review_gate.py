"""AI review verdict to owner solo-report bridge; literals model GitHub REST fields."""

import copy
from datetime import datetime, timezone
import io
import unittest
import unittest.mock

from wordpress.release import ai_review_gate as gate
from wordpress.release.github_source import SOLO_REVIEW_PREFIX, json_object

SHA = '1234567890abcdef1234567890abcdef12345678'
OLD = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
ROOT = '/repos/grzegorzrzeznikiewicz/company-site'
RUN_URL = 'https://github.com/grzegorzrzeznikiewicz/company-site/actions/runs/42'
REPO = {'id': 1163583409, 'full_name': 'grzegorzrzeznikiewicz/company-site', 'fork': False}
OWNER = {'id': 50638878, 'login': 'grzegorzrzeznikiewicz', 'type': 'User'}
BOT = {'id': 209825114, 'login': 'claude[bot]', 'type': 'Bot'}
STARTED = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)
GATES = ['WordPress Source and Build', 'WordPress Package Lifecycle',
         'WordPress Runtime and Restore', 'WordPress Release Regression']


def check(name, status='completed', conclusion='success', sha=SHA, app='github-actions'):
    return {'name': name, 'status': status, 'conclusion': conclusion, 'head_sha': sha,
            'app': {'slug': app}}


def review(review_id, state, when, commit=SHA, user=BOT, body='Verdict and findings.'):
    return {'id': review_id, 'state': state, 'submitted_at': when, 'commit_id': commit,
            'user': user, 'body': body,
            'html_url': 'https://github.com/x/pull/7#pullrequestreview-' + str(review_id)}


class FakeAPI:
    def __init__(self, reviews, pr=None):
        self.pr = pr or {'number': 7, 'state': 'open', 'draft': False, 'user': OWNER,
                         'base': {'ref': 'main', 'repo': REPO},
                         'head': {'sha': SHA, 'repo': REPO}}
        self.reviews = reviews
        self.posted = []
        self.merges = []
        self.check_polls = [[check(name) for name in GATES]]

    def get(self, path):
        if path.startswith(ROOT + '/commits/'):
            assert path == ROOT + '/commits/' + SHA + '/check-runs?filter=latest&per_page=100', path
            runs = self.check_polls[0] if len(self.check_polls) == 1 else self.check_polls.pop(0)
            return {'check_runs': copy.deepcopy(runs)}
        assert path == ROOT + '/pulls/7', path
        return copy.deepcopy(self.pr)

    def pages(self, path):
        assert path == ROOT + '/pulls/7/reviews', path
        return copy.deepcopy(self.reviews)

    def post(self, path, payload):
        assert path == ROOT + '/pulls/7/reviews', path
        self.posted.append(payload)
        return {'id': 900, 'state': 'COMMENTED', 'commit_id': payload['commit_id'], 'user': OWNER}

    def put(self, path, payload):
        assert path == ROOT + '/pulls/7/merge', path
        self.merges.append(payload)
        return {'merged': True, 'sha': 'f' * 40}


class AIReviewGateTest(unittest.TestCase):
    def report(self, api):
        self.assertEqual(len(api.posted), 1)
        payload = api.posted[0]
        self.assertEqual((payload['event'], payload['commit_id']), ('COMMENT', SHA))
        self.assertTrue(payload['body'].startswith(SOLO_REVIEW_PREFIX))
        parsed = json_object(payload['body'][len(SOLO_REVIEW_PREFIX):])
        self.assertEqual(frozenset(parsed), {'head_sha', 'result', 'report'})
        self.assertEqual(parsed['head_sha'], SHA)
        return parsed

    def test_latest_bot_approval_on_exact_head_is_recorded_as_owner_report(self):
        api = FakeAPI([review(1, 'CHANGES_REQUESTED', '2026-11-26T10:00:00Z'),
                       review(2, 'APPROVED', '2026-11-26T11:00:00Z'),
                       review(3, 'COMMENTED', '2026-11-26T12:00:00Z')])
        self.assertEqual(gate.run(api, 7, SHA, RUN_URL, STARTED), 'approved')
        parsed = self.report(api)
        self.assertEqual(parsed['result'], 'approved')
        self.assertIn('Verdict and findings.', parsed['report'])
        self.assertIn('review 2', parsed['report'])

    def test_blocking_verdict_is_recorded_and_never_approves(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z'),
                       review(2, 'CHANGES_REQUESTED', '2026-11-26T11:00:00Z')])
        self.assertEqual(gate.run(api, 7, SHA, RUN_URL, STARTED), 'changes-requested')
        self.assertEqual(self.report(api)['result'], 'changes-requested')

    def test_untrusted_or_stale_verdicts_record_nothing(self):
        cases = {
            'earlier run': [review(1, 'APPROVED', '2026-11-26T08:59:59Z')],
            'stale head': [review(1, 'APPROVED', '2026-11-26T10:00:00Z', commit=OLD)],
            'human imitation': [review(1, 'APPROVED', '2026-11-26T10:00:00Z',
                                       user={'id': 5, 'login': 'claude-bot', 'type': 'User'})],
            'other bot': [review(1, 'APPROVED', '2026-11-26T10:00:00Z',
                                 user={'id': 6, 'login': 'github-actions[bot]', 'type': 'Bot'})],
            'pending': [review(1, 'PENDING', '2026-11-26T10:00:00Z')],
            'dismissed': [review(1, 'DISMISSED', '2026-11-26T10:00:00Z')],
            'ambiguous': [review(1, 'APPROVED', '2026-11-26T10:00:00Z'),
                          review(2, 'CHANGES_REQUESTED', '2026-11-26T10:00:00Z')],
            'empty report': [review(1, 'APPROVED', '2026-11-26T10:00:00Z', body='  ')],
        }
        for name, reviews in cases.items():
            with self.subTest(name):
                api = FakeAPI(reviews)
                with self.assertRaises(gate.GateError):
                    gate.run(api, 7, SHA, RUN_URL, STARTED)
                self.assertEqual(api.posted, [])

    def test_pr_shape_is_pinned(self):
        mutations = {
            'moved head': lambda pr: pr['head'].update(sha=OLD),
            'draft': lambda pr: pr.update(draft=True),
            'closed': lambda pr: pr.update(state='closed'),
            'other base': lambda pr: pr['base'].update(ref='develop'),
            'fork head': lambda pr: pr['head'].update(repo=dict(REPO, id=1, fork=True)),
            'other author': lambda pr: pr.update(user={'id': 1, 'login': 'x', 'type': 'User'}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                mutate(api.pr)
                with self.assertRaises(gate.GateError):
                    gate.run(api, 7, SHA, RUN_URL, STARTED)
                self.assertEqual(api.posted, [])

    def test_oversized_report_is_truncated_within_production_limit(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z', body='ą"' * 60000)])
        self.assertEqual(gate.run(api, 7, SHA, RUN_URL, STARTED), 'approved')
        parsed = self.report(api)
        self.assertLessEqual(len(api.posted[0]['body'].encode('utf-8')), 64 * 1024)
        self.assertIn('[report truncated', parsed['report'])

    def env(self, **extra):
        return dict({'PR_NUMBER': '7', 'EXPECTED_HEAD_SHA': SHA, 'REVIEW_RUN_URL': RUN_URL,
                     'REVIEW_STARTED_AT': '2026-11-26T09:00:00Z'}, **extra)

    def test_main_merges_approved_head_pinned_to_sha_after_gates_pass(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
        api.check_polls = [[check(GATES[0], status='in_progress', conclusion=None)],
                           [check(name) for name in GATES]]
        sleeps = []
        out = io.StringIO()
        self.assertEqual(gate.main(self.env(), out, api, sleep=sleeps.append), 0)
        self.assertEqual(out.getvalue(), 'approved\nmerged ' + 'f' * 40 + '\n')
        self.assertEqual(api.merges, [{'sha': SHA, 'merge_method': 'squash'}])
        self.assertEqual(sleeps, [30])
        self.assertEqual(len(api.posted), 1)

    def test_main_never_merges_blocked_failed_or_foreign_gates(self):
        blocked = FakeAPI([review(1, 'CHANGES_REQUESTED', '2026-11-26T10:00:00Z')])
        self.assertEqual(gate.main(self.env(), io.StringIO(), blocked, sleep=lambda s: None), 2)
        self.assertEqual(blocked.merges, [])
        for name, runs in {
                'failed gate': [check(GATES[0], conclusion='failure')]
                + [check(n) for n in GATES[1:]],
                'other app': [check(n, app='imposter') for n in GATES],
                'other sha': [check(n, sha=OLD) for n in GATES]}.items():
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                api.check_polls = [runs]
                if name == 'failed gate':
                    self.assertEqual(gate.main(self.env(), io.StringIO(), api,
                                               sleep=lambda s: None), 1)
                else:
                    with unittest.mock.patch.object(gate, 'CHECK_WAIT_SECONDS', -1):
                        self.assertEqual(gate.main(self.env(), io.StringIO(), api,
                                                   sleep=lambda s: None), 1)
                self.assertEqual(api.merges, [])

    def test_main_validates_environment(self):
        for bad in ({'PR_NUMBER': '7; rm'}, {'REVIEW_RUN_URL': 'https://evil.example/runs/1'},
                    {'REVIEW_STARTED_AT': 'yesterday'}):
            with self.subTest(bad):
                quiet = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                self.assertEqual(gate.main(self.env(**bad), io.StringIO(), quiet), 1)
                self.assertEqual((quiet.posted, quiet.merges), ([], []))

if __name__ == '__main__':
    unittest.main()
