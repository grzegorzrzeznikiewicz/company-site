# Gama Software theme

`gama-software` is the production block-theme foundation for the Gama Software
website. Version 0.3.0 targets WordPress 7.1 and PHP 8.4. Its controlled Global
Styles palette, system typography, spacing, radii and shadows reproduce the
approved visual foundation without Tailwind, React or remote fonts.

The responsive contract starts with 1rem root padding, increases it to 1.5rem
at 768px and to 2rem at 1024px, and preserves visible keyboard focus and media
reflow down to 320 CSS pixels. All editor-facing design choices come from
`theme.json`; `style.css` contains only the shared responsive, focus, media and
line-height exceptions that WordPress 7.1 cannot express as stable Global
Styles settings.

The theme owns presentation and editor policy only. Business behavior belongs
in independent plugins. Build the deterministic distribution artifact with:

```sh
wordpress/bin/package theme gama-software
```

## Editing the header, menus and footer

In WordPress, open **Appearance → Editor**. Use **Design → Navigation** to
rename, reorder, add, remove or nest items in the primary menu. To edit the
whole shell, use **Design → Patterns → Manage my patterns**, open the Header or
Footer template part, then select its Navigation block. After an edit, choose
**Save** and confirm every changed Navigation and template-part entity shown in
the final save panel. Check the public homepage, a page, a post, `/blog/` and a
missing URL after saving.

Links to sections of the homepage must use the global `/#anchor` form, for
example `/#services`; a bare `#services` is wrong when the menu is rendered on
a page, post or 404. The initial footer intentionally contains only the real
Contact link. Do not add Privacy Policy or Terms links until their legal text
has been approved and the corresponding pages have been published with real
public URLs in GSWEB-21.

License: GPL-2.0-or-later.
