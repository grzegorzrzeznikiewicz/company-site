<?php
/** Assert the GSWEB-22 SEO plugin source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-seo-plugin.php <plugin-directory>\n" );
	exit( 64 );
}

$root = realpath( $argv[1] );
$fail = static function ( string $message ): never {
	fwrite( STDERR, "SEO plugin contract failed: {$message}\n" );
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

$bootstrap = $read( 'gama-seo.php' );
$plugin    = $read( 'src/class-plugin.php' );

foreach ( array( 'Plugin Name: Gama SEO', 'Version: 0.1.0', 'Requires at least: 7.1', 'Requires PHP: 8.4', 'GPL-2.0-or-later', 'Text Domain: gama-seo' ) as $required ) {
	if ( ! str_contains( $bootstrap, $required ) ) {
		$fail( "bootstrap misses {$required}" );
	}
}

foreach ( array( 'document_title_parts', 'language_attributes', 'wp_robots', 'robots_txt', 'pre_handle_404', 'wp_head', 'template_redirect', 'rel_canonical', 'wp_get_environment_type', 'canonical', 'og:title', 'og:description', 'og:url', 'og:type', 'application/ld+json', 'Organization', 'WebSite', '/wp-sitemap.xml' ) as $required ) {
	if ( ! str_contains( $plugin, $required ) ) {
		$fail( "SEO implementation misses {$required}" );
	}
}

if ( preg_match( '/(?:update|delete|insert)_post|\$wpdb|register_post_type/i', $plugin ) ) {
	$fail( 'SEO plugin must not own content persistence' );
}
if ( preg_match( '/(?:curl_|file_get_contents\s*\(\s*[\'\"]https?:|wp_remote_)/i', $plugin ) ) {
	$fail( 'SEO rendering must not call external services' );
}

fwrite( STDOUT, "GSWEB-22 SEO plugin source contract passed.\n" );
