"""Fail-closed, read-only GitHub provenance for the isolated release pipeline.

The REST credential needs Actions, Checks, Contents, Pull requests and repository
metadata reads, plus Administration read for classic branch protection. That last
permission is not an available workflow GITHUB_TOKEN YAML scope.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from wordpress.release.manifest import ReleaseValidationError

REPOSITORY = 'grzegorzrzeznikiewicz/company-site'
REPOSITORY_ID = 1163583409
WORKFLOW_ID = 351411087
WORKFLOW_PATH = '.github/workflows/wordpress-ci.yml'
ROOT = '/repos/' + REPOSITORY
OWNER_ID = 50638878
OWNER_LOGIN = 'grzegorzrzeznikiewicz'
SOLO_REVIEW_PREFIX = 'GAMA-SOLO-AI-REVIEW-V1\n'
WP_GATES = ('WordPress Source and Build', 'WordPress Package Lifecycle',
            'WordPress Runtime and Restore', 'WordPress Release Regression')
LEGACY_GATES = ('Backend Quality (Symfony)', 'Backend Tests',
                'Frontend Quality', 'End-to-End Tests')
MAX_ZIP_BYTES = 4 * 1024 * 1024 * 1024 + 1024 * 1024


class SourcePendingError(ReleaseValidationError):
    """Exact-SHA checks are still running; caller may retry with a fixed deadline.

    This is never a successful validation. Other validation errors are not
    retryable through this interface. The CLI uses exit code 3 with no output.
    """


def require(condition, message):
    if not condition:
        raise ReleaseValidationError(message)


def positive(value):
    return type(value) is int and value > 0


def full_sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None


def timestamp(value):
    require(type(value) is str and value.endswith('Z'), 'UTC timestamp required')
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as error:
        raise ReleaseValidationError('invalid UTC timestamp') from error


def json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ReleaseValidationError('non-finite JSON number')

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as error:
        raise ReleaseValidationError('invalid JSON response') from error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubAPI:
    """GET-only adapter; custom loopback origins support local integration tests.

    CLI callers always use api.github.com. No token is forwarded to artifact
    storage. Pagination accepts only the exact sequential endpoint URL.
    """

    def __init__(self, token, *, base_url='https://api.github.com'):
        parsed = urllib.parse.urlsplit(base_url)
        require(base_url == 'https://api.github.com' or (
            parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'
            and parsed.path == '' and not parsed.username and not parsed.query
            and not parsed.fragment), 'untrusted GitHub API origin')
        require(type(token) is str and token and not any(c.isspace() for c in token),
                'read-only GitHub credential is required')
        self.base_url = base_url
        self.token = token
        self.opener = urllib.request.build_opener(_NoRedirect)
        self.repository_verified = False

    def _request(self, path):
        roots = (ROOT,) + (('/repositories/' + str(REPOSITORY_ID),) if self.repository_verified else ())
        require(type(path) is str and any(path == root or path.startswith(root + '/')
                or path.startswith(root + '?') for root in roots) and
                '\n' not in path and '\r' not in path and '#' not in path,
                'invalid repository API path')
        request = urllib.request.Request(self.base_url + path, headers={
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'gama-wordpress-provenance',
        }, method='GET')
        return self.opener.open(request, timeout=30)

    def get(self, path, *, headers=False):
        try:
            with self._request(path) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                require(len(raw) <= 16 * 1024 * 1024, 'GitHub response too large')
                value = json_object(raw)
                return (value, response.headers) if headers else value
        except (OSError, urllib.error.URLError) as error:
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            raise ReleaseValidationError('GitHub read failed; required access unavailable') from error

    def pages(self, path, key=None):
        separator = '&' if '?' in path else '?'
        prefix = path + separator + 'per_page=100&page='
        canonical_prefix = '/repositories/' + str(REPOSITORY_ID) + prefix[len(ROOT):]
        current_prefix = prefix
        rows, total, seen = [], None, set()
        for page in range(1, 1001):
            value, headers = self.get(current_prefix + str(page), headers=True)
            if key:
                require(type(value) is dict and type(value.get('total_count')) is int,
                        'paginated response count missing')
                if total is None:
                    total = value['total_count']
                require(total == value['total_count'] and total >= 0,
                        'pagination changed during validation')
                batch = value.get(key)
            else:
                batch = value
            require(type(batch) is list and len(batch) <= 100, 'invalid page')
            for item in batch:
                require(type(item) is dict, 'invalid paginated item')
                identity = item.get('id')
                if identity is not None:
                    require(type(identity) is int and identity not in seen,
                            'duplicate paginated item')
                    seen.add(identity)
            rows.extend(batch)
            link = headers.get('Link', '')
            next_links = re.findall(r'<([^>]+)>;\s*rel="next"', link)
            require(len(next_links) <= 1, 'ambiguous pagination')
            if next_links:
                next_path = next_links[0]
                if next_path == self.base_url + canonical_prefix + str(page + 1):
                    if not self.repository_verified:
                        _repo(self.get(ROOT))
                        self.repository_verified = True
                    current_prefix = canonical_prefix
                else:
                    current_prefix = prefix
                require(next_path == self.base_url + current_prefix + str(page + 1)
                        and batch, 'untrusted or partial pagination')
                continue
            require('rel="next"' not in link, 'malformed pagination')
            if total is not None:
                require(len(rows) == total, 'incomplete pagination')
            return rows
        raise ReleaseValidationError('pagination limit exceeded')

    def download(self, artifact, destination):
        """Download one immutable ZIP with bounded size and SHA-256 verification."""
        require(positive(artifact.get('id')), 'invalid artifact ID')
        expected = artifact.get('digest')
        require(type(expected) is str and re.fullmatch('sha256:[0-9a-f]{64}', expected),
                'GitHub artifact digest missing')
        size = artifact.get('size_in_bytes')
        require(positive(size) and size <= MAX_ZIP_BYTES, 'invalid artifact size')
        try:
            try:
                response = self._request(ROOT + '/actions/artifacts/' + str(artifact['id']) + '/zip')
            except urllib.error.HTTPError as redirect:
                with redirect:
                    require(redirect.code == 302, 'artifact download failed')
                    location = redirect.headers.get('Location', '')
                parsed = urllib.parse.urlsplit(location)
                host = parsed.hostname or ''
                require(parsed.scheme == 'https' and not parsed.username and not parsed.password
                        and parsed.port in (None, 443) and not parsed.fragment and
                        (host.endswith('.blob.core.windows.net') or
                         host.endswith('.actions.githubusercontent.com')),
                        'untrusted artifact storage redirect')
                response = self.opener.open(urllib.request.Request(location, method='GET'), timeout=30)
            with response:
                digest, count = hashlib.sha256(), 0
                with open(destination, 'xb') as output:
                    while True:
                        chunk = response.read(min(1024 * 1024, size - count + 1))
                        if not chunk:
                            break
                        count += len(chunk)
                        require(count <= size, 'artifact exceeds declared size')
                        digest.update(chunk)
                        output.write(chunk)
                require(count == size and 'sha256:' + digest.hexdigest() == expected,
                        'GitHub ZIP digest or size mismatch')
        except (OSError, urllib.error.URLError) as error:
            raise ReleaseValidationError('artifact download failed') from error


def _repo(value):
    require(type(value) is dict and value.get('id') == REPOSITORY_ID
            and value.get('full_name') == REPOSITORY and value.get('fork') is False,
            'untrusted repository')


def _run(value, run_id, attempt, sha):
    require(type(value) is dict, 'missing workflow run')
    _repo(value.get('repository'))
    _repo(value.get('head_repository'))
    expected = {'id': run_id, 'run_attempt': attempt, 'workflow_id': WORKFLOW_ID,
                'path': WORKFLOW_PATH, 'head_sha': sha, 'head_branch': 'main',
                'event': 'push', 'status': 'completed', 'conclusion': 'success'}
    require(all(type(value.get(k)) is type(v) and value.get(k) == v
                for k, v in expected.items()), 'source run is not exact successful main attempt')


def _protection(api):
    classic = api.get(ROOT + '/branches/main/protection')
    require(type(classic) is dict, 'branch protection unavailable')
    rules = api.pages(ROOT + '/rules/branches/main')
    policies = []
    checks = []
    if classic.get('required_pull_request_reviews'):
        policies.append(classic['required_pull_request_reviews'])
    if classic.get('required_status_checks'):
        status = classic['required_status_checks']
        for item in status.get('checks', []):
            checks.append((item.get('context'), item.get('app_id')))
        for name in status.get('contexts', []):
            if not any(name == existing[0] for existing in checks):
                checks.append((name, None))
    for rule in rules:
        if rule.get('type') == 'pull_request':
            policies.append(rule.get('parameters', {}))
        elif rule.get('type') == 'required_status_checks':
            checks.extend((item.get('context'), item.get('integration_id'))
                          for item in rule.get('parameters', {}).get('required_status_checks', []))
    require(policies and checks, 'effective approval and nonempty check protections required')
    counts = [p.get('required_approving_review_count') for p in policies]
    require(all(type(n) is int and 0 <= n <= 6 for n in counts),
            'invalid required approval policy')
    if max(counts) == 0:
        require(classic.get('enforce_admins', {}).get('enabled') is True,
                'solo-owner policy requires protections enforced for administrators')
    # These policies need additional proof (CODEOWNERS / final pusher identity).
    require(not any(p.get('require_code_owner_reviews') or p.get('require_code_owner_review')
                    or p.get('require_last_push_approval') or p.get('required_reviewers')
                    for p in policies), 'configured review policy needs unavailable proof')
    require(all(type(name) is str and name and '\n' not in name and
                (app is None or type(app) is int and app >= -1)
                for name, app in checks), 'invalid required check policy')
    return max(counts), checks


def _approval(api, sha, count):
    for associated in api.pages(ROOT + '/commits/' + sha + '/pulls'):
        number = associated.get('number')
        require(positive(number), 'invalid associated pull request')
        pr = api.get(ROOT + '/pulls/' + str(number))
        if not (pr.get('merged') is True and pr.get('state') == 'closed'
                and pr.get('merge_commit_sha') == sha and pr.get('base', {}).get('ref') == 'main'):
            continue
        _repo(pr['base'].get('repo'))
        require(full_sha(pr.get('head', {}).get('sha')), 'missing merged PR head')
        merged = timestamp(pr.get('merged_at'))
        author = pr.get('user', {}).get('id')
        require(positive(author), 'missing PR author')
        reviews = api.pages(ROOT + '/pulls/' + str(number) + '/reviews')
        if count == 0:
            return _solo_approval(api, pr, number, merged, reviews)
        decisions = {}
        for review in sorted(reviews, key=lambda item: item.get('id', 0)):
            user = review.get('user', {})
            require(positive(review.get('id')) and positive(user.get('id')), 'invalid review identity')
            state = review.get('state')
            require(state in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED', 'COMMENTED', 'PENDING'),
                    'unknown review state')
            if state not in ('COMMENTED', 'PENDING'):
                decisions[user['id']] = review
        qualified = []
        for reviewer_id, review in decisions.items():
            user = review['user']
            if (review['state'] != 'APPROVED' or reviewer_id == author or
                    user.get('type') != 'User' or review.get('commit_id') != pr['head']['sha']
                    or timestamp(review.get('submitted_at')) > merged):
                continue
            login = user.get('login')
            require(type(login) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{0,38}', login),
                    'invalid reviewer login')
            permission = api.get(ROOT + '/collaborators/' + login + '/permission')
            identity = permission.get('user', {})
            require(identity.get('id') == reviewer_id and identity.get('login') == login,
                    'reviewer permission identity mismatch')
            if permission.get('permission') in ('write', 'admin'):
                qualified.append({'id': reviewer_id, 'login': login, 'review_id': review['id']})
        if len(qualified) >= count:
            return {'pull_request': number, 'head_sha': pr['head']['sha'],
                    'merged_at': pr['merged_at'], 'required_count': count, 'reviewers': qualified}
    raise ReleaseValidationError('merged PR with qualifying approval required')


def _is_owner(user):
    return (type(user) is dict and type(user.get('id')) is int
            and user['id'] == OWNER_ID and user.get('login') == OWNER_LOGIN
            and user.get('type') == 'User')


def _solo_approval(api, pr, number, merged, reviews):
    """Owner merge is consent; a COMMENTED review records the independent AI report.

    This is an owner attestation, not a second human or authenticated AI identity.
    Only explicit zero-review PR protection selects it; stricter rules stay strict.
    """
    _repo(pr['head'].get('repo'))
    require(_is_owner(pr.get('merged_by')), 'solo PR must be merged by the pinned owner')
    permission = api.get(ROOT + '/collaborators/' + OWNER_LOGIN + '/permission')
    require(_is_owner(permission.get('user')) and permission.get('permission') == 'admin',
            'solo owner identity or repository administration unavailable')
    decisions = []
    for review in reviews:
        require(positive(review.get('id')), 'invalid review identity')
        if not _is_owner(review.get('user')):
            continue
        body = review.get('body', '')
        if not (review.get('state') == 'CHANGES_REQUESTED'
                or type(body) is str and body.startswith(SOLO_REVIEW_PREFIX)):
            continue
        require(review.get('state') != 'PENDING', 'AI report has not been submitted')
        decisions.append((timestamp(review.get('submitted_at')), review))
    require(decisions, 'owner-recorded independent AI approval report required')
    # Review IDs are assigned before submission (a pending review may be older).
    # Conflicting submissions in the same timestamp cannot be safely ordered.
    latest_time = max(when for when, _ in decisions)
    latest_decisions = [review for when, review in decisions if when == latest_time]
    require(len(latest_decisions) == 1, 'ambiguous latest owner review submission')
    latest = latest_decisions[0]
    require(latest.get('state') == 'COMMENTED'
            and latest.get('commit_id') == pr['head']['sha']
            and timestamp(latest.get('submitted_at')) <= merged,
            'AI report is not submitted for the exact head before merge')
    body = latest['body']
    require(len(body.encode('utf-8')) <= 64 * 1024, 'AI report exceeds size limit')
    report = json_object(body[len(SOLO_REVIEW_PREFIX):])
    require(type(report) is dict and frozenset(report) == {'head_sha', 'result', 'report'}
            and report.get('head_sha') == pr['head']['sha']
            and report.get('result') == 'approved'
            and type(report.get('report')) is str and report['report'].strip(),
            'invalid SHA-bound AI approval report')
    return {'policy': 'solo-owner-ai-v1', 'pull_request': number,
            'head_sha': pr['head']['sha'], 'merged_at': pr['merged_at'],
            'owner': {'id': OWNER_ID, 'login': OWNER_LOGIN},
            'review_id': latest['id'],
            'report_sha256': hashlib.sha256(latest['body'].encode('utf-8')).hexdigest()}


def _checks(api, sha, required, source_run_id):
    legacy_workflow = api.get(ROOT + '/actions/workflows/ci.yml')
    require(positive(legacy_workflow.get('id'))
            and legacy_workflow.get('path') == '.github/workflows/ci.yml'
            and legacy_workflow.get('state') == 'active', 'legacy CI workflow identity unavailable')
    checks = api.pages(ROOT + '/commits/' + sha + '/check-runs?filter=latest', 'check_runs')
    statuses = api.pages(ROOT + '/commits/' + sha + '/statuses')
    for name, app_id in dict.fromkeys(required):
        matches = [c for c in checks if c.get('name') == name and
                   (app_id in (None, -1) or c.get('app', {}).get('id') == app_id)]
        matching_statuses = [s for s in statuses if s.get('context') == name]
        require(matches or matching_statuses, 'required main check missing: ' + name)
        if matches:
            require(len(matches) == 1 and matches[0].get('head_sha') == sha,
                    'required check does not identify exact main SHA: ' + name)
            if matches[0].get('status') in ('queued', 'in_progress'):
                raise SourcePendingError('required main check pending: ' + name)
            require(matches[0].get('status') == 'completed'
                    and matches[0].get('conclusion') == 'success',
                    'required exact-main check not successful: ' + name)
            check = matches[0]
            if check.get('app', {}).get('id') == 15368:
                link = check.get('details_url', '')
                match = re.fullmatch(r'https://github\.com/' + re.escape(REPOSITORY)
                                     + r'/actions/runs/([1-9][0-9]*)/job/([1-9][0-9]*)', link)
                require(match is not None, 'Actions check has no exact job identity')
                run_id, job_id = (int(value) for value in match.groups())
                current = api.get(ROOT + '/actions/runs/' + str(run_id))
                job = api.get(ROOT + '/actions/jobs/' + str(job_id))
                _repo(current.get('repository'))
                _repo(current.get('head_repository'))
                if name in WP_GATES:
                    require(current.get('workflow_id') == WORKFLOW_ID
                            and current.get('path') == WORKFLOW_PATH and run_id == source_run_id,
                            'WordPress check is not from the selected source workflow run')
                elif name in LEGACY_GATES:
                    require(current.get('workflow_id') == legacy_workflow['id']
                            and current.get('path') == legacy_workflow['path'],
                            'mandatory legacy job is not from the trusted CI workflow')
                require(current.get('id') == run_id and positive(current.get('run_attempt'))
                        and current.get('head_sha') == sha and current.get('head_branch') == 'main'
                        and current.get('event') == 'push'
                        and job.get('id') == job_id and job.get('run_id') == run_id
                        and job.get('run_attempt') == current['run_attempt']
                        and job.get('head_sha') == sha and job.get('name') == name
                        and job.get('status') == 'completed' and job.get('conclusion') == 'success',
                        'required Actions check is from a superseded or incomplete attempt')
                if current.get('status') in ('queued', 'in_progress', 'waiting', 'requested', 'pending'):
                    raise SourcePendingError('required main workflow still running: ' + name)
                require(current.get('status') == 'completed' and current.get('conclusion') == 'success',
                        'required main workflow did not succeed: ' + name)
        if matching_statuses:
            # A required name shared by Checks and Statuses requires both.
            # Status rows do not expose a verifiable app ID; a successful
            # Check Run cannot supply that missing provenance on their behalf.
            require(app_id in (None, -1),
                    'required commit status app provenance unavailable: ' + name)
            latest = max(matching_statuses, key=lambda item: item.get('id', 0))
            # Individual status objects have no sha field. The full-SHA GET
            # endpoint and its documented URL bind the status to this commit.
            require(positive(latest.get('id')) and latest.get('url') ==
                    'https://api.github.com' + ROOT + '/statuses/' + sha,
                    'required main status identity mismatch: ' + name)
            if latest.get('state') == 'pending':
                raise SourcePendingError('required main status pending: ' + name)
            require(latest.get('state') == 'success',
                    'required main status not successful: ' + name)


AUTHORIZATION_FIELDS = frozenset({
    'authorization_id', 'promotion_run_id', 'promotion_run_attempt', 'git_sha',
    'source_run_id', 'source_run_attempt', 'artifact_id', 'artifact_digest',
    'operators', 'window_start', 'window_end'})
CUTOVER_ENVIRONMENT = 'wordpress-production-cutover'


def authorization_comment(authorization):
    """Canonical review comment; formatting alone does not authorize anything."""
    require(type(authorization) is dict and frozenset(authorization) == AUTHORIZATION_FIELDS,
            'authorization fields do not match the closed schema')
    require(type(authorization['authorization_id']) is str and
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,127}', authorization['authorization_id']),
            'invalid authorization identifier')
    require(all(positive(authorization[key]) for key in (
        'promotion_run_id', 'source_run_id', 'source_run_attempt', 'artifact_id'))
        and type(authorization['promotion_run_attempt']) is int
        and authorization['promotion_run_attempt'] == 1
        and full_sha(authorization['git_sha'])
        and type(authorization['artifact_digest']) is str
        and re.fullmatch('sha256:[0-9a-f]{64}', authorization['artifact_digest']),
        'invalid authorization source binding')
    operators = authorization['operators']
    require(type(operators) is list and operators, 'explicit operators required')
    ids, logins = set(), set()
    for operator in operators:
        require(type(operator) is dict and set(operator) == {'id', 'login', 'type'}
                and positive(operator['id']) and operator['type'] == 'User'
                and type(operator['login']) is str
                and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{0,38}', operator['login'])
                and operator['id'] not in ids and operator['login'] not in logins,
                'operators must be distinct explicit human identities')
        ids.add(operator['id'])
        logins.add(operator['login'])
    require(timestamp(authorization['window_start']) < timestamp(authorization['window_end']),
            'invalid cutover window')
    return json.dumps(authorization, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _cutover(payload, api, mode):
    require(mode == 'off', 'first cutover requires off mode')
    _repo(payload.get('repository'))
    require(payload.get('ref') == 'refs/heads/main', 'trusted main dispatch required')
    authorization = payload.get('authorization')
    comment = authorization_comment(authorization)
    require(payload.get('promotion_run_id') == authorization['promotion_run_id']
            and payload.get('promotion_run_attempt') == 1, 'promotion dispatch identity mismatch')
    run = api.get(ROOT + '/actions/runs/' + str(authorization['promotion_run_id']))
    workflow = api.get(ROOT + '/actions/workflows/wordpress-production.yml')
    _repo(run.get('repository'))
    _repo(run.get('head_repository'))
    require(positive(workflow.get('id'))
            and workflow.get('path') == '.github/workflows/wordpress-production.yml'
            and workflow.get('state') == 'active' and run.get('workflow_id') == workflow['id']
            and run.get('path') == workflow['path'] and run.get('event') == 'workflow_dispatch'
            and run.get('head_branch') == 'main' and full_sha(run.get('head_sha'))
            and run.get('id') == authorization['promotion_run_id']
            and run.get('run_attempt') == 1 and run.get('status') == 'in_progress'
            and run.get('conclusion') is None, 'untrusted or reused cutover dispatch')
    start, end = timestamp(authorization['window_start']), timestamp(authorization['window_end'])
    require(start <= timestamp(run.get('created_at')) <= datetime.now(timezone.utc) <= end,
            'cutover dispatch or current time outside approved window')
    operator_ids = []
    for operator in authorization['operators']:
        permission = api.get(ROOT + '/collaborators/' + operator['login'] + '/permission')
        require(permission.get('permission') in ('write', 'admin')
                and permission.get('user', {}).get('id') == operator['id']
                and permission.get('user', {}).get('login') == operator['login']
                and permission.get('user', {}).get('type') == 'User',
                'cutover operator identity or permission mismatch')
        operator_ids.append(operator['id'])
    require(run.get('actor', {}).get('id') in operator_ids
            and run.get('triggering_actor', {}).get('id') in operator_ids,
            'dispatch actors are not approved operators')
    environment = api.get(ROOT + '/environments/' + CUTOVER_ENVIRONMENT)
    require(positive(environment.get('id')) and environment.get('name') == CUTOVER_ENVIRONMENT,
            'configured cutover environment missing')
    policies = [p for p in environment.get('protection_rules', []) if p.get('type') == 'required_reviewers']
    require(len(policies) == 1 and type(policies[0].get('prevent_self_review')) is bool,
            'configured owner review policy required')
    reviewers = policies[0].get('reviewers')
    require(type(reviewers) is list and reviewers, 'configured owner reviewers required')
    owners = []
    for entry in reviewers:
        user = entry.get('reviewer', {})
        require(entry.get('type') == 'User' and user.get('type') == 'User'
                and positive(user.get('id')) and type(user.get('login')) is str,
                'cutover supports explicitly configured human reviewers only')
        owners.append((user['id'], user['login']))
    history = api.get(ROOT + '/actions/runs/' + str(run['id']) + '/approvals')
    require(type(history) is list, 'cutover approval history unavailable')
    relevant = [entry for entry in history if any(
        e.get('id') == environment['id'] and e.get('name') == CUTOVER_ENVIRONMENT
        for e in entry.get('environments', []))]
    require(len(relevant) == 1, 'ambiguous or missing cutover approval history')
    approved = relevant[0]
    owner = approved.get('user', {})
    require(approved.get('state') == 'approved' and owner.get('type') == 'User'
            and (owner.get('id'), owner.get('login')) in owners
            and approved.get('comment') == comment, 'configured owner has not approved this exact cutover')
    if policies[0]['prevent_self_review']:
        require(owner['id'] != run['actor']['id'] and owner['id'] != run['triggering_actor']['id'],
                'configured cutover self-review prevention violated')
    return authorization


def resolve_source(event_payload, api, mode, *, operation='standard'):
    """Return source schema v1, or None for disabled standard operations.

    Source fields: schema_version, operation, mode, event_payload, provenance
    (Task 1/2 nine-field schema), artifact (immutable REST metadata), approval.
    The publisher re-resolves event_payload and compares the resulting object.
    """
    require(operation in ('standard', 'first-cutover'), 'unknown release operation')
    if operation == 'standard' and mode != 'wordpress':
        return None
    try:
        original_event = event_payload
        authorization = None
        if operation == 'first-cutover':
            authorization = _cutover(event_payload, api, mode)
            event_payload = event_payload.get('source_event')
        require(type(event_payload) is dict and event_payload.get('action') == 'completed',
                'completed workflow_run event required')
        _repo(event_payload.get('repository'))
        event_run = event_payload.get('workflow_run', {})
        run_id, attempt, sha = event_run.get('id'), event_run.get('run_attempt'), event_run.get('head_sha')
        require(positive(run_id) and positive(attempt) and full_sha(sha), 'invalid source identifiers')
        _run(event_run, run_id, attempt, sha)
        _repo(api.get(ROOT))
        workflow = api.get(ROOT + '/actions/workflows/' + str(WORKFLOW_ID))
        require(workflow.get('id') == WORKFLOW_ID and workflow.get('path') == WORKFLOW_PATH
                and workflow.get('state') == 'active', 'untrusted source workflow')
        run_path = ROOT + '/actions/runs/' + str(run_id)
        _run(api.get(run_path), run_id, attempt, sha)
        _run(api.get(run_path + '/attempts/' + str(attempt)), run_id, attempt, sha)
        jobs = api.pages(run_path + '/attempts/' + str(attempt) + '/jobs', 'jobs')
        for name in WP_GATES:
            matches = [j for j in jobs if j.get('name') == name]
            require(len(matches) == 1, 'missing or duplicate WordPress gate')
            job = matches[0]
            require(job.get('run_id') == run_id and job.get('run_attempt') == attempt
                    and job.get('head_sha') == sha and job.get('status') == 'completed'
                    and job.get('conclusion') == 'success', 'WordPress gate attempt not successful')
        count, required = _protection(api)
        approval = _approval(api, sha, count)
        _checks(api, sha, required + [(n, 15368) for n in WP_GATES + LEGACY_GATES], run_id)
        name = 'wordpress-release-{0}-{1}-{2}'.format(sha, run_id, attempt)
        artifacts = api.pages(run_path + '/artifacts', 'artifacts')
        selected = [a for a in artifacts if a.get('name') == name]
        require(len(selected) == 1, 'unique exact-attempt release artifact required')
        artifact = selected[0]
        source = artifact.get('workflow_run', {})
        require(positive(artifact.get('id')) and artifact.get('expired') is False
                and positive(artifact.get('size_in_bytes')) and artifact['size_in_bytes'] <= MAX_ZIP_BYTES
                and type(artifact.get('digest')) is str
                and re.fullmatch('sha256:[0-9a-f]{64}', artifact['digest'])
                and source.get('id') == run_id and source.get('repository_id') == REPOSITORY_ID
                and source.get('head_repository_id') == REPOSITORY_ID
                and source.get('head_sha') == sha and source.get('head_branch') == 'main',
                'artifact metadata does not prove exact trusted source')
        if authorization:
            require(authorization['source_run_id'] == run_id
                    and authorization['source_run_attempt'] == attempt and authorization['git_sha'] == sha
                    and authorization['artifact_id'] == artifact['id']
                    and authorization['artifact_digest'] == artifact['digest'],
                    'owner authorization does not bind selected source artifact')
        result = {'schema_version': 1, 'operation': operation, 'mode': mode,
                'event_payload': original_event, 'provenance': {
                    'repository': REPOSITORY, 'git_sha': sha, 'workflow_id': WORKFLOW_ID,
                    'workflow_path': WORKFLOW_PATH, 'run_id': run_id, 'run_attempt': attempt,
                    'event': 'push', 'ref': 'refs/heads/main', 'platform': 'linux/amd64'},
                'artifact': artifact, 'approval': approval}
        if authorization:
            result['authorization'] = authorization
        return result
    except (KeyError, TypeError, AttributeError) as error:
        raise ReleaseValidationError('incomplete GitHub provenance response') from error
