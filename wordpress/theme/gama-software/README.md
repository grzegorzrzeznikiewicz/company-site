# Gama Software theme

`gama-software` is the production block-theme foundation for the Gama Software
website. Version 0.4.1 targets WordPress 7.1 and PHP 8.4. Its controlled Global
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

## Local and disposable activation

The repository's local runtime mounts the theme source read-only and
`wordpress/bin/start` activates `gama-software` idempotently. Do not install a
ZIP over that source-mounted directory. Verify the local state with:

```sh
wordpress/bin/wp theme is-active gama-software
wordpress/bin/wp theme get gama-software --field=version
```

To exercise the actual package without the owner's port-8090 preview, build it
and run the unique-namespace lifecycle. The lifecycle uses a disposable
no-host-port Compose project and removes its containers, volumes, network and
local image after collecting test artifacts:

```sh
wordpress/bin/package theme gama-software
wordpress/bin/test-package wordpress/dist/gama-software-0.4.1.zip
```

For a separate disposable WordPress installation where the built ZIP is
available to WP-CLI, install, activate and verify it with:

```sh
wp theme install /absolute/path/to/gama-software-0.4.1.zip
wp theme activate gama-software
wp theme is-active gama-software
wp theme get gama-software --field=version
```

Do not use those standalone commands to write into production or the
repository's read-only Compose mounts.

## Reverting one saved template or template part

When an editor saves a theme template or template part, WordPress forks that
target into a `wp_template` or `wp_template_part` database record. The saved
database override takes precedence over the matching file in the active theme.
Consequently, installing a newer theme ZIP updates the theme file but does not
overwrite that target's saved customization; the override continues to render.

Revert only an exact target whose saved customization the owner has approved
discarding:

1. Record whether the target is a template or template part and its exact name.
   Back it up with the environment's approved WordPress export/backup process,
   and confirm the backup can restore that exact target.
2. Obtain explicit owner confirmation for that named target. Reverting discards
   its saved database customization and reveals the current theme-file version.
3. In **Appearance → Editor**, open the exact item under **Design → Templates**
   or, for Header/Footer template parts, **Design → Patterns → Manage my
   patterns**.
4. With that target open, use the Settings sidebar's **Template → Actions →
   Reset** action and confirm the reset. Labels can vary by WordPress version or
   interface language. If the targeted Reset action is unavailable, stop and
   verify that the item is a custom override backed by a theme file; do not
   substitute SQL or bulk deletion.
5. Reopen the named target and its affected public route to verify the current
   file-backed design is visible.

This targeted Site Editor reset removes only the selected template or
template-part override. It preserves other templates and parts, pages, posts,
media, navigation entities and Global Styles. It is fundamentally different
from `wordpress/bin/reset --confirm`, which destroys the local Compose
database, uploads and Core volumes, and from the destructive clean-runtime
smoke mode. Never use either all-site reset on the owner's preview. The
repository's `wordpress/tests/reset-theme-overrides.php` helper is destructive,
test-only and guarded for generated disposable theme-package namespaces; it is
not an operator procedure and must never be run against the preview. Do not use
blanket SQL, direct `wp_template`/`wp_template_part` post deletion, bootstrap,
or an all-site reset to revert an editor target.

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

## Editing the homepage Hero

The **Gama Software Hero** pattern is included at the start of the Front Page
template. In **Appearance → Editor → Templates → Front Page**, select the Hero
section to change its H1, lead text, button label or button destination; use a
global homepage anchor such as `/#services` or a complete URL. The outer Core
Group deliberately remains unlocked, so an editor can also set an optional
background image with the standard block controls. Do not add a second H1 to
the page content.

## Editing homepage services

The three service cards in **Appearance → Editor → Templates → Front Page** are
direct, unlocked Core blocks, so their structure can be changed immediately.
Select a card to edit its image, H3 or description. The supplied icons are
decorative and intentionally have empty alternative text; if an image adds
information, provide a useful alternative text instead. To add an optional card
link, insert a standard Button or linked paragraph inside that card.

Open **List View** in the Site Editor to manage cards without code: select a
`gama-service-card`, use **Duplicate** to add cards, drag it to reorder, or use
the block menu to remove it. Keep cards directly inside the services Grid Group;
that native Grid automatically reflows from up to three columns to one column
when the available width is too narrow. Check the result at desktop and mobile
widths, and tab through any links to confirm the visible focus outline.

The separately available **Gama Software Services** pattern is a starter for a
new page or template. If WordPress presents that inserted pattern as linked,
choose **Detach** from its block menu before making structural changes; the
homepage cards do not require this step.

## Editing homepage modules

The **Moduły Magento 2** section follows Services in the Front Page template.
Its six starter cards are direct, unlocked Core Group, Heading, Image, List and
List Item blocks. In List View, duplicate, remove or drag a
`gama-module-card` inside the `gama-modules__grid` Group. Card titles,
descriptions, icons and every feature remain editable without a deployment.
Insert a Core Button inside a card when that module needs its own link.

The final availability note and **Zapisz się na listę oczekujących** button are
kept in the removable `gama-modules__action` Group. Its accepted initial target
is `/#contact`. Editors may change the text or destination, or remove the whole
Group. The separately available **Gama Software Modules** pattern provides the
same starter content for another template; it is not a runtime data store or a
fixed React/PHP card array on the homepage.

Keep the Core-block model while modules only need a flexible marketing grid.
Introduce a plugin-owned custom post type only after the product requires
filtering, module detail pages or reuse across multiple independently queried
views. That change needs its own Jira task and migration test so content remains
available after switching themes.

## Editing the blog

WordPress posts are the single source of truth for the blog. Create, preview,
schedule and publish them in **Posts**; the newest published articles appear in
the editable Blog Query block on the homepage and all articles appear at
`/blog/`. The archive and homepage use responsive Core Query grids, while the
Single template owns article metadata, featured image and previous/next links.

Set a featured image, excerpt and category for a useful card. The **Gama
Software Article** pattern provides an optional lead, section heading and quote
starter without locking the post. When no article is published, both query
locations display the intentional **W budowie** state instead of an empty or
broken grid. Draft, private and future-scheduled posts are never public.

## Editing the Contact section

The Contact section is made from direct, unlocked Core blocks in the Front Page
template. Its centered 42rem card preserves the original site layout: name and
e-mail share a row from 768px, while phone and message span the form width.
Editors can change the heading and fallback e-mail link, and move or replace
the entire form slot. The separate **Gama Software Contact** pattern provides
the same starter structure; there is no additional promotional text column.

The `gama-contact__form-slot` Group is the stable presentation boundary for a
theme-independent form block. Before the form plugin is active it displays a
visitor-facing availability message with a working `mailto:` link. That fallback
is hidden when the form is present. Form processing, validation and anti-spam
never belong in the theme.

License: GPL-2.0-or-later.
