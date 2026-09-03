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
wordpress/bin/package plugin gama-contact
wordpress/tests/plugin-package-contract.sh
wordpress/tests/package-compose-contract.sh
wordpress/tests/test-package-input-contract.sh
wordpress/tests/test-package-isolation-contract.sh
wordpress/bin/test-package wordpress/dist/gama-contact-0.1.0.zip

wordpress/bin/package theme gama-software
wordpress/tests/theme-contract.sh
wordpress/bin/test-package wordpress/dist/gama-software-0.3.0.zip
```

`wordpress/dist` contains ignored local artifacts only. Do not upload, release,
attach, or distribute them without separate owner approval.
