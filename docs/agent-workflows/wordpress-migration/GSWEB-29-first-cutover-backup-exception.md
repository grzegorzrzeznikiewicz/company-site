# GSWEB-29 — one first-cutover backup exception

## Owner decision (2026-09-27)

The owner explicitly approved deployment without a data backup, then approved
limiting this exception to the first WordPress cutover. The legacy application
must remain intact and traffic must remain reversible. This supersedes the
off-host backup requirement **only for that exact first-cutover operation**.
It does not approve deleting legacy data, disabling HTTPS checks, or skipping
CI, source provenance, SMTP/content checks, or the owner cutover gate.

There is no guaranteed data recovery without a backup. Preserving the old
application and its routing is not a database/upload backup and must not be
reported as one. Future standard releases still require the original backup
and restore evidence; automatic updates will refuse until it is configured.

## Protected host configuration

The root-owned host configuration may contain `first_cutover_without_backup`:

```json
{
  "operation_id": "EXACT_CUTOVER_OPERATION_ID",
  "git_sha": "EXACT_MAIN_COMMIT_SHA",
  "image": "EXACT_IMMUTABLE_IMAGE_REFERENCE",
  "authorization_ref": "EXACT_OWNER_AUTHORIZATION_ID",
  "accept_data_loss_without_backup": true
}
```

The values above are descriptive placeholders, not deployable configuration.
They must match the CI-verified request and the approved cutover window. The
record is rejected for any other release identity. The host still refuses an
existing or partial WordPress installation. Do not populate a backup reference
or checksum for a skipped backup.

The durable operation journal records `backup: null`, `backup_waiver`, and its
authorization reference. Neither legacy nor newly bootstrapped WordPress data
is backed up on this exception path. Normal releases do not use the exception.

## Routing-only adapter contract

Before deployment the protected `legacy_adapter` receives `prepare-routing`.
It must inspect and preserve the legacy routing target without stopping,
deleting, or modifying the legacy application/data. `verify-routing` must
verify the restored legacy target. Both receive JSON with `operation_id`,
`git_sha`, `image`, and `deployment_operation_id` (the original cutover ID
during rollback). They return exactly:

```json
{
  "binding_sha256": "SHA256_OF_CANONICAL_INPUT_JSON",
  "routing_recovery_reference": "PERSISTENT_ROUTING_RECORD_REFERENCE"
}
```

Canonical JSON uses sorted keys and compact separators. The adapter must
return success only after its actual routing checks succeed. This contract is
not off-host backup evidence and has no encryption or restore claim. Existing
backup-backed operations retain the original evidence contract. Keep the
exception configuration until any authorized routing recovery is complete.

The fixed cutover and rollback executables remain mandatory. WordPress binds
only `127.0.0.1:8000`; existing Magento port 8080 and legacy site port 8090 are
not modified. The public address remains `https://gama-software.com`.

## Verification and operational status

Tests cover no backup calls or false backup records, exact release binding,
rejection for standard updates, automatic return to legacy on failure, manual
routing recovery, and routing-only adapter evidence. This document records
approval and implementation requirements, **not a completed deployment**.
