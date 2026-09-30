<?php
/** Assert the GSWEB-17 editable Modules source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-modules.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Modules contract failed: {$message}\n" );
	exit( 1 );
};
$read = static function ( string $relative_path ) use ( $theme_directory, $fail ): string {
	$path = realpath( $theme_directory . DIRECTORY_SEPARATOR . $relative_path );
	if ( false === $path || ! str_starts_with( $path, $theme_directory . DIRECTORY_SEPARATOR ) || ! is_file( $path ) ) {
		$fail( "missing or escaped file {$relative_path}" );
	}
	$content = file_get_contents( $path );
	if ( false === $content ) {
		$fail( "could not read {$relative_path}" );
	}
	return $content;
};

$pattern     = $read( 'patterns/modules.php' );
$front_page = $read( 'templates/front-page.html' );
$style_css   = $read( 'style.css' );
$icon        = $read( 'assets/icons/module-package.svg' );

foreach (
	array(
		'Title: Gama Software Modules',
		'Slug: gama-software/modules',
		'Categories: featured, text',
		'Inserter: yes',
	) as $metadata
) {
	if ( ! str_contains( $pattern, $metadata ) ) {
		$fail( "pattern metadata misses {$metadata}" );
	}
}

foreach (
	array(
		'Moduły Magento 2',
		'Profesjonalne rozszerzenia dostępne w modelu subskrypcji',
		'Advanced SEO Suite',
		'Smart Product Recommendations',
		'Enhanced Checkout',
		'Inventory Management Pro',
		'Customer Loyalty Program',
		'Performance Optimizer',
		'Wkrótce dostępne w formie subskrypcji',
		'Zapisz się na listę oczekujących',
	) as $baseline
) {
	if ( ! str_contains( $pattern, $baseline ) || ! str_contains( $front_page, $baseline ) ) {
		$fail( "pattern or front-page misses approved baseline {$baseline}" );
	}
}

$pattern_reference = '<!-- wp:pattern {"slug":"gama-software/modules"} /-->';
if ( str_contains( $front_page, $pattern_reference ) ) {
	$fail( 'front-page Modules must be direct editable blocks, not a pattern reference' );
}
if ( 6 !== substr_count( $front_page, '"className":"gama-module-card"' ) ) {
	$fail( 'front-page must contain six directly editable module cards' );
}
if ( 30 !== substr_count( $front_page, '<!-- wp:list-item -->' ) || 30 !== substr_count( $front_page, '<!-- /wp:list-item -->' ) ) {
	$fail( 'front-page must contain thirty valid editable feature list items' );
}
foreach (
	array(
		'"tagName":"section"',
		'"anchor":"modules"',
		'"className":"gama-modules"',
		'"className":"gama-modules__grid"',
		'"layout":{"type":"grid","minimumColumnWidth":"20rem"}',
		'"className":"gama-module-card__features"',
		'"className":"gama-modules__action"',
		'href="/#contact"',
	) as $structure
) {
	if ( ! str_contains( $pattern, $structure ) || ! str_contains( $front_page, $structure ) ) {
		$fail( "pattern or front-page misses editable structure {$structure}" );
	}
}
if ( str_contains( $front_page, 'templateLock' ) || str_contains( $front_page, '"lock"' ) ) {
	$fail( 'module cards and final action must remain removable and reorderable' );
}
if ( preg_match( '/(?:<script|on(?:click|load|mouseover)\s*=|motion\/|animation:)/i', $pattern . $front_page ) ) {
	$fail( 'Modules must not rely on script-driven behavior or animation' );
}

$services = strpos( $front_page, '<section id="services"' );
$modules  = strpos( $front_page, '<section id="modules"' );
$content  = strpos( $front_page, '<!-- wp:post-content' );
if ( false === $services || false === $modules || false === $content || $services > $modules || $modules > $content ) {
	$fail( 'front-page must render Modules after Services and before page content' );
}

foreach (
	array(
		'.gama-modules {',
		'.gama-modules__content {',
		'.gama-modules__grid {',
		'.gama-module-card {',
		'.gama-module-card__header,',
		'.gama-module-card__icon {',
		'.gama-module-card__features {',
		'display: flex',
		'flex-direction: column',
		'min-height: 100%',
		'overflow-wrap: anywhere',
	) as $required_css
) {
	if ( ! str_contains( $style_css, $required_css ) ) {
		$fail( "style.css misses responsive Modules behavior {$required_css}" );
	}
}
if ( ! str_contains( $icon, '<svg ' ) || ! str_contains( $icon, 'viewBox="0 0 24 24"' ) || ! str_contains( $icon, 'aria-hidden="true"' ) ) {
	$fail( 'decorative module icon is not a stable hidden 24px SVG' );
}
if ( preg_match( '/(?:<script|on[a-z]+\s*=|<foreignObject|(?:href|src)\s*=\s*["\']https?:\/\/)/i', $icon ) ) {
	$fail( 'decorative module icon contains unsafe or remote behavior' );
}

fwrite( STDOUT, "Editable GSWEB-17 Modules source contract passed.\n" );
