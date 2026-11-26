# WordPress workspace

This self-contained area holds the pinned local runtime, the production-ready
`gama-software` block-theme foundation, independently installable first-party
plugins, external-extension lock, package tools, and contract tests.

The complete GSWEB-11 boundary decision and next-plugin procedure are in
[`GSWEB-11-architecture.md`](../docs/agent-workflows/wordpress-migration/GSWEB-11-architecture.md).
The GSWEB-12 Gate A decision and its immutable QA inputs are in
[`GSWEB-12-gate-a.md`](../docs/agent-workflows/wordpress-migration/GSWEB-12-gate-a.md).

```sh
wordpress/bin/start
wordpress/bin/validate-extensions-lock
wordpress/tests/seo-plugin-contract.sh
wordpress/tests/seo-runtime.sh
wordpress/bin/package plugin gama-contact
wordpress/tests/plugin-package-contract.sh
wordpress/tests/package-compose-contract.sh
wordpress/tests/test-package-input-contract.sh
wordpress/tests/test-package-isolation-contract.sh
wordpress/tests/ci-package-input-contract.sh
wordpress/bin/test-package wordpress/dist/gama-contact-0.3.3.zip

wordpress/bin/package theme gama-software
wordpress/tests/theme-contract.sh
wordpress/bin/test-package wordpress/dist/gama-software-0.4.2.zip
```

External extensions are never committed. Site Kit by Google, Complianz and
WP Consent API (GSWEB-31) are pinned by version and SHA-256 in
`config/extensions.lock.json`. The production image downloads and verifies them
in `runtime/Dockerfile`; `bin/start` runs `bin/fetch-extensions`, which reads the
lock and verifies the same archives into the ignored `.cache/extensions/<slug>`
that Compose mounts read-only. `tests/external-extensions-contract.sh` keeps the
pins in sync. Connecting a Google account and completing the Complianz wizard
(cookie policy, consent categories) are owner actions in wp-admin and are not
automated; Complianz writes its generated files under `wp-content/uploads/complianz`.
An ordinary production release does not run the bootstrap, so the owner activates
the plugins in wp-admin after the first release that ships them: see the
[GSWEB-31 runbook](../docs/agent-workflows/wordpress-migration/GSWEB-31-external-extensions.md).

`wordpress/dist` contains ignored local artifacts only. Do not upload, release,
attach, or distribute them without separate owner approval.
