<?php
/** Assert the GSWEB-19 editable Contact source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-contact.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
$fail            = static function ( string $message ): never {
	fwrite( STDERR, "Contact contract failed: {$message}\n" );
	exit( 1 );
};
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	$fail( 'theme directory is unavailable' );
}
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

$pattern     = $read( 'patterns/contact.php' );
$front_page = $read( 'templates/front-page.html' );
$style_css   = $read( 'style.css' );

foreach ( array( 'Title: Gama Software Contact', 'Slug: gama-software/contact', 'Inserter: yes' ) as $metadata ) {
	if ( ! str_contains( $pattern, $metadata ) ) {
		$fail( "pattern metadata misses {$metadata}" );
	}
}
foreach ( array( 'anchor":"contact', 'gama-contact', 'Kontakt', 'mailto:founders@gama-software.com', 'gama-contact__form-slot', 'gama-contact__form-placeholder' ) as $required ) {
	if ( ! str_contains( $pattern, $required ) || ! str_contains( $front_page, $required ) ) {
		$fail( "pattern or front page misses {$required}" );
	}
}
if ( str_contains( $front_page, '<!-- wp:pattern {"slug":"gama-software/contact"} /-->' ) ) {
	$fail( 'front-page Contact must be direct editable Core blocks' );
}
if ( str_contains( $front_page, 'templateLock' ) || str_contains( $front_page, 'wp:html' ) ) {
	$fail( 'Contact content must stay unlocked and avoid raw HTML blocks' );
}
foreach ( array( '.gama-contact {', '.gama-contact__card {', '.gama-contact__form-slot {' ) as $required_css ) {
	if ( ! str_contains( $style_css, $required_css ) ) {
		$fail( "style.css misses {$required_css}" );
	}
}
$blog    = strpos( $front_page, '<section id="blog"' );
$contact = strpos( $front_page, '<section id="contact"' );
$content = strpos( $front_page, '<!-- wp:post-content' );
if ( false === $blog || false === $contact || false === $content || $blog > $contact || $contact > $content ) {
	$fail( 'front-page must render Contact after Blog and before page content' );
}

fwrite( STDOUT, "Editable GSWEB-19 Contact source contract passed.\n" );
