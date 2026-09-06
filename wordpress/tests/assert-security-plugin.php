<?php
/** Assert the GSWEB-23 security plugin source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-security-plugin.php <plugin-directory>\n" );
	exit( 64 );
}

$root = realpath( $argv[1] );
$fail = static function ( string $message ): never {
	fwrite( STDERR, "Security plugin contract failed: {$message}\n" );
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
	return false === $content ? $fail( "could not read {$relative}" ) : $content;
};

$bootstrap = $read( 'gama-security.php' );
$plugin    = $read( 'src/class-plugin.php' );
$guard     = $read( 'src/class-loginguard.php' );

foreach ( array( 'Plugin Name: Gama Security', 'Version: 0.1.1', 'Requires at least: 7.1', 'Requires PHP: 8.4', 'GPL-2.0-or-later', 'Text Domain: gama-security' ) as $required ) {
	if ( ! str_contains( $bootstrap, $required ) ) {
		$fail( "bootstrap misses {$required}" );
	}
}
foreach ( array( 'user_has_cap', "in_array( 'edit_theme_options', \$caps, true )", 'editor', 'activate_plugins', 'send_headers', 'X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy', 'Permissions-Policy', 'Strict-Transport-Security', 'wp_get_environment_type', 'login_errors', 'the_generator' ) as $required ) {
	if ( ! str_contains( $plugin, $required ) ) {
		$fail( "security policy misses {$required}" );
	}
}
foreach ( array( 'authenticate', 'wp_login_failed', 'wp_login', 'WP_Error', 'GET_LOCK', 'RELEASE_LOCK', '$wpdb', 'hash_hmac', 'wp_salt', '429' ) as $required ) {
	if ( ! str_contains( $guard, $required ) ) {
		$fail( "login guard misses {$required}" );
	}
}

fwrite( STDOUT, "GSWEB-23 role and security plugin source contract passed.\n" );
