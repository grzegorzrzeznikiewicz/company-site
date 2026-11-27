# Automated AI code review and merge (GSWEB-34)

Every ready (non-draft) owner PR to `main` is reviewed by the
[Open Mercato](https://github.com/open-mercato/skills) `om-auto-review-pr` skill.
An approval merges and deploys the PR; a change request blocks it.

## Flow

`.github/workflows/ai-code-review.yml` starts on `opened`, `synchronize`,
`reopened` and `ready_for_review`. A newer push cancels the older run.

1. **`review` job (no owner token).** `anthropics/claude-code-action` runs
   `/om-auto-review-pr <PR>` as the Claude GitHub App (`claude[bot]`), using the
   vendored `om-code-review` engine, its built-in checklist, `CODE_REVIEW.md` and
   `.ai/agentic.config.json`. Its tools are limited to reading the code,
   read-only `git` subcommands and `gh pr view/diff/checks/review/comment`. It
   cannot run repository code, call `gh api`, push or merge. It submits one review:
   **Approve** or **Request changes**.
2. **`gate` job (owner token, trusted code only).** This job checks out `main`
   and never the PR head. It runs `wordpress/release/ai_review_gate.py`, which:
   - takes the latest decisive `claude[bot]` review on the exact head, submitted
     after this run started;
   - records it as the owner's `GAMA-SOLO-AI-REVIEW-V1` COMMENTED review, the
     proof the production source check requires (see
     [GSWEB-29 production pipeline](wordpress-migration/GSWEB-29-production-pipeline.md));
   - on `approved`, waits up to 50 minutes for the four WordPress quality gates
     on that head, then squash-merges with `sha=<reviewed head>`, which GitHub
     enforces at merge time.

A missing, stale, ambiguous or blocking verdict, or a failed gate, means no
merge, and the job fails. A `changes-requested` report also makes the
production pipeline refuse a manual merge of that head. After a merge, the
production workflow deploys, subject to the `wordpress-production` environment
approval.

The merge uses the owner's token, not `GITHUB_TOKEN`. That keeps `merged_by` on
the owner, which `_solo_approval` requires, and lets the `push` to `main`
trigger the quality gates and the deployment. GitHub auto-merge is not used, so
an approval cannot carry over to a newer head.

Changes to `ai_review_gate.py` take effect only after they reach `main`. The PR
that changes the workflow itself cannot be reviewed by the action, because
claude-code-action requires the workflow file to match the default branch. That
PR needs a manual owner report.

## One-time setup (owner)

- Secret `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`), or `ANTHROPIC_API_KEY`.
- Secret `GAMASOFTWARE_AUTOMERGE_TOKEN`: a fine-grained personal access token
  limited to this repository, with Contents read/write, Pull requests read/write
  and Metadata read.
- The Claude GitHub App installed on the repository.

## Updating the skills

The skills are vendored under `.claude/skills` and pinned in `skills-lock.json`.
To update them, run `npx skills update -p` in a PR. That PR is reviewed like any other.
