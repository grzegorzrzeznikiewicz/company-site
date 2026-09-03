<?php
/** Assert the exact disposable theme package Compose boundary. */

declare(strict_types=1);

function gama_theme_compose_fail( string $message ): never {
	fwrite( STDERR, "Theme package Compose contract failed: {$message}\n" );
	exit( 1 );
}

$expected_zip = getenv( 'EXPECTED_PACKAGE_ZIP' );
$resolved     = json_decode( (string) stream_get_contents( STDIN ), true );
if ( ! is_string( $expected_zip ) || '' === $expected_zip || ! is_array( $resolved ) ) {
	gama_theme_compose_fail( 'invalid contract input' );
}
$services = $resolved['services'] ?? array();
$expected = array( 'browser', 'db', 'uploads-init', 'wordpress', 'wp' );
$actual   = array_keys( $services );
sort( $actual, SORT_STRING );
if ( $actual !== $expected ) {
	gama_theme_compose_fail( 'service set changed' );
}

$expected_images = array(
	'db'           => 'mariadb:10.11.18-jammy@sha256:8020e05c4c498d06c87f0a1db010eb79bd6f8fb30e9b763d4690c34ce1e61008',
	'uploads-init' => 'wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d',
	'wordpress'    => 'wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d',
	'wp'           => 'wordpress:cli-2.12.0-php8.4@sha256:1e1d1485277d15e0331b598b6e19972243128ead978b7134d758097d82116b99',
	'browser'      => 'gama-theme-browser:gsweb12',
);
$expected_mounts = array(
	'browser'      => array( array( 'volume', 'browser-artifacts', '/artifacts', false ) ),
	'db'           => array( array( 'volume', 'db-data', '/var/lib/mysql', false ) ),
	'uploads-init' => array( array( 'volume', 'uploads', '/uploads', false ) ),
	'wordpress'    => array(
		array( 'volume', 'core', '/var/www/html', false ),
		array( 'volume', 'uploads', '/var/www/html/wp-content/uploads', false ),
	),
	'wp'           => array(
		array( 'volume', 'core', '/var/www/html', false ),
		array( 'volume', 'uploads', '/var/www/html/wp-content/uploads', false ),
		array( 'bind', $expected_zip, '/package/gama-software.zip', true ),
	),
);
$binds = array();
foreach ( $expected_images as $name => $image ) {
	$service = $services[ $name ];
	if ( ( $service['image'] ?? null ) !== $image || array_key_exists( 'ports', $service ) ) {
		gama_theme_compose_fail( "{$name} image or port boundary changed" );
	}
	$actual_mounts = array();
	foreach ( $service['volumes'] ?? array() as $mount ) {
		$normalized_mount = array(
			$mount['type'] ?? null,
			$mount['source'] ?? null,
			$mount['target'] ?? null,
			(bool) ( $mount['read_only'] ?? false ),
		);
		$actual_mounts[] = $normalized_mount;
		if ( 'bind' === ( $mount['type'] ?? null ) ) {
			$binds[] = array_merge( array( $name ), $normalized_mount );
		}
	}
	if ( $actual_mounts !== $expected_mounts[ $name ] ) {
		gama_theme_compose_fail( "{$name} mount set changed" );
	}
}
if ( array( array( 'wp', 'bind', $expected_zip, '/package/gama-software.zip', true ) ) !== $binds ) {
	gama_theme_compose_fail( 'canonical read-only ZIP must be the only bind mount' );
}
$browser_build = $services['browser']['build'] ?? array();
if ( ! str_ends_with( (string) ( $browser_build['context'] ?? '' ), '/web' )
	|| 'wordpress/qa/browser.Dockerfile' !== ( $browser_build['dockerfile'] ?? null ) ) {
	gama_theme_compose_fail( 'browser build boundary changed' );
}
if ( true !== ( $resolved['networks']['default']['internal'] ?? false ) ) {
	gama_theme_compose_fail( 'default project network must be internal' );
}
$volume_names = array_keys( $resolved['volumes'] ?? array() );
sort( $volume_names, SORT_STRING );
if ( array( 'browser-artifacts', 'core', 'db-data', 'uploads' ) !== $volume_names ) {
	gama_theme_compose_fail( 'project volume set changed' );
}
fwrite( STDOUT, "Resolved theme package Compose boundary is exact.\n" );
