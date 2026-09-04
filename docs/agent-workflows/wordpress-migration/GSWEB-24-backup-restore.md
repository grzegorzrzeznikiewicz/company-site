# GSWEB-24 — backup and full restore

The backup unit is one immutable directory containing `database.sql`,
`uploads.tar`, `manifest.txt` and `SHA256SUMS`. The manifest records UTC time,
source project, Git commit, WordPress version and database image without
secrets. Files are created with owner-only permissions and checksums are
verified before any restore starts.

Create a backup only into a new absolute destination on storage outside the
production host:

```sh
wordpress/bin/backup /mounted-off-host-backups/gama/2026-09-04T190000Z
```

The infrastructure owner must copy or stream the completed directory to
versioned off-host object storage, enforce encryption and access logging, keep
30 daily and 12 monthly restore points, and alert when the newest successful
backup is older than 24 hours. A local directory on the application host is a
staging location, not a completed production backup.

Restore is deliberately limited to a fresh `gama-restore-*` Compose namespace;
it refuses existing containers/volumes and the live local project. This keeps a
restore drill separate from any code rollback:

```sh
wordpress/bin/restore --project gama-restore-drill-20260904 --confirm \
  /mounted-off-host-backups/gama/2026-09-04T190000Z
```

After the restore, verify the recorded Git artifact, database content, media
hashes, public/admin health, contact mail isolation and the regression suite.
The command prints the exact cleanup command but does not automatically destroy
evidence. Production disaster recovery uses a new replacement namespace and a
traffic switch after verification; it never imports a database over a running
production database. Database rollback requires a separate owner decision
because it can discard legitimate writes made after a code release.

`wordpress/tests/backup-restore-runtime.sh` creates unique content and media,
backs up the running local model, restores both into a fresh namespace, compares
the database identity and media SHA-256, records elapsed time, and then removes
only its labelled drill resources.
