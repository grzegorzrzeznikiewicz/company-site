"""Turn the automated Open Mercato review verdict into the owner's solo AI report.

`AI Code Review` (`.github/workflows/ai-code-review.yml`, `pull_request`) runs
Open Mercato `om-code-review` (the `om-auto-review-pr` review engine) as the
Claude GitHub App (`claude[bot]`). When it
completes, `AI Review Gate` (`.github/workflows/ai-review-gate.yml`,
`workflow_run`) runs this file from the default branch with `python3 -I`, so
no repository file can shadow its standard-library imports, in the `ai-merge`
environment that only `main` may use, so no PR-controlled workflow or code
ever sees the owner token. The module trusts nothing from the triggering
event except the run id, and re-reads everything else from the GitHub API:

1. The run must be an exact, successful `pull_request` run of the pinned review
   workflow for an open owner PR from this repository to `main`, still at that
   head.
2. PRs touching the review machinery or release tooling (`is_sensitive`:
   workflows, Claude/agent instruction files at any depth, skills, review rules,
   `wordpress/release/`) are never automated; they need a manual review and
   merge. The complete file list must be verifiable (fewer than 3000 files).
3. The single decisive `claude[bot]` review submitted during this run, on the
   exact head, is recorded with the owner token as the `GAMA-SOLO-AI-REVIEW-V1`
   COMMENTED review that `github_source._solo_approval` requires. A blocking
   verdict is recorded as `changes-requested` and nothing merges.
4. On approval it waits for the pinned `WordPress Quality Gates` run on that
   head and squash-merges with `sha=<head>`, which GitHub enforces at merge time.

Anything missing, stale, ambiguous or unexpected exits non-zero.
"""

from datetime import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

REPOSITORY = 'grzegorzrzeznikiewicz/company-site'
REPOSITORY_ID = 1163583409
ROOT = '/repos/' + REPOSITORY
OWNER_ID = 50638878
OWNER_LOGIN = 'grzegorzrzeznikiewicz'
REVIEWER_LOGIN = 'claude[bot]'
REVIEW_WORKFLOW_PATH = '.github/workflows/ai-code-review.yml'
CI_WORKFLOW_PATH = '.github/workflows/wordpress-ci.yml'
SOLO_REVIEW_PREFIX = 'GAMA-SOLO-AI-REVIEW-V1\n'
MAX_BODY_BYTES = 64 * 1024
VERDICTS = {'APPROVED': 'approved', 'CHANGES_REQUESTED': 'changes-requested'}
WP_GATES = ('WordPress Source and Build', 'WordPress Package Lifecycle',
            'WordPress Runtime and Restore', 'WordPress Release Regression')
SENSITIVE_PATHS = ('.github/', '.claude/', '.ai/', 'skills-lock.json', 'CODE_REVIEW.md',
                   '.mcp.json', 'wordpress/release/', 'wordpress/tests/release/',
                   'wordpress/tests/wordpress-ci-contract.sh')
# Files Claude Code or the skills load as instructions wherever they live.
SENSITIVE_NAMES = ('CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', '.mcp.json')
SENSITIVE_SEGMENTS = ('.claude', '.github', '.ai')
# Python can be imported by the release tooling and gates; none is automated.
SENSITIVE_SUFFIXES = ('.py', '.pth')
MAX_LISTED_FILES = 3000
CHECK_POLL_SECONDS = 30
CHECK_WAIT_SECONDS = 50 * 60
EXIT_BLOCKED = 2
EXIT_MANUAL = 3


class GateError(Exception):
    """The verdict cannot be trusted or acted on; nothing more is done."""


class ManualReview(GateError):
    """The PR is outside automation; the owner reviews and merges it by hand."""


def require(condition, message):
    if not condition:
        raise GateError(message)


def full_sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None


def utc(value):
    require(type(value) is str and re.fullmatch(
        '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value) is not None,
        'UTC timestamp required')
    return datetime.fromisoformat(value[:-1] + '+00:00')


class GitHubAPI:
    def __init__(self, token, base='https://api.github.com'):
        require(type(token) is str and token.strip(), 'GitHub token required')
        self.token = token
        self.base = base.rstrip('/')

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + self.token,
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'gama-ai-review-gate'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8') or 'null')
        except urllib.error.HTTPError as error:
            raise GateError('GitHub API ' + method + ' ' + path.split('?')[0]
                            + ' failed: ' + str(error.code)) from error
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise GateError('GitHub API ' + method + ' ' + path.split('?')[0]
                            + ' unavailable: ' + type(error).__name__) from error

    def get(self, path):
        return self.request('GET', path)

    def pages(self, path, key=None):
        items = []
        for page in range(1, 51):
            separator = '&' if '?' in path else '?'
            batch = self.get(path + separator + 'per_page=100&page=' + str(page))
            if key is not None:
                require(type(batch) is dict, 'object response expected')
                batch = batch.get(key)
            require(type(batch) is list, 'list response expected')
            items.extend(batch)
            if len(batch) < 100:
                return items
        raise GateError('too many pages')

    def post(self, path, payload):
        return self.request('POST', path, payload)

    def put(self, path, payload):
        return self.request('PUT', path, payload)


def _same_repo(repo):
    return (type(repo) is dict and repo.get('id') == REPOSITORY_ID
            and repo.get('full_name') == REPOSITORY and repo.get('fork') is False)


def _is_owner(user):
    return (type(user) is dict and user.get('id') == OWNER_ID
            and user.get('login') == OWNER_LOGIN and user.get('type') == 'User')


def _is_reviewer(user):
    return (type(user) is dict and user.get('login') == REVIEWER_LOGIN
            and user.get('type') == 'Bot' and type(user.get('id')) is int)


def review_run(api, run_id):
    run = api.get(ROOT + '/actions/runs/' + str(run_id))
    require(type(run) is dict and run.get('id') == run_id, 'review run unavailable')
    require(run.get('path') == REVIEW_WORKFLOW_PATH and run.get('event') == 'pull_request'
            and run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'triggering run is not a successful pinned AI review run')
    require(_same_repo(run.get('repository')) and _same_repo(run.get('head_repository')),
            'review run is not from this repository')
    require(full_sha(run.get('head_sha')), 'review run head missing')
    started, finished = utc(run.get('run_started_at')), utc(run.get('updated_at'))
    require(started <= finished, 'invalid review run window')
    return run['head_sha'], (started, finished)


def open_pull(api, head_sha):
    listed = api.get(ROOT + '/commits/' + head_sha + '/pulls')
    require(type(listed) is list, 'associated PR list unavailable')
    found = [pr for pr in listed if type(pr) is dict
             and pr.get('state') == 'open' and pr.get('head', {}).get('sha') == head_sha]
    require(len(found) == 1, 'exactly one open PR at the reviewed head required')
    number = found[0].get('number')
    require(type(number) is int and number > 0, 'invalid PR number')
    pr = api.get(ROOT + '/pulls/' + str(number))
    require(pr.get('number') == number and pr.get('state') == 'open'
            and pr.get('draft') is False, 'PR is not open and ready')
    require(pr.get('base', {}).get('ref') == 'main' and _same_repo(pr['base'].get('repo'))
            and _same_repo(pr.get('head', {}).get('repo')), 'PR must target main from this repository')
    require(_is_owner(pr.get('user')), 'only owner PRs are automated')
    require(pr['head'].get('sha') == head_sha, 'PR head moved; a newer review run owns it')
    return number, pr.get('changed_files')


def is_sensitive(name):
    parts = name.split('/')
    return (any(name == path or path.endswith('/') and name.startswith(path)
                for path in SENSITIVE_PATHS)
            or parts[-1] in SENSITIVE_NAMES
            or parts[-1].endswith(SENSITIVE_SUFFIXES)
            or any(part in SENSITIVE_SEGMENTS for part in parts[:-1]))


def sensitive_files(api, number, changed_files):
    require(type(changed_files) is int and 0 < changed_files < MAX_LISTED_FILES,
            'PR too large to verify its file list')
    listed = api.pages(ROOT + '/pulls/' + str(number) + '/files')
    require(len(listed) == changed_files, 'PR file list is incomplete')
    names = set()
    for item in listed:
        require(type(item) is dict and type(item.get('filename')) is str, 'invalid PR file entry')
        names.add(item['filename'])
        if type(item.get('previous_filename')) is str:
            names.add(item['previous_filename'])
    return sorted(name for name in names if is_sensitive(name))


def run_verdict(reviews, head_sha, window):
    """The single decisive claude[bot] review on `head_sha` submitted during this run.

    More than one (a re-review, or a review minted by another workflow) is ambiguous
    and refused rather than ordered.
    """
    started, finished = window
    decisive = []
    for review in reviews:
        require(type(review) is dict, 'invalid review entry')
        if not _is_reviewer(review.get('user')) or review.get('state') not in VERDICTS:
            continue
        submitted = utc(review.get('submitted_at'))
        if started <= submitted <= finished:
            require(review.get('commit_id') == head_sha, 'AI verdict in this run is not on the head')
            decisive.append(review)
    if not decisive:
        return None
    require(len(decisive) == 1, 'more than one AI verdict during this run')
    return decisive[0]


def report_body(head_sha, review, run_url):
    result = VERDICTS[review['state']]
    header = ('Automated review: Open Mercato om-code-review + repo CODE_REVIEW.md, '
              'submitted by ' + REVIEWER_LOGIN + ' as review ' + str(review['id'])
              + ' (' + str(review.get('html_url', '')) + '), workflow run ' + run_url
              + '. Verdict: ' + result + '.\n\n')
    text = review.get('body') if type(review.get('body')) is str else ''
    require(text.strip(), 'AI verdict has an empty report')
    marker = '\n\n[report truncated; full text in the linked review]'
    while True:
        body = SOLO_REVIEW_PREFIX + json.dumps(
            {'head_sha': head_sha, 'result': result, 'report': header + text},
            ensure_ascii=False, separators=(',', ':'))
        size = len(body.encode('utf-8'))
        if size <= MAX_BODY_BYTES:
            return body
        cut = min(len(text) - len(marker) - 1, int(len(text) * MAX_BODY_BYTES * 0.9 / size))
        require(cut > 1024, 'AI report cannot fit the size limit')
        text = text[:cut].rstrip() + marker


def record(api, number, head_sha, window, run_url):
    reviews = api.pages(ROOT + '/pulls/' + str(number) + '/reviews')
    review = run_verdict(reviews, head_sha, window)
    require(review is not None, 'no AI verdict from this run on the exact PR head')
    recorded = api.post(ROOT + '/pulls/' + str(number) + '/reviews',
                        {'commit_id': head_sha, 'event': 'COMMENT',
                         'body': report_body(head_sha, review, run_url)})
    require(type(recorded) is dict and recorded.get('state') == 'COMMENTED'
            and recorded.get('commit_id') == head_sha and _is_owner(recorded.get('user')),
            'owner report was not recorded on the exact head')
    return VERDICTS[review['state']]


def gates_state(api, head_sha):
    runs = [run for run in api.pages(
        ROOT + '/actions/workflows/wordpress-ci.yml/runs?event=pull_request&head_sha=' + head_sha,
        'workflow_runs')
        if run.get('path') == CI_WORKFLOW_PATH and run.get('head_sha') == head_sha
        and run.get('event') == 'pull_request' and _same_repo(run.get('repository'))]
    if not runs:
        return 'pending'
    run = max(runs, key=lambda item: (item.get('run_number', 0), item.get('run_attempt', 0)))
    if run.get('status') != 'completed':
        return 'pending'
    require(run.get('conclusion') == 'success', 'WordPress Quality Gates did not pass')
    jobs = api.pages(ROOT + '/actions/runs/' + str(run['id']) + '/jobs', 'jobs')
    for name in WP_GATES:
        matches = [job for job in jobs if job.get('name') == name]
        require(len(matches) == 1 and matches[0].get('conclusion') == 'success'
                and matches[0].get('head_sha') == head_sha, 'quality gate did not pass: ' + name)
    return 'success'


def merge_when_green(api, number, head_sha, sleep=time.sleep, clock=time.monotonic):
    deadline = clock() + CHECK_WAIT_SECONDS
    while gates_state(api, head_sha) != 'success':
        require(clock() < deadline, 'quality gates still pending after the wait budget')
        sleep(CHECK_POLL_SECONDS)
    merged = api.put(ROOT + '/pulls/' + str(number) + '/merge',
                     {'sha': head_sha, 'merge_method': 'squash'})
    require(type(merged) is dict and merged.get('merged') is True
            and full_sha(merged.get('sha')), 'merge was not completed')
    return merged['sha']


def main(environ=os.environ, out=sys.stdout, api=None, sleep=time.sleep):
    try:
        run_id = environ.get('REVIEW_RUN_ID', '')
        require(re.fullmatch('[1-9][0-9]{0,14}', run_id) is not None, 'invalid review run id')
        run_url = 'https://github.com/' + REPOSITORY + '/actions/runs/' + run_id
        api = api or GitHubAPI(environ.get('GH_TOKEN', ''))
        head_sha, window = review_run(api, int(run_id))
        number, changed_files = open_pull(api, head_sha)
        print('PR #' + str(number) + ' at ' + head_sha, file=out, flush=True)
        sensitive = sensitive_files(api, number, changed_files)
        if sensitive:
            raise ManualReview('PR changes review machinery (' + ', '.join(sensitive[:10])
                               + '); owner reviews and merges it manually')
        result = record(api, number, head_sha, window, run_url)
        print(result, file=out, flush=True)
        if result != 'approved':
            return EXIT_BLOCKED
        merge_sha = merge_when_green(api, number, head_sha, sleep=sleep)
    except ManualReview as error:
        print('ai-review-gate: manual: ' + str(error), file=sys.stderr)
        return EXIT_MANUAL
    except GateError as error:
        print('ai-review-gate: refused: ' + str(error), file=sys.stderr)
        return 1
    except (AttributeError, KeyError, TypeError) as error:
        print('ai-review-gate: refused: unexpected API shape: ' + type(error).__name__,
              file=sys.stderr)
        return 1
    print('merged ' + merge_sha, file=out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
