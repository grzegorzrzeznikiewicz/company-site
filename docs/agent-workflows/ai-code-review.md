# Automated AI code review and auto-merge (GSWEB-34)

Every ready (non-draft) owner PR to `main` is reviewed by the
[Open Mercato](https://github.com/open-mercato/skills) `om-auto-review-pr` skill.
An approval merges and deploys the PR; a change request blocks it.

## Flow

1. `.github/workflows/ai-code-review.yml` starts on `opened`, `synchronize`,
   `reopened` and `ready_for_review`. A new push first withdraws any auto-merge
   armed for an earlier head, so no unreviewed code merges.
2. `anthropics/claude-code-action` runs `/om-auto-review-pr <PR>` as the Claude
   GitHub App (`claude[bot]`). The skill uses the vendored `om-code-review`
   engine, the built-in checklist, the repository's `CODE_REVIEW.md`, and the
   validation gate in `.ai/agentic.config.json`. It submits one review:
   **Approve** or **Request changes**. It does not push, merge or label.
3. `wordpress/release/ai_review_gate.py` reads the latest decisive `claude[bot]`
   review on the exact head. With the owner's repository-scoped token it records
   that verdict as the owner's `GAMA-SOLO-AI-REVIEW-V1` COMMENTED review, which
   the production source check already requires (see
   [GSWEB-29 production pipeline](wordpress-migration/GSWEB-29-production-pipeline.md)).
   A missing, stale or ambiguous verdict records nothing and fails the job.
4. On `approved`, the workflow enables squash auto-merge pinned to that head
   (`--match-head-commit`). GitHub merges after the four WordPress quality gates
   pass. The production workflow then deploys, after the `wordpress-production`
   environment approval.
5. On `changes-requested`, the blocking report is recorded, auto-merge stays
   off and the job fails, so the PR shows red. Push fixes to trigger a fresh review.

The merge uses the owner's token, not `GITHUB_TOKEN`. That keeps `merged_by` on
the owner, which `_solo_approval` requires, and lets the `push` to `main`
trigger the quality gates and deployment.

## One-time setup (owner)

- Secret `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`.
- Secret `GAMASOFTWARE_AUTOMERGE_TOKEN`: a fine-grained personal access token limited to
  this repository, with Contents read/write, Pull requests read/write and Metadata read.
- Settings → General → Pull Requests → **Allow auto-merge**.
- The Claude GitHub App must be installed on the repository.

## Updating the skills

The skills are vendored under `.claude/skills` and pinned in `skills-lock.json`.
To update them, run `npx skills update -p` in a PR. That PR is reviewed like any other.
