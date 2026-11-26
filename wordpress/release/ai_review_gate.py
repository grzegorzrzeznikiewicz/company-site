"""Turn the automated Open Mercato review verdict into the owner's solo AI report.

The `AI Code Review` workflow runs the `om-auto-review-pr` skill as the Claude
GitHub App (`claude[bot]`). This module reads that bot's latest decisive review
on the exact PR head and records it, with the owner's repository-scoped token,
as the `GAMA-SOLO-AI-REVIEW-V1` COMMENTED review that the production source
check (`github_source._solo_approval`) already requires. It never merges; the
workflow enables auto-merge only after this module prints `approved`.

Fail closed: a missing, stale, pending or unrecognised verdict records nothing
and exits non-zero. A blocking verdict is recorded as `changes-requested` so a
manual merge of that head is still refused by the production pipeline.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

REPOSITORY = 'grzegorzrzeznikiewicz/company-site'
REPOSITORY_ID = 1163583409
ROOT = '/repos/' + REPOSITORY
OWNER_ID = 50638878
OWNER_LOGIN = 'grzegorzrzeznikiewicz'
REVIEWER_LOGIN = 'claude[bot]'
SOLO_REVIEW_PREFIX = 'GAMA-SOLO-AI-REVIEW-V1\n'
MAX_BODY_BYTES = 64 * 1024
VERDICTS = {'APPROVED': 'approved', 'CHANGES_REQUESTED': 'changes-requested'}


class GateError(Exception):
    """The verdict cannot be trusted; nothing is recorded."""


def require(condition, message):
    if not condition:
        raise GateError(message)


def full_sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None


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
            raise GateError('GitHub API ' + method + ' ' + path + ' failed: '
                            + str(error.code)) from error

    def get(self, path):
        return self.request('GET', path)

    def pages(self, path):
        items = []
        for page in range(1, 51):
            separator = '&' if '?' in path else '?'
            batch = self.get(path + separator + 'per_page=100&page=' + str(page))
            require(type(batch) is list, 'list response expected')
            items.extend(batch)
            if len(batch) < 100:
                return items
        raise GateError('too many pages')

    def post(self, path, payload):
        return self.request('POST', path, payload)


def _same_repo(repo):
    return (type(repo) is dict and repo.get('id') == REPOSITORY_ID
            and repo.get('full_name') == REPOSITORY and repo.get('fork') is False)


def _is_owner(user):
    return (type(user) is dict and user.get('id') == OWNER_ID
            and user.get('login') == OWNER_LOGIN and user.get('type') == 'User')


def _is_reviewer(user):
    return (type(user) is dict and user.get('login') == REVIEWER_LOGIN
            and user.get('type') == 'Bot' and type(user.get('id')) is int)


def latest_verdict(reviews, head_sha):
    """Latest submitted decisive claude[bot] review on `head_sha`, or None."""
    decisive = []
    for review in reviews:
        if not _is_reviewer(review.get('user')):
            continue
        if review.get('commit_id') != head_sha or review.get('state') not in VERDICTS:
            continue
        submitted = review.get('submitted_at')
        require(type(submitted) is str and submitted.endswith('Z'), 'review timestamp missing')
        decisive.append((submitted, review))
    if not decisive:
        return None
    latest_time = max(when for when, _ in decisive)
    latest = [review for when, review in decisive if when == latest_time]
    require(len(latest) == 1, 'ambiguous latest AI verdict')
    return latest[0]


def report_body(head_sha, review, run_url):
    result = VERDICTS[review['state']]
    header = ('Automated review: Open Mercato om-auto-review-pr + repo CODE_REVIEW.md, '
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
        if len(body.encode('utf-8')) <= MAX_BODY_BYTES:
            return body
        size = len(body.encode('utf-8'))
        cut = min(len(text) - len(marker) - 1, int(len(text) * MAX_BODY_BYTES * 0.9 / size))
        require(cut > 1024, 'AI report cannot fit the size limit')
        text = text[:cut].rstrip() + marker


def run(api, number, expected_head, run_url):
    require(type(number) is int and number > 0, 'invalid PR number')
    require(full_sha(expected_head), 'invalid expected head SHA')
    pr = api.get(ROOT + '/pulls/' + str(number))
    require(pr.get('number') == number and pr.get('state') == 'open'
            and pr.get('draft') is False, 'PR is not open and ready')
    require(pr.get('base', {}).get('ref') == 'main' and _same_repo(pr['base'].get('repo'))
            and _same_repo(pr.get('head', {}).get('repo')), 'PR must target main from this repository')
    require(_is_owner(pr.get('user')), 'only owner PRs are automated')
    head_sha = pr['head'].get('sha')
    require(head_sha == expected_head, 'PR head moved; a newer review run owns it')
    review = latest_verdict(api.pages(ROOT + '/pulls/' + str(number) + '/reviews'), head_sha)
    require(review is not None, 'no AI verdict on the exact PR head')
    body = report_body(head_sha, review, run_url)
    recorded = api.post(ROOT + '/pulls/' + str(number) + '/reviews',
                        {'commit_id': head_sha, 'event': 'COMMENT', 'body': body})
    require(type(recorded) is dict and recorded.get('state') == 'COMMENTED'
            and recorded.get('commit_id') == head_sha and _is_owner(recorded.get('user')),
            'owner report was not recorded on the exact head')
    return VERDICTS[review['state']]


def main(environ=os.environ, out=sys.stdout, api=None):
    try:
        number = environ.get('PR_NUMBER', '')
        require(re.fullmatch('[1-9][0-9]{0,8}', number) is not None, 'invalid PR number')
        run_url = environ.get('REVIEW_RUN_URL', '')
        require(re.fullmatch(r'https://github\.com/' + re.escape(REPOSITORY)
                             + r'/actions/runs/[0-9]+(/attempts/[0-9]+)?', run_url) is not None,
                'invalid run URL')
        api = api or GitHubAPI(environ.get('GH_TOKEN', ''))
        result = run(api, int(number), environ.get('EXPECTED_HEAD_SHA', ''), run_url)
    except GateError as error:
        print('ai-review-gate: refused: ' + str(error), file=sys.stderr)
        return 1
    print(result, file=out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
