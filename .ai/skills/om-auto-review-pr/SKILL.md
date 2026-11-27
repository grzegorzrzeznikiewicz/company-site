# Repo-local extension: om-auto-review-pr in the `AI Code Review` workflow

This repository runs `om-auto-review-pr` unattended in GitHub Actions
(`.github/workflows/ai-code-review.yml`), with read-only tools. These specifics
apply on top of the skill. They change only coordination and reporting, never
the review method, the checklists, the severity scale or the verdict rule.

- **Claim (step 1, step 12):** ownership is provided by the workflow's
  per-PR `concurrency` group, which cancels older runs. Do not call
  get-lock/acquire-lock/release-lock and do not post claim or completion
  comments. The tools for them are not available in this run.
- **Labels (step 10):** `labels.enabled` is `false`; skip all label work.
- **Comments:** post nothing except the single review in step 10. The handoff,
  label-rationale, manual-QA and CI-result comments are skipped. Put anything
  the author needs into the review body.
- **Worktree (step 5):** the CI checkout is a disposable worktree at the PR
  head. Review it in place, without creating another one.
- **Validation (step 8):** run `validation.commands` only when the available
  tools allow it. Otherwise list them as not run in the report. The WordPress
  quality gates run as separate required checks and are verified before any merge.
- **Autofix (step 11):** never. This run cannot push.
- **CI follow-up (step 13):** skipped (`ci.maxWaitMinutes` is `0`).
- **Verdict (step 10):** submit exactly one review on the head with
  `gh pr review --approve --body "..."` or `gh pr review --request-changes --body "..."`.
