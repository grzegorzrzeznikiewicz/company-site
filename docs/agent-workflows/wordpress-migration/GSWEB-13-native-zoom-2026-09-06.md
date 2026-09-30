# GSWEB-13 — current-package native Chrome 200% checkpoint

Date: 2026-09-06. This replaces only the stale native-zoom checkpoint for theme
0.2.0; it is not whole-epic, public-staging, Safari, screen-reader or owner visual
acceptance.

## Exact target and isolation

- Published source: `1398f41dbcb39a627ff554c1cf96c801f5f6e552` on
  `feature/GSWEB-9`; no application change was made for this test.
- WordPress 7.1, theme `gama-software` 0.4.1, contact plugin 0.3.2, installed
  through WP-CLI from the current local ZIPs, not theme source mounts.
- Theme ZIP SHA-256:
  `67caf7865fb19b0acdcef21e626c28116725eb55c52511501d6c6ee808747bef`.
- Contact ZIP SHA-256:
  `7b150f168fce6053910d87ca81592c1175a9129e1b49ef6162fc13361ceb6b7e`.
- Google Chrome 152.0.7977.76, Gama Software profile, macOS 26.6.2 (25G83).
- Disposable namespace `gama-gsweb13-native-20260906-r2strd`, URL
  `http://127.0.0.1:18096/`. Separate database/Core/uploads; no preview reset.

The existing ZIP-test Compose network is internal. Its initial host connection
failed despite the configured port; inspection showed empty runtime port
bindings. A temporary second network was attached only to this fixture's web
service, leaving its database on the internal network. The host binding then
reported `127.0.0.1:18096 -> 80` and HTTP 200. This local override was not applied
to repository Compose files, staging or production.

CI 34027935198 uses a fixed package timestamp rather than the package-source
commit timestamp: its theme ZIP is
`2a921df6330cc45b2f53eaaf044b71c70ea7bf647cc1b1f601c5f83679fd238b`, and
contact ZIP is `d0800517e14e399f0b603ad3077f64e01c95346d34ebaac62ef889c590db46d7`.
Every entry name and payload byte was compared and matched the local ZIPs;
archive timestamps differ. Native evidence identifies the local ZIP hashes
above, not a byte-identical CI archive.

## Observed result

Chrome was changed with its native zoom shortcuts. Its UI explicitly reported
200%; no CSS zoom, viewport emulation or page-scale command was used.

| View                                              | Outer width | Inner width | DPR | Visual viewport scale | Horizontal overflow |
| ------------------------------------------------- | ----------: | ----------: | --: | --------------------: | ------------------: |
| Initial front, 100%                               |         960 |         960 |   1 |                     1 |                   0 |
| Front, native 200%                                |         960 |         480 |   2 |                     1 |                   0 |
| Site Editor shell, narrow native 200%             |         960 |         480 |   2 |                     1 |                   0 |
| Site Editor shell, enlarged window at native 200% |        1920 |         960 |   2 |                     1 |                   0 |

At the enlarged editor size the canvas client, scroll and body widths were all
680 px: no horizontal overflow. The window resize used the native window
control and did not change the 200% zoom setting.

- Front: logo and navigation remained available, hero text wrapped and its CTA
  remained visible. The full section headings and content were present in the
  accessibility tree; the document had no horizontal overflow.
- Keyboard: Tab reached the skip link, logo and menu toggle. Enter opened the
  menu; Tab traversed its links and Enter on Kontakt reached `/#contact`.
- Contact: the fields and submit control were reachable. The submit control's
  visible focus outline is retained in the screenshot. Blank submission focused
  `gama-contact-name` and kept the page at `/#contact`; no valid message was sent.
  This is a zoom/validation check, not a new SMTP-delivery acceptance.
- Editor: Front Page opened, Global Styles → Colors → Edit palette was usable,
  and all eleven shipped theme colors were exposed. Tab and Shift+Tab reached
  the color tab, palette options, Base swatch and Add color. The focused swatch
  and control outlines were visually inspected. No template/style change was
  saved; Save stayed disabled.
- The connected tab reported no console errors. The fixture PHP log contained
  one line and no Fatal/Parse/Deprecated/theme/plugin-matching diagnostic.

A Chrome password-save prompt was declined; no test password was saved. The
clear editor screenshot, rather than the earlier obstructed capture, is the
visual evidence used here.

## Evidence and cleanup

Evidence is retained locally in `/tmp/gama-native-1398f41.r2strd/`. JPEG screenshots
include browser UI and are not published as repository assets or uploaded to Jira.

| Artifact                       | SHA-256                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `observations.json`            | `b17af14df8aad21d2f1d562a9ccbbebfa5af19333a64195c615bd3431e0af7b5` |
| `front-native-200.jpg`         | `4aecf05cbee4feb12292209586ef292e17831d418e034bab7ed85087a9eed8a6` |
| `contact-native-200.jpg`       | `e3e167f8bec8edaf13461e94179a770c6d735e1c74fd14f72e7c0335d06b7bd7` |
| `editor-native-200-clear.jpg`  | `f91c819a3ec5e5f0795fb036f5e8fcfcc8bab56de95ac41ef0ea1253eb61f3f6` |
| `editor-palette-focus-200.jpg` | `c00d90ba9e0b4c1a2f8e3f6ba6005031d6ee6454534ed451f48c8d58da6689fa` |

Chrome was restored to 100% (`1920/1920`, DPR 1), then its previous 960 px
window width was restored (`960/960`, DPR 1). The test tab was closed.
`cleanup.sh` removed only the named fixture's containers, Core/database/uploads
volumes and its two networks. Exact-label absence checks passed. These disposable
test data were deleted; the environment can be recreated from the retained setup
script and ZIPs. The owner's `http://localhost:8090/` still returned HTTP 200.

This checkpoint supports the current-artifact native-zoom portion of GSWEB-13
and the shared GSWEB-27 evidence. It does not replace manual assistive-technology
testing, native Safari/device testing, CWV/baseline measurements, or fresh owner
acceptance of Contact and the migration.
