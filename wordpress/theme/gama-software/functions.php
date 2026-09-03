<?php
/**
 * Theme setup and editor policy.
 *
 * @package GamaSoftware
 */

declare(strict_types=1);

/** Register supported WordPress features. */
function gama_software_setup(): void {
	load_theme_textdomain( 'gama-software', get_template_directory() . '/languages' );
	add_theme_support( 'custom-logo' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'wp-block-styles' );
	add_theme_support( 'responsive-embeds' );
	add_theme_support( 'editor-styles' );
	add_editor_style( 'style.css' );
}
add_action( 'after_setup_theme', 'gama_software_setup' );

/** Enqueue the same foundation stylesheet used in the editor. */
function gama_software_enqueue_styles(): void {
	wp_enqueue_style( 'gama-software-style', get_stylesheet_uri(), array(), (string) wp_get_theme()->get( 'Version' ) );
}
add_action( 'wp_enqueue_scripts', 'gama_software_enqueue_styles' );

/**
 * Disable code editing for users who cannot activate plugins.
 *
 * @param array<string, mixed>    $settings Editor settings.
 * @param WP_Block_Editor_Context $context  Current editor context.
 * @return array<string, mixed>
 */
function gama_software_filter_editor_settings( array $settings, WP_Block_Editor_Context $context ): array {
	unset( $context );
	if ( ! current_user_can( 'activate_plugins' ) ) {
		$settings['codeEditingEnabled'] = false;
	}
	return $settings;
}
add_filter( 'block_editor_settings_all', 'gama_software_filter_editor_settings', 10, 2 );

/**
 * Remove only the Custom HTML block for non-administrative editors.
 *
 * @param bool|string[]           $allowed_blocks Allowed block names.
 * @param WP_Block_Editor_Context $context        Current editor context.
 * @return bool|string[]
 */
function gama_software_filter_allowed_blocks( $allowed_blocks, WP_Block_Editor_Context $context ) {
	unset( $context );
	if ( current_user_can( 'activate_plugins' ) || false === $allowed_blocks ) {
		return $allowed_blocks;
	}
	if ( true === $allowed_blocks ) {
		$allowed_blocks = array_keys( WP_Block_Type_Registry::get_instance()->get_all_registered() );
	}
	return array_values(
		array_filter(
			$allowed_blocks,
			static fn( string $block_name ): bool => 'core/html' !== $block_name
		)
	);
}
add_filter( 'allowed_block_types_all', 'gama_software_filter_allowed_blocks', 10, 2 );
