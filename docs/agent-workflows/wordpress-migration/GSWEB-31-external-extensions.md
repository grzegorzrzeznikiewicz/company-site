# GSWEB-31 — external plugins: Site Kit, Complianz, WP Consent API

| Plugin | Version | Purpose |
| --- | --- | --- |
| `google-site-kit` | 1.192.0 | Official Google plugin: Analytics 4, Search Console, PageSpeed Insights |
| `complianz-gdpr` | 7.5.9 | Cookie consent banner, cookie policy, Google Consent Mode signals |
| `wp-consent-api` | 2.1.0 | Consent bridge that Site Kit Consent Mode reads (`wp_set_consent`) |

The pins (version, source, SHA-256) live in `wordpress/config/extensions.lock.json`.
The image downloads every archive with `ADD --checksum` in
`wordpress/runtime/Dockerfile`, and local development verifies the same archives
with `wordpress/bin/fetch-extensions`. `wordpress/tests/external-extensions-contract.sh`
keeps those places in sync. The plugin code is never committed.

## Activation: bootstrap vs. an ordinary production release

`wordpress/bin/bootstrap` activates the three plugins. That covers local
development, CI and the first production cutover. **An ordinary production
release does not run the bootstrap.** As the
[production pipeline](GSWEB-29-production-pipeline.md) says, it replaces only
code. After the first release that contains these plugins they are therefore
installed in production but **inactive** until the owner activates them.
Activating them is a database change, so it stays an explicit owner action.

## Owner runbook after the release is deployed

All steps are in production wp-admin, as an Administrator. `DISALLOW_FILE_MODS`
blocks installing, updating and deleting plugins, not activating them.

1. **Plugins:** activate **WP Consent API**, then **Complianz | GDPR/CCPA Cookie
   Consent**, then **Site Kit by Google**. Install, update and delete links are
   absent by design.
2. **Complianz wizard:** choose region EU (GDPR), select statistics via Google
   Analytics through Site Kit, enable Google Consent Mode, and generate and
   publish the cookie policy. Complianz writes its generated files under
   `wp-content/uploads/complianz`, which is the persistent uploads volume. The
   banner appears only after the wizard is completed. Skip the optional
   external website scan unless you accept sending the site URL to Complianz.
3. **Site Kit:** "Sign in with Google" with the account that owns the GA4
   property. Connect Search Console and Analytics, then enable Consent Mode in
   Site Kit settings; it detects WP Consent API as already installed.
4. **Check:** in a private window, the banner shows. With statistics refused,
   no `google-analytics.com/g/collect` requests are sent. With them accepted,
   they are sent.

## Rollback

Rolling back to an image without these plugins leaves their options in the
database, and WordPress deactivates the missing plugins. Rolling forward again
needs step 1 again; the wizard and Site Kit settings are kept.
