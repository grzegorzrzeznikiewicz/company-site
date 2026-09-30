<?php
/** Assert the GSWEB-21 content, media and homepage assembly contract. */

declare(strict_types=1);

if ( 3 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-content.php <theme-directory> <bootstrap-file>\n" );
	exit( 64 );
}

$theme = realpath( $argv[1] );
$bootstrap = realpath( $argv[2] );
$fail = static function ( string $message ): never {
	fwrite( STDERR, "Homepage content contract failed: {$message}\n" );
	exit( 1 );
};
if ( false === $theme || ! is_dir( $theme ) || false === $bootstrap || ! is_file( $bootstrap ) ) {
	$fail( 'required source is unavailable' );
}
$read = static function ( string $relative ) use ( $theme, $fail ): string {
	$path = realpath( $theme . DIRECTORY_SEPARATOR . $relative );
	if ( false === $path || ! str_starts_with( $path, $theme . DIRECTORY_SEPARATOR ) || ! is_file( $path ) ) {
		$fail( "missing or escaped file {$relative}" );
	}
	$content = file_get_contents( $path );
	if ( false === $content ) {
		$fail( "could not read {$relative}" );
	}
	return $content;
};

$front = $read( 'templates/front-page.html' );
$header = $read( 'parts/header.html' );
$footer = $read( 'parts/footer.html' );
$hero = $read( 'patterns/hero.php' );
$logo = $theme . '/assets/images/gama-software-logo.png';
$logo_dimensions = is_file( $logo ) ? getimagesize( $logo ) : false;
if ( false === $logo_dimensions || 1024 !== $logo_dimensions[0] || 1024 !== $logo_dimensions[1] || IMAGETYPE_PNG !== $logo_dimensions[2] || 'image/png' !== ( $logo_dimensions['mime'] ?? null ) ) {
	$fail( 'approved 1024px PNG logo is missing or changed' );
}

$expected_order = array( 'gama-software/hero', 'gama-services', 'gama-modules', 'gama-blog-latest', 'gama-contact' );
$offset = -1;
foreach ( $expected_order as $class ) {
	$next = strpos( $front, $class );
	if ( false === $next || $next <= $offset ) {
		$fail( "homepage section order differs at {$class}" );
	}
	$offset = $next;
}

$assembled_source = $front . "\n" . $hero;
foreach ( array( 'anchor":"home', 'anchor":"services', 'anchor":"modules', 'anchor":"blog', 'anchor":"contact' ) as $anchor ) {
	if ( 1 !== substr_count( $assembled_source, $anchor ) ) {
		$fail( "stable homepage anchor differs: {$anchor}" );
	}
}
foreach ( array(
	'Gama Software',
	'Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu',
	'Poznaj nasze usługi',
	'Nasze Usługi',
	'Wdrożenia E-commerce',
	'Konsultacje E-commerce',
	'Agenci AI',
	'Moduły Magento 2',
	'Advanced SEO Suite',
	'Smart Product Recommendations',
	'Enhanced Checkout',
	'Inventory Management Pro',
	'Customer Loyalty Program',
	'Performance Optimizer',
	'Blog',
	'W budowie',
	'Kontakt',
) as $copy ) {
	if ( ! str_contains( $assembled_source, $copy ) ) {
		$fail( "homepage misses approved copy: {$copy}" );
	}
}
if ( 1 !== preg_match_all( '/<h1\b/i', $assembled_source ) || preg_match( '/lorem ipsum|welcome to wordpress/i', $assembled_source . $header . $footer ) ) {
	$fail( 'homepage heading or demonstration-copy contract differs' );
}
if ( preg_match( '/href=["\']#["\']|"url"\s*:\s*"#"/i', $front . $header . $footer ) ) {
	$fail( 'placeholder links remain in the assembled homepage' );
}

$bootstrap_source = file_get_contents( $bootstrap );
if ( false === $bootstrap_source ) {
	$fail( 'could not read bootstrap' );
}
foreach ( array( 'gama-software-logo.png', '_gama_asset_key', 'gama-software-logo', 'custom_logo', 'Polityka prywatności', 'polityka-prywatnosci', 'Regulamin', 'post_status=draft', 'TREŚĆ WYMAGA ZATWIERDZENIA WŁAŚCICIELA' ) as $required ) {
	if ( ! str_contains( $bootstrap_source, $required ) ) {
		$fail( "bootstrap misses {$required}" );
	}
}

fwrite( STDOUT, "GSWEB-21 content, logo and legal-draft source contract passed.\n" );
