# GSWEB-26 — immutable deployment and rollback

The release unit is the image built by `wordpress/runtime/Dockerfile`. It pins
WordPress 7.1/PHP 8.4 and WP-CLI by digest and embeds the reviewed theme,
first-party plugins, bootstrap and a release revision label. The CI registry
reference is `ghcr.io/<owner>/gama-wordpress:sha-<full-commit>@sha256:<digest>`.
That exact digest—not a moving tag—is promoted from staging to production.

`wordpress/deploy/compose.yaml` has three named persistence boundaries: database,
uploads and the installed core. Before each code deployment, the one-shot
installer replaces only the core volume from the selected image while the
application is stopped. Database and uploads are never removed or implicitly
rolled back. The bootstrap is idempotent and preserves valid Editor changes.

The manual `WordPress Staging Deployment` workflow builds one image only after
the selected commit has a successful WordPress Quality Gates run, and deploys
it to the isolated `gama-wp-staging` namespace. Its protected GitHub
environment and server `.env` own staging credentials. Staging activates the
SMTP sink, uses only `example.test` recipients, and publishes `noindex`. The
workflow performs no production action. After its health check it publishes a
run-bound release-evidence artifact containing the exact SHA and digest.
Production promotion belongs to the separately gated GSWEB-29 workflow after a
fresh Gate C decision and explicit deployment-window approval; see
`GSWEB-29-production-pipeline.md`.

Local release and rollback rehearsal:

```sh
wordpress/bin/build-release
wordpress/bin/deploy-staging --project gama-wp-staging-drill \
  --env-file /absolute/path/staging.env --confirm
wordpress/bin/rollback-staging --project gama-wp-staging-drill \
  --env-file /absolute/path/previous-image.env --confirm
```

The env file must contain an immutable registry digest (or local image ID for a
drill). The reverse proxy example enforces the apex canonical host, HTTP→HTTPS,
and `X-Forwarded-Proto`. Before using it, infrastructure ownership must confirm
certificate paths and that port 8080 and the selected Docker/project resources
are not shared with another workload.

`wordpress/tests/staging-rollback-runtime.sh` deploys a base image, creates
database content and media, deploys a distinct candidate image, verifies
health/noindex/sink mail and persistence, then rolls code back to the exact base
image and verifies the same data again. This is code rollback evidence; database
recovery remains the separate GSWEB-24 procedure.
