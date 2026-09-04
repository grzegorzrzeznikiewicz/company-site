# Changelog

All notable changes to `gama-software/gama-contact` are documented here.

## 0.3.1 - 2026-09-04

- Serialize rate-limit updates with a MariaDB advisory lock.
- Add a deterministic database-lock runtime contract.

## 0.3.0 - 2026-09-04

- Make IP rate limiting atomic under concurrent requests.
- Associate field errors with their inputs and focus the first invalid field.
- Show a localized message when browser delivery fails.

## 0.2.0 - 2026-09-04

- Add the accessible, theme-independent contact form shortcode.
- Validate and sanitize all fields on the server without losing browser input.
- Add same-origin nonce checks, a honeypot, and per-IP rate limiting.
- Deliver through WordPress mail using environment-configured addresses without storing messages.

## 0.1.0 - 2026-09-03

- Add the dependency-free, theme-independent plugin lifecycle scaffold.
- Persist schema version 1 across deactivate, theme switch, and default uninstall.
