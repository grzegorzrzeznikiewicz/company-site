"""AI review verdict to owner solo-report bridge; literals model GitHub REST fields."""

import copy
import io
import unittest
import unittest.mock

from wordpress.release import ai_review_gate as gate
from wordpress.release.github_source import SOLO_REVIEW_PREFIX, json_object

SHA = '1234567890abcdef1234567890abcdef12345678'
OLD = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
ROOT = '/repos/grzegorzrzeznikiewicz/company-site'
REPO = {'id': 1163583409, 'full_name': 'grzegorzrzeznikiewicz/company-site', 'fork': False}
OWNER = {'id': 50638878, 'login': 'grzegorzrzeznikiewicz', 'type': 'User'}
BOT = {'id': 209825114, 'login': 'claude[bot]', 'type': 'Bot'}
RUN_ID = 4242
GATES = ['WordPress Source and Build', 'WordPress Package Lifecycle',
         'WordPress Runtime and Restore', 'WordPress Release Regression']


def review(review_id, state, when, commit=SHA, user=BOT, body='Verdict and findings.'):
    return {'id': review_id, 'state': state, 'submitted_at': when, 'commit_id': commit,
            'user': user, 'body': body,
            'html_url': 'https://github.com/x/pull/7#pullrequestreview-' + str(review_id)}


def ci_run(status='completed', conclusion='success', path='.github/workflows/wordpress-ci.yml',
           sha=SHA, number=10):
    return {'id': 900 + number, 'run_number': number, 'run_attempt': 1, 'path': path,
            'head_sha': sha, 'event': 'pull_request', 'status': status,
            'conclusion': conclusion, 'repository': REPO}


class FakeAPI:
    def __init__(self, reviews, files=('wordpress/theme/gama-software/theme.json',)):
        self.run = {'id': RUN_ID, 'path': '.github/workflows/ai-code-review.yml',
                    'event': 'pull_request', 'status': 'completed', 'conclusion': 'success',
                    'repository': REPO, 'head_repository': REPO, 'head_sha': SHA,
                    'run_started_at': '2026-11-26T09:00:00Z', 'updated_at': '2026-11-26T13:00:00Z'}
        self.pr = {'number': 7, 'state': 'open', 'draft': False, 'user': OWNER,
                   'base': {'ref': 'main', 'repo': REPO}, 'head': {'sha': SHA, 'repo': REPO},
                   'changed_files': len(files)}
        self.reviews = reviews
        self.files = [{'filename': name} for name in files]
        self.ci_polls = [[ci_run()]]
        self.jobs = [{'name': name, 'conclusion': 'success', 'head_sha': SHA} for name in GATES]
        self.posted = []
        self.merges = []

    def get(self, path):
        if path == ROOT + '/actions/runs/' + str(RUN_ID):
            return copy.deepcopy(self.run)
        if path == ROOT + '/commits/' + SHA + '/pulls':
            return [copy.deepcopy(self.pr)]
        if path == ROOT + '/pulls/7':
            return copy.deepcopy(self.pr)
        raise AssertionError(path)

    def pages(self, path, key=None):
        if path == ROOT + '/pulls/7/reviews':
            return copy.deepcopy(self.reviews)
        if path == ROOT + '/pulls/7/files':
            return copy.deepcopy(self.files)
        if path == (ROOT + '/actions/workflows/wordpress-ci.yml/runs?event=pull_request&head_sha='
                    + SHA):
            assert key == 'workflow_runs'
            runs = self.ci_polls[0] if len(self.ci_polls) == 1 else self.ci_polls.pop(0)
            return copy.deepcopy(runs)
        if path.startswith(ROOT + '/actions/runs/') and path.endswith('/jobs'):
            assert key == 'jobs'
            return copy.deepcopy(self.jobs)
        raise AssertionError(path)

    def post(self, path, payload):
        assert path == ROOT + '/pulls/7/reviews', path
        self.posted.append(payload)
        return {'id': 901, 'state': 'COMMENTED', 'commit_id': payload['commit_id'], 'user': OWNER}

    def put(self, path, payload):
        assert path == ROOT + '/pulls/7/merge', path
        self.merges.append(payload)
        return {'merged': True, 'sha': 'f' * 40}


def run_gate(api, sleeps=None):
    out = io.StringIO()
    code = gate.main({'REVIEW_RUN_ID': str(RUN_ID)}, out, api,
                     sleep=(sleeps.append if sleeps is not None else lambda s: None))
    return code, out.getvalue()


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

    def test_approval_is_recorded_then_merged_pinned_to_sha_after_gates(self):
        api = FakeAPI([review(1, 'CHANGES_REQUESTED', '2026-11-26T08:00:00Z', commit=OLD),
                       review(2, 'APPROVED', '2026-11-26T11:00:00Z'),
                       review(3, 'COMMENTED', '2026-11-26T12:00:00Z')])
        api.ci_polls = [[], [ci_run(status='in_progress', conclusion=None)], [ci_run()]]
        sleeps = []
        code, out = run_gate(api, sleeps)
        self.assertEqual(code, 0)
        self.assertEqual(out, 'PR #7 at ' + SHA + '\napproved\nmerged ' + 'f' * 40 + '\n')
        parsed = self.report(api)
        self.assertEqual(parsed['result'], 'approved')
        self.assertIn('Verdict and findings.', parsed['report'])
        self.assertIn('review 2', parsed['report'])
        self.assertEqual(api.merges, [{'sha': SHA, 'merge_method': 'squash'}])
        self.assertEqual(sleeps, [30, 30])

    def test_blocking_verdict_is_recorded_and_never_merges(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T08:00:00Z'),
                       review(2, 'CHANGES_REQUESTED', '2026-11-26T11:00:00Z')])
        self.assertEqual(run_gate(api)[0], gate.EXIT_BLOCKED)
        self.assertEqual(self.report(api)['result'], 'changes-requested')
        self.assertEqual(api.merges, [])

    def test_review_machinery_changes_are_never_automated(self):
        for name in ('.github/workflows/ai-code-review.yml', '.github/workflows/new.yml',
                     '.claude/settings.json', '.claude/skills/om-code-review/SKILL.md',
                     '.ai/agentic.config.json', 'skills-lock.json', 'CODE_REVIEW.md',
                     'AGENTS.md', 'CLAUDE.md', 'CLAUDE.local.md', '.mcp.json',
                     'wordpress/CLAUDE.md', 'wordpress/theme/AGENTS.md', 'docs/x/CLAUDE.local.md',
                     'wordpress/plugins/x/.claude/settings.json', 'docs/.mcp.json',
                     'wordpress/release/ai_review_gate.py', 'wordpress/release/github_source.py',
                     'wordpress/tests/release/test_promote.py',
                     'wordpress/tests/wordpress-ci-contract.sh'):
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')],
                              files=('docs/a.md', name))
                self.assertEqual(run_gate(api)[0], gate.EXIT_MANUAL)
                self.assertEqual((api.posted, api.merges), ([], []))
        renamed = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
        renamed.files = [{'filename': 'docs/x.md', 'previous_filename': 'CODE_REVIEW.md'}]
        renamed.pr['changed_files'] = 1
        self.assertEqual(run_gate(renamed)[0], gate.EXIT_MANUAL)
        lookalike = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')],
                            files=('docs/.github-notes.md', 'wordpress/AGENTS.md.txt'))
        self.assertEqual(run_gate(lookalike)[0], 0)

    def test_truncated_or_oversized_file_lists_fail_closed(self):
        for name, mutate in {
                'truncated listing': lambda api: api.pr.update(changed_files=3500),
                'listing shorter than count': lambda api: api.pr.update(changed_files=2),
                'listing at api cap': lambda api: (api.pr.update(changed_files=3000),
                                                   setattr(api, 'files', api.files * 3000)),
                'missing count': lambda api: api.pr.pop('changed_files')}.items():
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                mutate(api)
                self.assertEqual(run_gate(api)[0], 1)
                self.assertEqual((api.posted, api.merges), ([], []))

    def test_untrusted_or_stale_verdicts_record_nothing(self):
        cases = {
            'earlier run': [review(1, 'APPROVED', '2026-11-26T08:59:59Z')],
            'after run': [review(1, 'APPROVED', '2026-11-26T13:00:01Z')],
            'two verdicts in run': [review(1, 'APPROVED', '2026-11-26T10:00:00Z'),
                                    review(2, 'APPROVED', '2026-11-26T10:05:00Z')],
            'minted for other head': [review(1, 'APPROVED', '2026-11-26T10:00:00Z'),
                                      review(2, 'APPROVED', '2026-11-26T10:01:00Z', commit=OLD)],
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
                self.assertEqual(run_gate(api)[0], 1)
                self.assertEqual((api.posted, api.merges), ([], []))

    def test_triggering_run_and_pr_shape_are_pinned(self):
        mutations = {
            'other workflow': lambda api: api.run.update(path='.github/workflows/evil.yml'),
            'push event': lambda api: api.run.update(event='push'),
            'failed run': lambda api: api.run.update(conclusion='failure'),
            'fork run': lambda api: api.run.update(head_repository=dict(REPO, id=1, fork=True)),
            'moved head': lambda api: api.pr['head'].update(sha=OLD),
            'draft': lambda api: api.pr.update(draft=True),
            'other base': lambda api: api.pr['base'].update(ref='develop'),
            'fork head': lambda api: api.pr['head'].update(repo=dict(REPO, id=1, fork=True)),
            'other author': lambda api: api.pr.update(user={'id': 1, 'login': 'x', 'type': 'User'}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                mutate(api)
                self.assertEqual(run_gate(api)[0], 1)
                self.assertEqual((api.posted, api.merges), ([], []))

    def test_quality_gates_are_pinned_to_the_ci_workflow(self):
        cases = {
            'failed run': ([ci_run(conclusion='failure')], None),
            'shadow workflow only': ([ci_run(path='.github/workflows/fake.yml')], None),
            'other sha': ([ci_run(sha=OLD)], None),
            'failed job': ([ci_run()], 'job'),
            'missing job': ([ci_run()], 'missing'),
            'latest rerun failed': ([ci_run(number=10), ci_run(conclusion='failure', number=11)],
                                    None),
        }
        for name, (runs, mode) in cases.items():
            with self.subTest(name):
                api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
                api.ci_polls = [runs]
                if mode == 'job':
                    api.jobs[2]['conclusion'] = 'failure'
                elif mode == 'missing':
                    api.jobs = api.jobs[:3]
                with unittest.mock.patch.object(gate, 'CHECK_WAIT_SECONDS', -1):
                    self.assertEqual(run_gate(api)[0], 1)
                self.assertEqual(api.merges, [])
                self.assertEqual(len(api.posted), 1)

    def test_oversized_report_is_truncated_within_production_limit(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z', body='ą"' * 60000)])
        self.assertEqual(run_gate(api)[0], 0)
        parsed = self.report(api)
        self.assertLessEqual(len(api.posted[0]['body'].encode('utf-8')), 64 * 1024)
        self.assertIn('[report truncated', parsed['report'])

    def test_invalid_run_id_and_unreachable_api_fail_closed(self):
        api = FakeAPI([review(1, 'APPROVED', '2026-11-26T10:00:00Z')])
        for bad in ('', '0', '12; rm', '-1'):
            with self.subTest(bad):
                self.assertEqual(gate.main({'REVIEW_RUN_ID': bad}, io.StringIO(), api), 1)
        self.assertEqual((api.posted, api.merges), ([], []))
        offline = gate.GitHubAPI('token', base='http://127.0.0.1:9')
        self.assertEqual(gate.main({'REVIEW_RUN_ID': '5'}, io.StringIO(), offline), 1)


if __name__ == '__main__':
    unittest.main()
