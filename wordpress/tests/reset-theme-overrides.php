<?php
/**
 * Test-only destructive helper for disposable theme-package databases.
 *
 * The caller must define all GAMA_THEME_RESET_* constants before evaluating
 * this file inside WordPress. This file is never part of the theme package.
 */

declare(strict_types=1);

$gama_theme_reset_fail = static function ( string $message ): never {
	fwrite( STDERR, $message . PHP_EOL );
	exit( 1 );
};

$gama_theme_required_constants = array(
	'GAMA_THEME_RESET_CONFIRM',
	'GAMA_THEME_RESET_PROJECT',
	'GAMA_THEME_RESET_SENTINEL',
	'GAMA_THEME_RESET_IDS',
	'GAMA_THEME_RESET_TARGETS',
);
foreach ( $gama_theme_required_constants as $gama_theme_constant ) {
	if ( ! defined( $gama_theme_constant ) ) {
		$gama_theme_reset_fail( "Missing reset constant: {$gama_theme_constant}" );
	}
}
if ( true !== GAMA_THEME_RESET_CONFIRM ) {
	$gama_theme_reset_fail( 'Explicit reset confirmation is required.' );
}
if ( 1 !== preg_match( '/^gama-theme-package-[0-9]+-[0-9]+-[0-9]+$/', GAMA_THEME_RESET_PROJECT ) ) {
	$gama_theme_reset_fail( 'Refusing a non-disposable project name.' );
}
if ( ! hash_equals( (string) get_option( 'gama_theme_test_sentinel' ), GAMA_THEME_RESET_SENTINEL ) ) {
	$gama_theme_reset_fail( 'Disposable database sentinel mismatch.' );
}
if ( ! is_array( GAMA_THEME_RESET_IDS ) || array() === GAMA_THEME_RESET_IDS ) {
	$gama_theme_reset_fail( 'A non-empty explicit post ID list is required.' );
}
if ( ! is_array( GAMA_THEME_RESET_TARGETS ) || count( GAMA_THEME_RESET_IDS ) !== count( GAMA_THEME_RESET_TARGETS ) ) {
	$gama_theme_reset_fail( 'The exact reset target map is required.' );
}

$gama_theme_verified = array();
foreach ( GAMA_THEME_RESET_IDS as $gama_theme_index => $gama_theme_post_id ) {
	$gama_theme_target = GAMA_THEME_RESET_TARGETS[ $gama_theme_index ];
	$gama_theme_post   = get_post( $gama_theme_post_id );
	if ( ! $gama_theme_post instanceof WP_Post
		|| ! in_array( $gama_theme_post->post_type, array( 'wp_template', 'wp_template_part' ), true )
		|| ! is_array( $gama_theme_target )
		|| 'gama-software' !== ( $gama_theme_target['theme'] ?? null )
		|| $gama_theme_post->post_type !== ( $gama_theme_target['type'] ?? null ) ) {
		$gama_theme_reset_fail( 'Reset post identity does not match the explicit target.' );
	}
	$gama_theme_terms = wp_get_object_terms( $gama_theme_post_id, 'wp_theme', array( 'fields' => 'names' ) );
	if ( is_wp_error( $gama_theme_terms ) || array( 'gama-software' ) !== array_values( $gama_theme_terms ) ) {
		$gama_theme_reset_fail( 'Reset target does not belong exclusively to gama-software.' );
	}
	$gama_theme_slug     = (string) ( $gama_theme_target['slug'] ?? '' );
	$gama_theme_template = get_block_template( "gama-software//{$gama_theme_slug}", $gama_theme_post->post_type );
	if ( ! $gama_theme_template instanceof WP_Block_Template
		|| 'custom' !== $gama_theme_template->source
		|| true !== $gama_theme_template->has_theme_file ) {
		$gama_theme_reset_fail( 'Target is not a custom override backed by a theme file.' );
	}
	$gama_theme_verified[] = array(
		'id'    => $gama_theme_post_id,
		'theme' => 'gama-software',
		'slug'  => $gama_theme_slug,
		'type'  => $gama_theme_post->post_type,
	);
}

echo wp_json_encode( $gama_theme_verified, JSON_UNESCAPED_SLASHES ) . PHP_EOL;
foreach ( $gama_theme_verified as $gama_theme_target ) {
	if ( ! wp_delete_post( $gama_theme_target['id'], true ) ) {
		$gama_theme_reset_fail( 'WordPress refused to delete an approved override.' );
	}
}
foreach ( $gama_theme_verified as $gama_theme_target ) {
	if ( null !== get_post( $gama_theme_target['id'] ) ) {
		$gama_theme_reset_fail( 'An approved override remains after reset.' );
	}
}
echo 'test-only-theme-overrides-reset' . PHP_EOL;
