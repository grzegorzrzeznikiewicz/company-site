# OVH routing adapters

These three root-run commands implement the first-cutover routing interface in
`wordpress/release/host_ops.py`. They preserve the existing Nginx site file in
`/srv/gama-wordpress-production/control/routing-<deployment-id>.json` and change
only the root `proxy_pass` from `127.0.0.1:8090` to `127.0.0.1:8000`. The saved
configuration is routing recovery material, not a database or media backup.

Install from a reviewed checkout on the OVH host as root, after confirming
`/etc/nginx/sites-enabled/gama-software.com` resolves to
`/etc/nginx/sites-available/gama-software.com` and that the latter contains one
root-location legacy upstream. Keep the legacy containers and data intact.

```sh
install -d -o root -g root -m 0755 /usr/local/lib/gama-wordpress-routing
install -o root -g root -m 0644 wordpress/routing/ovh.py /usr/local/lib/gama-wordpress-routing/ovh.py
install -o root -g root -m 0755 wordpress/routing/bin/gama-wordpress-legacy-routing /usr/local/sbin/gama-wordpress-legacy-routing
install -o root -g root -m 0755 wordpress/routing/bin/gama-wordpress-cutover /usr/local/sbin/gama-wordpress-cutover
install -o root -g root -m 0755 wordpress/routing/bin/gama-wordpress-rollback-routing /usr/local/sbin/gama-wordpress-rollback-routing
```

The adapters require Python 3.10+, `/usr/bin/docker`, `/usr/sbin/nginx`, and
`/usr/bin/systemctl`. The control directory and its parent, and the Nginx site
file and its parent, must be root-owned, free of symlinks at the checked paths,
and not group/other writable. The saved record and lock are private mode 0600.
Every routing operation also verifies that the root-owned
`/etc/nginx/sites-enabled/gama-software.com` link still points directly to the
reviewed file in `sites-available`; a missing or redirected link is refused.
Install the `legacy_adapter` host configuration value as
`/usr/local/sbin/gama-wordpress-legacy-routing`; the cutover and rollback paths
are fixed in the host release code. The host release transaction invokes the
commands with their bound IDs and immutable image; do not call cutover by hand.

Run local verification with:

```sh
python3 -m unittest wordpress.tests.release.test_ovh_routing -v
python3 -m unittest wordpress.tests.release.test_workflow_boundaries -v
```

On an adapter failure, the release coordinator retains its incident barrier.
If a cutover Nginx validation or reload fails, the adapter restores the saved
legacy configuration and attempts to validate and reload it. A failed restore
reload remains an error requiring operator inspection. Rollback accepts only
the saved deployment ID and the exact expected site state. No adapter stops or
removes legacy resources.
