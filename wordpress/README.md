# WordPress workspace

This self-contained area holds the pinned local runtime, the current
`gama-software` runtime theme scaffold, independently installable first-party
plugins, external-extension lock, package tools, and contract tests.

The complete GSWEB-11 boundary decision and next-plugin procedure are in
[`GSWEB-11-architecture.md`](../docs/agent-workflows/wordpress-migration/GSWEB-11-architecture.md).
The current theme is not a production package; GSWEB-12 owns that work.

```sh
wordpress/bin/start
wordpress/bin/validate-extensions-lock
wordpress/bin/package plugin gama-contact
wordpress/tests/plugin-package-contract.sh
wordpress/tests/package-compose-contract.sh
wordpress/tests/test-package-input-contract.sh
wordpress/tests/test-package-isolation-contract.sh
wordpress/bin/test-package wordpress/dist/gama-contact-0.1.0.zip
```

`wordpress/dist` contains ignored local artifacts only. Do not upload, release,
attach, or distribute them without separate owner approval.
