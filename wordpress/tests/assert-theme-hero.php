<?php
/** Assert the GSWEB-15 editable Hero pattern source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-hero.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Hero contract failed: {$message}\n" );
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

$pattern    = $read( 'patterns/hero.php' );
$front_page = $read( 'templates/front-page.html' );
$style_css  = $read( 'style.css' );

foreach (
	array(
		'Title: Gama Software Hero',
		'Slug: gama-software/hero',
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
$allowed_blocks = array( 'group', 'heading', 'paragraph', 'buttons', 'button' );
foreach ( $block_names as $block_name ) {
	if ( ! in_array( $block_name, $allowed_blocks, true ) ) {
		$fail( "pattern uses non-Core or unapproved block {$block_name}" );
	}
}
if ( 1 !== count( array_keys( $block_names, 'heading', true ) ) ) {
	$fail( 'pattern must contain exactly one Heading block' );
}
if ( 1 !== preg_match( '/<!--\\s+wp:heading\\s+\\{[^}]*"level":1[^}]*\\}\\s+-->/', $pattern ) ) {
	$fail( 'pattern Heading must be the single H1' );
}
if ( ! str_contains( $pattern, '<h1 class="wp-block-heading has-text-align-center has-display-font-size">' ) ) {
	$fail( 'pattern H1 misses the editable display heading markup' );
}
if ( ! str_contains( $pattern, '<section id="home" class="wp-block-group gama-hero">' ) ) {
	$fail( 'pattern must expose the home anchor on a semantic Hero section' );
}
if ( ! str_contains( $pattern, '"anchor":"home"' ) || ! str_contains( $pattern, '"className":"gama-hero"' ) ) {
	$fail( 'pattern outer Group must remain the editable Hero anchor' );
}
if ( ! str_contains( $pattern, '"className":"gama-hero__content"' )
	|| ! str_contains( $pattern, '"className":"gama-hero__lead"' ) ) {
	$fail( 'pattern misses the responsive Hero content classes' );
}
foreach (
	array(
		'Gama Software',
		'Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu',
		'Poznaj nasze usługi',
		'"url":"/#services"',
	) as $baseline
) {
	if ( ! str_contains( $pattern, $baseline ) ) {
		$fail( "pattern misses the approved baseline {$baseline}" );
	}
}
if ( ! str_contains( $pattern, '<a class="wp-block-button__link has-base-color has-accent-background-color has-text-color has-background wp-element-button" href="/#services">' ) ) {
	$fail( 'Hero CTA must be a Core Button with a no-JavaScript homepage anchor URL' );
}
if ( str_contains( $pattern, 'templateLock' ) || str_contains( $pattern, '"lock"' ) ) {
	$fail( 'Hero must remain editable in the Site Editor' );
}
if ( preg_match( '/(?:<script|on(?:click|load|mouseover)\\s*=|motion\\/|animation:)/i', $pattern ) ) {
	$fail( 'Hero must not require script-driven behavior or animation' );
}

$pattern_reference = '<!-- wp:pattern {"slug":"gama-software/hero"} /-->';
if ( 1 !== substr_count( $front_page, $pattern_reference ) ) {
	$fail( 'front-page must include exactly one Hero pattern starter' );
}
if ( false === strpos( $front_page, $pattern_reference ) || false === strpos( $front_page, '<!-- wp:post-content' )
	|| strpos( $front_page, $pattern_reference ) > strpos( $front_page, '<!-- wp:post-content' ) ) {
	$fail( 'front-page must render Hero before the editable page content' );
}
if ( preg_match( '/<!--\\s+wp:heading\\s+\\{[^}]*"level":1[^}]*\\}\\s+-->/', $front_page ) ) {
	$fail( 'front-page must not add another H1 outside the Hero pattern' );
}

foreach (
	array(
		'.gama-hero {',
		'.gama-hero__content {',
		'.gama-hero .wp-block-buttons {',
		'padding-top: clamp(',
		'padding-bottom: clamp(',
		'max-width: 48rem',
		'justify-content: center',
		'@media (min-width: 768px)',
	) as $required_css
) {
	if ( ! str_contains( $style_css, $required_css ) ) {
		$fail( "style.css misses Hero responsive behavior {$required_css}" );
	}
}
preg_match_all( '/\\.gama-hero[^\\{]*\\{(?P<declarations>[^}]*)\\}/', $style_css, $hero_style_matches );
$hero_styles = implode( "\n", $hero_style_matches['declarations'] ?? array() );
if ( '' === $hero_styles ) {
	$fail( 'could not isolate Hero style declarations' );
}
foreach ( array( 'animation:', 'transition:', 'background-image:' ) as $forbidden_css ) {
	if ( str_contains( strtolower( $hero_styles ), strtolower( $forbidden_css ) ) ) {
		$fail( "Hero styles must not force {$forbidden_css}" );
	}
}

fwrite( STDOUT, "Editable GSWEB-15 Hero source contract passed.\n" );
