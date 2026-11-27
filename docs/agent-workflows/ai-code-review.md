# Automated AI code review and merge (GSWEB-34)

Every ready (non-draft) owner PR to `main` is reviewed by the
[Open Mercato](https://github.com/open-mercato/skills) `om-auto-review-pr` skill.
An approval merges and deploys the PR; a change request blocks it.

## Flow

1. **`AI Code Review`** (`.github/workflows/ai-code-review.yml`,
   `pull_request`) holds no owner token.
   - `anthropics/claude-code-action` runs `/om-auto-review-pr <PR>` as the
     Claude GitHub App (`claude[bot]`). It uses the vendored `om-code-review`
     engine, its checklist, `CODE_REVIEW.md`, `.ai/agentic.config.json` and the
     repo-local extension `.ai/skills/om-auto-review-pr/SKILL.md`.
   - Claude gets only Read/Glob/Grep and `gh pr view/diff/checks/review`. It
     cannot run code, use `git`, call `gh api`, comment, push or merge.
   - It submits one review: **Approve** or **Request changes**.
   - A newer push cancels the older run.
2. **`AI Review Gate`** (`.github/workflows/ai-review-gate.yml`,
   `workflow_run`) always runs the definition from `main`. It runs in the
   `ai-merge` environment, whose deployment branch policy admits only `main`;
   that environment is the only place that holds the owner token. It checks out
   `main` and runs `wordpress/release/ai_review_gate.py`, which takes only the
   run id from the event and re-reads everything else from the API:
   - The run must be a successful `pull_request` run of the pinned review
     workflow, for an open owner PR from this repository to `main`, still at
     the same head.
   - **PRs that touch the review machinery are never automated:** `.github/`,
     `.claude/`, `.ai/`, `skills-lock.json`, `CODE_REVIEW.md`, `AGENTS.md`,
     `CLAUDE.md` and `ai_review_gate.py`. Such a PR could change the reviewer,
     its rules or its workflow, so it needs a manual review and a manual owner
     report.
   - The latest decisive `claude[bot]` review on the exact head, submitted
     during this run, is recorded as the owner's `GAMA-SOLO-AI-REVIEW-V1`
     COMMENTED review. That is the proof the production source check requires
     (see [GSWEB-29 production pipeline](wordpress-migration/GSWEB-29-production-pipeline.md)).
   - On `approved`, the gate waits up to 50 minutes for the pinned
     `WordPress Quality Gates` run (`wordpress-ci.yml`, all four jobs green) on
     that head. It then squash-merges with `sha=<reviewed head>`, which GitHub
     enforces at merge time.

A missing, stale, ambiguous or blocking verdict, or a failed gate, means no
merge. A `changes-requested` report also makes the production pipeline refuse a
manual merge of that head.

After a merge, production deploys after the `wordpress-production` environment
approval. The merge uses the owner's token, so `merged_by` is the owner, as
`_solo_approval` requires, and the `push` to `main` triggers the deployment.
GitHub auto-merge is not used.

## Residual risk

- `CLAUDE_CODE_OAUTH_TOKEN` is a repository secret, so a malicious owner-branch
  workflow could read it. That costs usage, not production access.
- A prompt injection in public PR comments could at worst sway the verdict on
  an owner-authored diff. The review prompt treats non-owner comments as
  untrusted data.

## One-time setup (owner)

- Repository secret `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`), or `ANTHROPIC_API_KEY`.
- Environment **`ai-merge`** (Settings → Environments). Deployment branches:
  *Selected branches*, only `main`. Environment secret
  `GAMASOFTWARE_AUTOMERGE_TOKEN`: a fine-grained PAT limited to this repository,
  with Contents read/write, Pull requests read/write and Metadata read. Remove
  any repository-level copy of that secret.
- The Claude GitHub App installed on the repository.

## Updating the skills

The skills are vendored under `.claude/skills` and pinned in `skills-lock.json`.
To update them, run `npx skills update -p` in a PR. That PR touches the review
machinery, so it is reviewed and merged manually.
