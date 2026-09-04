# Gate B — editable migrated site

## Decision

- **Verdict: GO**
- Date and reviewed branch: 2026-09-04, `feature/GSWEB-9`
- Environment: isolated local WordPress at `http://localhost:8090`
- Owner decision: the owner explicitly accepted the current result and asked to
  continue the epic through completion.

## Evidence

- Desktop/mobile source and browser contracts cover the header, native menu,
  footer, Hero CTA, services, modules, blog and contact sections against the
  approved GSWEB-9 inventory.
- Content assembly removes the default WordPress post, imports the exact logo,
  preserves Editor-selected logo changes across bootstrap and leaves legal
  pages as unpublished drafts.
- Navigation links resolve to working sections/routes; the contact form performs
  accessible browser validation, verified delivery to Mailpit and generic
  transport-error handling.
- The contact limiter uses MariaDB advisory locking. A handshake-controlled
  exclusion test and a 12-request runtime test prove exactly five accepted
  validation attempts followed by seven HTTP 429 responses.
- The independently reviewed Gate B blockers were fixed in `ea643ec`; the
  re-review verdict is **APPROVE** with no P0/P1 finding. The timing-sensitive
  test observation was removed by replacing the fixed sleep with an explicit
  release handshake.
- Reproducible theme 0.4.0 and contact 0.3.1 packages pass source contracts,
  checksums and clean ZIP lifecycle tests. Playwright verifies the active form
  and requires HTML plus `.last-run.json` artifacts.

## Accepted follow-up scope

Gate B validates the content model and public result. GSWEB-28 still owns the
complete rehearsal of Editor and Administrator journeys on the immutable
staging artifact, including persistence after logout/restart. This is an
additional release gate, not a missing public-site feature.

## Rollback point

The legacy React/Symfony deployment and all of its workflows remain untouched.
No production traffic has moved, so the operational rollback point is still the
current production release documented in GSWEB-9.
