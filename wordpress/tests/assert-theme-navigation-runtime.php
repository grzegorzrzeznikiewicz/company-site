<?php
/** Assert GSWEB-14 against the installed ZIP and the real WordPress runtime. */

declare(strict_types=1);

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Installed navigation contract failed: {$message}\n" );
	exit( 1 );
};
$theme_root = realpath( get_theme_root( 'gama-software' ) . '/gama-software' );
if ( false === $theme_root || WP_CONTENT_DIR . '/themes/gama-software' !== $theme_root ) {
	$fail( 'theme is not installed at the exact ZIP destination' );
}

$walk = static function ( array $blocks, string $source ) use ( &$walk, $fail ): void {
	foreach ( $blocks as $block ) {
		$block_name = $block['blockName'] ?? null;
		if ( null === $block_name ) {
			if ( '' !== trim( (string) ( $block['innerHTML'] ?? '' ) ) ) {
				$fail( "non-block fragment in {$source}" );
			}
			continue;
		}
		if ( ! WP_Block_Type_Registry::get_instance()->is_registered( $block_name ) ) {
			$fail( "unregistered block {$block_name} in {$source}" );
		}
		$walk( $block['innerBlocks'] ?? array(), $source );
	}
};
$find_blocks = static function ( array $blocks, string $block_name ) use ( &$find_blocks ): array {
	$found = array();
	foreach ( $blocks as $block ) {
		if ( $block_name === ( $block['blockName'] ?? null ) ) {
			$found[] = $block;
		}
		$found = array_merge( $found, $find_blocks( $block['innerBlocks'] ?? array(), $block_name ) );
	}
	return $found;
};

$parsed_files = array();
foreach ( array_merge( glob( $theme_root . '/templates/*.html' ), glob( $theme_root . '/parts/*.html' ) ) as $file ) {
	$content = file_get_contents( $file );
	if ( false === $content ) {
		$fail( 'could not read installed file ' . basename( $file ) );
	}
	$blocks = parse_blocks( $content );
	$walk( $blocks, basename( $file ) );
	$parsed_files[ basename( $file ) ] = $blocks;
}

$header_navigations = $find_blocks( $parsed_files['header.html'], 'core/navigation' );
$footer_navigations = $find_blocks( $parsed_files['footer.html'], 'core/navigation' );
if ( 1 !== count( $header_navigations ) || 1 !== count( $footer_navigations ) ) {
	$fail( 'installed parts must contain exactly one Navigation each' );
}
$primary   = $header_navigations[0];
$auxiliary = $footer_navigations[0];
if ( 'mobile' !== ( $primary['attrs']['overlayMenu'] ?? null ) || 'Główna nawigacja' !== ( $primary['attrs']['ariaLabel'] ?? null ) ) {
	$fail( 'installed primary Navigation attributes differ' );
}
if ( 'never' !== ( $auxiliary['attrs']['overlayMenu'] ?? null ) || 'Nawigacja pomocnicza' !== ( $auxiliary['attrs']['ariaLabel'] ?? null ) ) {
	$fail( 'installed auxiliary Navigation attributes differ' );
}

$rendered = render_block( $primary );
$container_processor = new WP_HTML_Tag_Processor( $rendered );
if ( ! $container_processor->next_tag( array( 'tag_name' => 'DIV', 'class_name' => 'wp-block-navigation__responsive-container' ) ) ) {
	$fail( 'Core did not render the responsive container' );
}
$container_id = $container_processor->get_attribute( 'id' );
if ( ! is_string( $container_id ) || '' === $container_id ) {
	$fail( 'Core responsive container has no ID' );
}
$button_processor = new WP_HTML_Tag_Processor( $rendered );
if ( ! $button_processor->next_tag( array( 'tag_name' => 'BUTTON', 'class_name' => 'wp-block-navigation__responsive-container-open' ) ) ) {
	$fail( 'Core did not render the exact open control' );
}
if ( $container_id !== $button_processor->get_attribute( 'aria-controls' ) ) {
	$fail( 'open control aria-controls does not reference the overlay container' );
}
if ( 'false' !== $button_processor->get_attribute( 'aria-expanded' ) ) {
	$fail( 'open control does not expose the server-rendered false expanded state' );
}
if ( 'context.overlayOpenedBy.click' !== $button_processor->get_attribute( 'data-wp-bind--aria-expanded' ) ) {
	$fail( 'open control is not bound to Core Navigation click state' );
}

$block_instance = new WP_Block(
	array(
		'blockName'    => 'core/navigation',
		'attrs'        => array( 'overlayMenu' => 'mobile' ),
		'innerBlocks'  => array(),
		'innerHTML'    => '',
		'innerContent' => array(),
	)
);
$unchanged_cases = array(
	array( 'overlay never', '<nav><button class="wp-block-navigation__responsive-container-open">Open</button><div id="modal-1" class="wp-block-navigation__responsive-container"></div></nav>', array( 'overlayMenu' => 'never' ) ),
	array( 'empty HTML', '', array( 'overlayMenu' => 'mobile' ) ),
	array( 'missing container', '<nav><button class="wp-block-navigation__responsive-container-open">Open</button></nav>', array( 'overlayMenu' => 'mobile' ) ),
	array( 'missing container ID', '<nav><button class="wp-block-navigation__responsive-container-open">Open</button><div class="wp-block-navigation__responsive-container"></div></nav>', array( 'overlayMenu' => 'mobile' ) ),
	array( 'missing exact trigger', '<nav><button class="arbitrary">Open</button><div id="modal-1" class="wp-block-navigation__responsive-container"></div></nav>', array( 'overlayMenu' => 'mobile' ) ),
	array( 'damaged markup', '<div id="modal-1" class="wp-block-navigation__responsive-container">', array( 'overlayMenu' => 'mobile' ) ),
);
foreach ( $unchanged_cases as list( $label, $html, $attributes ) ) {
	$block = array( 'attrs' => $attributes );
	if ( $html !== gama_software_add_navigation_toggle_state( $html, $block, $block_instance ) ) {
		$fail( "fail-closed case changed HTML: {$label}" );
	}
}

$targeted = '<nav><button class="arbitrary">Other</button><button class="wp-block-navigation__responsive-container-open">Open</button><div id="modal-target" class="wp-block-navigation__responsive-container"></div></nav>';
$targeted_result = gama_software_add_navigation_toggle_state( $targeted, array( 'attrs' => array( 'overlayMenu' => 'mobile' ) ), $block_instance );
if ( ! str_contains( $targeted_result, '<button class="arbitrary">Other</button>' ) ) {
	$fail( 'bridge changed an arbitrary button' );
}
$targeted_processor = new WP_HTML_Tag_Processor( $targeted_result );
if ( ! $targeted_processor->next_tag( array( 'tag_name' => 'BUTTON', 'class_name' => 'wp-block-navigation__responsive-container-open' ) )
	|| 'modal-target' !== $targeted_processor->get_attribute( 'aria-controls' )
	|| 'context.overlayOpenedBy.click' !== $targeted_processor->get_attribute( 'data-wp-bind--aria-expanded' ) ) {
	$fail( 'bridge did not update only the exact open control' );
}

global $wp_filter;
$registered = array();
foreach ( ( $wp_filter['render_block_core/navigation']->callbacks ?? array() ) as $callbacks ) {
	foreach ( $callbacks as $callback ) {
		if ( 'gama_software_add_navigation_toggle_state' === $callback['function'] ) {
			$registered[] = $callback;
		}
	}
}
if ( 1 !== count( $registered ) || 3 !== ( $registered[0]['accepted_args'] ?? null ) ) {
	$fail( 'Navigation render bridge must be registered exactly once with three arguments' );
}

echo "installed-navigation-runtime-ok";
