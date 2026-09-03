# Gama Software theme

`gama-software` is the production block-theme foundation for the Gama Software
website. Version 0.2.0 targets WordPress 7.1 and PHP 8.4. Its controlled Global
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

License: GPL-2.0-or-later.
