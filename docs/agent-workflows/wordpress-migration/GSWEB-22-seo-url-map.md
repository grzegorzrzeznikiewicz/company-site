# GSWEB-22 SEO and URL map

## Canonical policy

- The canonical production origin is `https://gama-software.com` (apex, no
  `www`). This records the working owner decision from the accepted baseline;
  the proxy implementation belongs to GSWEB-26.
- HTTP and `www` must reach the canonical HTTPS URL in one `301` response.
- Non-production WordPress environments publish `noindex, nofollow,
  noarchive`; only `WP_ENVIRONMENT_TYPE=production` publishes `index, follow`.
- WordPress Core is the only XML sitemap source. `/sitemap.xml` returns one
  `301` to `/wp-sitemap.xml` for compatibility.

## Public URL mapping

| Legacy URL | WordPress target | Rule |
| --- | --- | --- |
| `/` and `/#home` | `/` and `/#home` | unchanged |
| `/#services` | `/#services` | unchanged fragment |
| `/#modules` | `/#modules` | unchanged fragment |
| `/#blog` | `/#blog`, with archive at `/blog/` | homepage fragment retained; native archive added |
| `/#contact` | `/#contact` | unchanged fragment |
| `/robots.txt` | `/robots.txt` | valid environment-aware plain text replaces SPA fallback |
| `/sitemap.xml` | `/wp-sitemap.xml` | one `301` |
| unknown paths | native 404 template | real `404`, no soft fallback |
| `/wp-admin/`, `/wp-login.php` | native WordPress administration | canonical administration entry points |

The former `/admin` SPA fallback and `/api/contact` Symfony endpoint were not
working public content URLs and have no confirmed external consumer. They are
therefore not redirected. The new contact form uses the first-party WordPress
REST route owned by `gama-contact`.

The legal pages remain drafts and are intentionally absent from public
navigation and sitemaps until the owner supplies and approves their content.
