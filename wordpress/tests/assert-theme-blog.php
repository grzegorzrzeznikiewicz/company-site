<?php
/** Assert the GSWEB-18 native blog source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-blog.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Blog contract failed: {$message}\n" );
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

$front_page = $read( 'templates/front-page.html' );
$home       = $read( 'templates/home.html' );
$archive    = $read( 'templates/archive.html' );
$single     = $read( 'templates/single.html' );
$article    = $read( 'patterns/article.php' );
$style_css  = $read( 'style.css' );

foreach ( array( $home, $archive ) as $query_template ) {
	foreach ( array( 'wp:query', 'wp:post-template', 'wp:post-title', 'wp:post-date', 'wp:post-excerpt', 'wp:query-pagination', 'wp:query-no-results' ) as $block ) {
		if ( ! str_contains( $query_template, $block ) ) {
			$fail( "archive query misses {$block}" );
		}
	}
}

foreach ( array( 'anchor":"blog', 'gama-blog-latest', '"inherit":false', '"perPage":3', 'Wszystkie artykuły', 'href="/blog/"' ) as $required ) {
	if ( ! str_contains( $front_page, $required ) ) {
		$fail( "front-page latest-post section misses {$required}" );
	}
}
if ( substr_count( $front_page, '<section id="blog"' ) !== 1 ) {
	$fail( 'front-page must contain one semantic Blog section' );
}
if ( ! str_contains( $front_page, 'wp:query-no-results' ) || ! str_contains( $front_page, 'W budowie' ) ) {
	$fail( 'homepage blog must have an intentional empty state' );
}

foreach ( array( 'tagName":"article', 'wp:post-title', '"level":1', 'wp:post-date', 'wp:post-terms', 'wp:post-featured-image', 'wp:post-content', 'wp:post-navigation-link' ) as $required ) {
	if ( ! str_contains( $single, $required ) ) {
		$fail( "single article template misses {$required}" );
	}
}
if ( str_contains( $single, 'wp:comments' ) || str_contains( $single, 'wp:post-comments' ) ) {
	$fail( 'comments are outside the accepted scope' );
}

foreach ( array( 'Title: Gama Software Article', 'Slug: gama-software/article', 'Inserter: yes', 'wp:heading', 'wp:quote' ) as $required ) {
	if ( ! str_contains( $article, $required ) ) {
		$fail( "article starter pattern misses {$required}" );
	}
}

foreach ( array( '.gama-blog-latest {', '.gama-post-grid {', '.gama-post-card {', '.gama-blog-empty {', '.gama-article {', 'repeat(auto-fit', 'overflow-wrap: anywhere' ) as $required ) {
	if ( ! str_contains( $style_css, $required ) ) {
		$fail( "responsive blog CSS misses {$required}" );
	}
}

$modules = strpos( $front_page, '<section id="modules"' );
$blog    = strpos( $front_page, '<section id="blog"' );
$content = strpos( $front_page, '<!-- wp:post-content' );
if ( false === $modules || false === $blog || false === $content || $modules > $blog || $blog > $content ) {
	$fail( 'front-page must render Blog after Modules and before page content' );
}

fwrite( STDOUT, "Native GSWEB-18 blog source contract passed.\n" );
