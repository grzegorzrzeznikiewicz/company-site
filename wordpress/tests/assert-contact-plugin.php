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
$renderer   = $read( 'src/Form/FormRenderer.php' );
$validator  = $read( 'src/Form/Validator.php' );
$script     = $read( 'assets/contact-form.js' );

foreach ( array( 'Version: 0.3.0', "GAMA_CONTACT_VERSION', '0.3.0", 'SubmissionController.php', 'FormRenderer.php', 'Validator.php' ) as $required ) {
	if ( ! str_contains( $plugin, $required ) ) {
		$fail( "plugin bootstrap misses {$required}" );
	}
}
foreach ( array( 'gama-contact/v1', 'messages', 'wp_verify_nonce', 'wp_get_raw_referer', 'wp_mail', 'GAMA_CONTACT_RECIPIENT', 'set_transient', 'add_option', 'delete_option', 'lock_token', '429', 'company' ) as $required ) {
	if ( ! str_contains( $controller, $required ) ) {
		$fail( "submission controller misses {$required}" );
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
if ( preg_match( '/(?:insert|update|delete)_post|\$wpdb|register_post_type/i', $controller . $renderer . $validator ) ) {
	$fail( 'plugin must not persist contact message content' );
}

fwrite( STDOUT, "Secure GSWEB-20 contact plugin source contract passed.\n" );
