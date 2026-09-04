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

License: GPL-2.0-or-later.
