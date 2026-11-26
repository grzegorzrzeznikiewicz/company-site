# Legal page content (GSWEB-32)

Source block markup for the WordPress pages `polityka-prywatnosci` and
`regulamin`. The pages live in the database and stay editable in wp-admin;
these files are the reviewed source of their first published version.

Owner data filled in on 2026-11-26 (GSWEB-32): Gama Software Grzegorz
Rzeźnikiewicz, NIP 8133496665, correspondence kept 12 months, replies within
24 hours. By owner decision no postal address and no registry link are
published. Server log retention is stated as at most 30 days; confirm it
against the production log rotation.

Apply locally first (pages stay drafts until approved):

```bash
for slug in polityka-prywatnosci regulamin; do
  id="$(wordpress/bin/wp eval "echo get_page_by_path('$slug', OBJECT, 'page')->ID;" 2>/dev/null | tail -n 1)"
  wordpress/bin/wp post update "$id" --post_content="$(cat "docs/legal/$slug.html")"
done
```

Production order: publish both pages in wp-admin and set Settings → Privacy to
`Polityka prywatności` first, then release theme 0.4.2 (footer links) and
`gama-contact` 0.3.3 (form notice), so the footer never links to a 404.
