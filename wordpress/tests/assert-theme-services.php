<?php
/** Assert the GSWEB-16 editable Services pattern source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-services.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Services contract failed: {$message}\n" );
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

$pattern    = $read( 'patterns/services.php' );
$front_page = $read( 'templates/front-page.html' );
$style_css  = $read( 'style.css' );

foreach (
	array(
		'Title: Gama Software Services',
		'Slug: gama-software/services',
		'Categories: featured, text',
		'Inserter: yes',
	) as $metadata
) {
	if ( ! str_contains( $pattern, $metadata ) ) {
		$fail( "pattern metadata misses {$metadata}" );
	}
}

preg_match_all( '/<!--\\s+wp:([^\\s{]+)(?:\\s+[^>]*)?-->/', $pattern, $matches );
$block_names = $matches[1] ?? array();
if ( array() === $block_names ) {
	$fail( 'pattern has no opening block comments' );
}
$allowed_blocks = array( 'group', 'heading', 'image', 'paragraph' );
foreach ( $block_names as $block_name ) {
	if ( ! in_array( $block_name, $allowed_blocks, true ) ) {
		$fail( "pattern uses non-Core or unapproved block {$block_name}" );
	}
}
if ( 4 !== count( array_keys( $block_names, 'heading', true ) ) ) {
	$fail( 'pattern must contain one H2 and three H3 Heading blocks' );
}
if ( 1 !== preg_match( '/<!--\\s+wp:heading\\s+\\{[^}]*"level":2[^}]*\\}\\s+-->/', $pattern ) ) {
	$fail( 'pattern Heading must contain one H2' );
}
if ( 3 !== preg_match_all( '/<!--\\s+wp:heading\\s+\\{[^}]*"level":3[^}]*\\}\\s+-->/', $pattern ) ) {
	$fail( 'pattern must contain three H3 card titles' );
}
if ( str_contains( $pattern, '"level":1' ) || str_contains( $pattern, '<h1' ) ) {
	$fail( 'Services pattern must not introduce a second H1' );
}

if ( ! str_contains( $pattern, '<section id="services" class="wp-block-group alignfull gama-services has-surface-subtle-background-color has-background">' ) ) {
	$fail( 'pattern must expose a full-width semantic services section' );
}
foreach (
	array(
		'"tagName":"section"',
		'"anchor":"services"',
		'"align":"full"',
		'"className":"gama-services"',
		'"backgroundColor":"surface-subtle"',
		'"className":"gama-services__content"',
		'"className":"gama-services__grid"',
		'"layout":{"type":"grid","minimumColumnWidth":"20rem"}',
	) as $required_structure
) {
	if ( ! str_contains( $pattern, $required_structure ) ) {
		$fail( "pattern misses editable Core Grid structure {$required_structure}" );
	}
}
if ( str_contains( $pattern, '"columnCount"' ) ) {
	$fail( 'responsive Services Grid must not hard-code a column count' );
}
if ( 3 !== substr_count( $pattern, '"className":"gama-service-card"' ) ) {
	$fail( 'pattern must contain exactly three baseline service card groups' );
}
if ( 3 !== substr_count( $pattern, '"className":"gama-service-card__icon"' ) ) {
	$fail( 'pattern must contain exactly three baseline decorative icon blocks' );
}
if ( 3 !== substr_count( $pattern, 'alt=""' ) ) {
	$fail( 'baseline service icons must be decorative with empty alternative text' );
}

foreach (
	array(
		'Nasze Usługi',
		'Wdrożenia E-commerce',
		'Kompleksowe wdrożenia platform e-commerce, w tym Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po uruchomienie sklepu.',
		'Konsultacje E-commerce',
		'Profesjonalne doradztwo w zakresie strategii e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych rozwiązań technologicznych.',
		'Agenci AI',
		'Budujemy inteligentnych asystentów AI, którzy automatyzują obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu online.',
	) as $baseline
) {
	if ( ! str_contains( $pattern, $baseline ) ) {
		$fail( "pattern misses the approved baseline {$baseline}" );
	}
}
foreach ( array( 'service-ecommerce.svg', 'service-consulting.svg', 'service-ai.svg' ) as $asset ) {
	if ( ! str_contains( $pattern, "get_theme_file_uri( 'assets/icons/{$asset}' )" ) ) {
		$fail( "pattern does not use its packaged icon {$asset}" );
	}
}
if ( preg_match( '/<img[^>]+src=["\\\']https?:\\/\\//i', $pattern ) ) {
	$fail( 'pattern must not depend on a remote icon' );
}
if ( str_contains( $pattern, 'templateLock' ) || str_contains( $pattern, '"lock"' ) ) {
	$fail( 'Services cards must remain editable in the Site Editor' );
}
if ( preg_match( '/(?:<script|on(?:click|load|mouseover)\\s*=|motion\\/|animation:)/i', $pattern ) ) {
	$fail( 'Services pattern must not require script-driven behavior or animation' );
}

$hero_reference     = '<!-- wp:pattern {"slug":"gama-software/hero"} /-->';
$services_reference = '<!-- wp:pattern {"slug":"gama-software/services"} /-->';
$post_content       = '<!-- wp:post-content';
if ( str_contains( $front_page, $services_reference ) ) {
	$fail( 'front-page Services must be direct blocks, not a structure-locked pattern reference' );
}
if ( false === strpos( $front_page, $hero_reference ) || false === strpos( $front_page, '<section id="services"' ) || false === strpos( $front_page, $post_content )
	|| strpos( $front_page, $hero_reference ) > strpos( $front_page, '<section id="services"' )
	|| strpos( $front_page, '<section id="services"' ) > strpos( $front_page, $post_content ) ) {
	$fail( 'front-page must render Services after Hero and before editable page content' );
}
foreach (
	array(
		'"anchor":"services"',
		'"align":"full"',
		'"className":"gama-services"',
		'"className":"gama-services__grid"',
		'"layout":{"type":"grid","minimumColumnWidth":"20rem"}',
		'Nasze Usługi',
		'Wdrożenia E-commerce',
		'Konsultacje E-commerce',
		'Agenci AI',
	) as $required_template_content
) {
	if ( ! str_contains( $front_page, $required_template_content ) ) {
		$fail( "front-page misses editable Services content {$required_template_content}" );
	}
}
$services_end = strpos( $front_page, '<section id="modules"' );
$services_front_page = false === $services_end ? $front_page : substr( $front_page, 0, $services_end );
if ( 3 !== substr_count( $services_front_page, '"className":"gama-service-card"' ) || 3 !== substr_count( $services_front_page, 'alt=""' ) ) {
	$fail( 'front-page must contain three directly editable decorative service cards' );
}
foreach ( array( 'service-ecommerce.svg', 'service-consulting.svg', 'service-ai.svg' ) as $asset ) {
	if ( ! str_contains( $front_page, "/wp-content/themes/gama-software/assets/icons/{$asset}" ) ) {
		$fail( "front-page misses the installed theme icon URL {$asset}" );
	}
}
if ( str_contains( $front_page, 'templateLock' ) || str_contains( $front_page, '"lock"' ) ) {
	$fail( 'front-page Services cards must remain structurally editable in the Site Editor' );
}

foreach (
	array(
		'.gama-services {',
		'.gama-services__content {',
		'.gama-services__grid {',
		'.gama-service-card {',
		'.gama-service-card__icon {',
		'.gama-service-card .wp-block-button {',
		'padding-top: clamp(',
		'padding-bottom: clamp(',
		'display: flex',
		'flex-direction: column',
		'min-height: 100%',
		'border-radius: var(--wp--custom--radius--card)',
		'box-shadow: var(--wp--preset--shadow--elevation-2)',
		'margin-top: auto',
	) as $required_css
) {
	if ( ! str_contains( $style_css, $required_css ) ) {
		$fail( "style.css misses Services responsive behavior {$required_css}" );
	}
}
preg_match_all( '/\\.(?:gama-services|gama-service-card)[^{]*\\{(?P<declarations>[^}]*)\\}/', $style_css, $service_style_matches );
$service_styles = implode( "\n", $service_style_matches['declarations'] ?? array() );
if ( '' === $service_styles ) {
	$fail( 'could not isolate Services style declarations' );
}
foreach ( array( 'animation:', 'transition:', 'background-image:' ) as $forbidden_css ) {
	if ( str_contains( strtolower( $service_styles ), strtolower( $forbidden_css ) ) ) {
		$fail( "Services styles must not force {$forbidden_css}" );
	}
}

foreach ( array( 'service-ecommerce.svg', 'service-consulting.svg', 'service-ai.svg' ) as $asset ) {
	$svg = $read( "assets/icons/{$asset}" );
	if ( ! str_contains( $svg, '<svg ' ) || ! str_contains( $svg, 'viewBox="0 0 24 24"' ) || ! str_contains( $svg, 'aria-hidden="true"' ) ) {
		$fail( "decorative icon {$asset} is not a stable 24px hidden SVG" );
	}
	if ( ! str_contains( $svg, '#155dfc' ) ) {
		$fail( "decorative icon {$asset} must preserve the accent color" );
	}
	if ( preg_match( '/(?:<script|on[a-z]+\\s*=|<foreignObject|(?:href|src)\\s*=\\s*["\\\']https?:\\/\\/)/i', $svg ) ) {
		$fail( "decorative icon {$asset} contains unsafe or remote behavior" );
	}
}

fwrite( STDOUT, "Editable GSWEB-16 Services source contract passed.\n" );
