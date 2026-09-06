=== Gama Contact ===
Contributors: gamasoftware
Tags: contact
Requires at least: 7.1
Requires PHP: 8.4
Stable tag: 0.3.2
License: GPL-2.0-or-later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Theme-independent and secure Gama Software contact form.

== Description ==

Version 0.3.2 provides an accessible shortcode form, server validation, same-origin
nonce checks, honeypot protection, per-IP rate limiting, and WordPress mail
delivery without storing message content.

== Installation ==

Install the versioned ZIP in WordPress and activate Gama Contact.

== Changelog ==

= 0.3.2 =
* Fix shortcode formatting and empty validation spacing in the contact form.

= 0.3.1 =
* Serialize rate-limit updates with a database advisory lock.

= 0.3.0 =
* Add atomic concurrent rate limiting and accessible field-error handling.

= 0.2.0 =
* Add the secure contact form and environment-configured mail delivery.

= 0.1.0 =
* Add the dependency-free lifecycle scaffold.
