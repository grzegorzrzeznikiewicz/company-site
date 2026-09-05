<?php
/** Assert the GSWEB-20 contact plugin source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-contact-plugin.php <plugin-directory>\n" );
	exit( 64 );
}

$root = realpath( $argv[1] );
$fail = static function ( string $message ): never {
	fwrite( STDERR, "Contact plugin contract failed: {$message}\n" );
	exit( 1 );
};
if ( false === $root || ! is_dir( $root ) ) {
	$fail( 'plugin directory is unavailable' );
}
$read = static function ( string $relative ) use ( $root, $fail ): string {
	$path = realpath( $root . DIRECTORY_SEPARATOR . $relative );
	if ( false === $path || ! str_starts_with( $path, $root . DIRECTORY_SEPARATOR ) || ! is_file( $path ) ) {
		$fail( "missing or escaped file {$relative}" );
	}
	$content = file_get_contents( $path );
	if ( false === $content ) {
		$fail( "could not read {$relative}" );
	}
	return $content;
};

$plugin     = $read( 'gama-contact.php' );
$controller = $read( 'src/Form/SubmissionController.php' );
$rate_limiter = $read( 'src/Form/RateLimiter.php' );
$renderer   = $read( 'src/Form/FormRenderer.php' );
$validator  = $read( 'src/Form/Validator.php' );
$script     = $read( 'assets/contact-form.js' );

foreach ( array( 'Version: 0.3.2', "GAMA_CONTACT_VERSION', '0.3.2", 'SubmissionController.php', 'RateLimiter.php', 'FormRenderer.php', 'Validator.php' ) as $required ) {
	if ( ! str_contains( $plugin, $required ) ) {
		$fail( "plugin bootstrap misses {$required}" );
	}
}
foreach ( array( 'gama-contact/v1', 'messages', 'wp_verify_nonce', 'wp_get_raw_referer', 'wp_mail', 'RateLimiter::consume', '429', 'company' ) as $required ) {
	if ( ! str_contains( $controller, $required ) ) {
		$fail( "submission controller misses {$required}" );
	}
}
foreach ( array( 'GET_LOCK', 'RELEASE_LOCK', '$wpdb', 'get_transient', 'set_transient', 'hash_hmac' ) as $required ) {
	if ( ! str_contains( $rate_limiter, $required ) ) {
		$fail( "atomic rate limiter misses {$required}" );
	}
}
foreach ( array( 'name', 'email', 'phone', 'message', 'sanitize_text_field', 'sanitize_email', 'sanitize_textarea_field', 'is_email' ) as $required ) {
	if ( ! str_contains( $validator, $required ) ) {
		$fail( "server validator misses {$required}" );
	}
}
foreach ( array( '<form', '<label', 'aria-live="polite"', 'aria-describedby="gama-contact-name-error"', 'id="gama-contact-name-error"', 'autocomplete="name"', 'autocomplete="email"', 'autocomplete="tel"', 'gama_contact_nonce', 'company' ) as $required ) {
	if ( ! str_contains( $renderer, $required ) ) {
		$fail( "accessible renderer misses {$required}" );
	}
}
foreach ( array( 'fetch(', 'FormData', 'aria-invalid', 'firstInvalidField', 'focus()', 'response.ok', 'reset()' ) as $required ) {
	if ( ! str_contains( $script, $required ) ) {
		$fail( "browser enhancement misses {$required}" );
	}
}
if ( preg_match( '/(?:insert|update|delete)_post|register_post_type/i', $controller . $rate_limiter . $renderer . $validator ) ) {
	$fail( 'plugin must not persist contact message content' );
}

fwrite( STDOUT, "Secure GSWEB-20 contact plugin source contract passed.\n" );
