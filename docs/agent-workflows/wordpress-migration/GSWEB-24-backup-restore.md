# GSWEB-24 — backup and full restore

The backup unit is one immutable directory containing `database.sql`,
`uploads.tar`, `manifest.txt` and `SHA256SUMS`. The manifest records UTC time,
source project, Git commit, the exact WordPress image ID and revision,
WordPress version and database image without secrets. The command discovers
database and uploads from the explicitly named running Compose project rather
than assuming the local development model. Files are created with owner-only
permissions and checksums are verified before any restore starts.

Create a backup only into a new absolute destination on storage outside the
production host:

```sh
wordpress/bin/backup --project gama-wp-production \
  /mounted-off-host-backups/gama/2026-09-04T190000Z
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
wordpress/bin/restore --project gama-restore-drill-20260904 \
  --env-file /run/secrets/gama-wordpress-production.env --confirm \
  /mounted-off-host-backups/gama/2026-09-04T190000Z
```

The deployment env must select the same immutable image recorded in the backup;
restore refuses a mismatch and seeds a fresh Core volume from that exact image.
After the restore, verify the recorded Git artifact, database content, media
hashes, public/admin health, contact mail isolation and the regression suite.
The command prints the exact cleanup command but does not automatically destroy
evidence. Production disaster recovery uses a new replacement namespace and a
traffic switch after verification; it never imports a database over a running
production database. Database rollback requires a separate owner decision
because it can discard legitimate writes made after a code release.

`wordpress/tests/backup-restore-runtime.sh` deploys a unique immutable staging
namespace, creates unique content and media, backs up that deployment model,
restores database and uploads with the exact image into a fresh namespace,
compares the image, database identity and media SHA-256, records elapsed time,
and then removes only its labelled source and drill resources.
