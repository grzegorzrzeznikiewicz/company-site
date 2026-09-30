<?php
/** Assert the exact GSWEB-14 header, navigation and footer source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-header-footer.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Header/footer contract failed: {$message}\n" );
	exit( 1 );
};
$read = static function ( string $relative_path ) use ( $theme_directory, $fail ): string {
	$path = realpath( $theme_directory . DIRECTORY_SEPARATOR . $relative_path );
	if ( false === $path || ! str_starts_with( $path, $theme_directory . DIRECTORY_SEPARATOR ) ) {
		$fail( "missing or escaped file {$relative_path}" );
	}
	$content = file_get_contents( $path );
	if ( false === $content ) {
		$fail( "could not read {$relative_path}" );
	}
	return $content;
};

/**
 * Parse serialized block comments into a flat, parent-indexed tree.
 *
 * This deliberately validates the theme's stored source. The installed-ZIP
 * lifecycle separately parses the same files with WordPress Core.
 *
 * @return array<int, array{name:string, attrs:array<string, mixed>, parent:int|null}>
 */
$parse = static function ( string $source, string $name ) use ( $fail ): array {
	$matched = preg_match_all(
		'/<!--\s+(\/?)wp:([a-z0-9-]+(?:\/[a-z0-9-]+)?)(?:\s+(\{[^\r\n]*\}))?\s*(\/?)-->/i',
		$source,
		$matches,
		PREG_SET_ORDER
	);
	if ( false === $matched || 0 === $matched ) {
		$fail( "{$name} contains no serialized blocks" );
	}

	$nodes = array();
	$stack = array();
	foreach ( $matches as $match ) {
		$is_closing = '/' === $match[1];
		$block_name = str_contains( $match[2], '/' ) ? $match[2] : 'core/' . $match[2];
		if ( $is_closing ) {
			$open = array_pop( $stack );
			if ( ! is_int( $open ) || $nodes[ $open ]['name'] !== $block_name ) {
				$fail( "{$name} has mismatched closing block {$block_name}" );
			}
			continue;
		}

		$attributes = array();
		if ( isset( $match[3] ) && '' !== $match[3] ) {
			try {
				$decoded = json_decode( $match[3], true, 512, JSON_THROW_ON_ERROR );
			} catch ( JsonException $exception ) {
				$fail( "{$name} has invalid block JSON: " . $exception->getMessage() );
			}
			if ( ! is_array( $decoded ) ) {
				$fail( "{$name} has non-object block attributes" );
			}
			$attributes = $decoded;
		}

		$index   = count( $nodes );
		$nodes[] = array(
			'name'   => $block_name,
			'attrs'  => $attributes,
			'parent' => [] === $stack ? null : $stack[ array_key_last( $stack ) ],
		);
		$is_self_closing = isset( $match[4] ) && '/' === $match[4];
		if ( ! $is_self_closing ) {
			$stack[] = $index;
		}
	}
	if ( array() !== $stack ) {
		$fail( "{$name} has unclosed serialized blocks" );
	}
	return $nodes;
};

$children = static fn( array $nodes, int $parent ): array => array_values(
	array_filter( $nodes, static fn( array $node ): bool => $node['parent'] === $parent )
);
$indexes = static fn( array $nodes, int|null $parent ): array => array_keys(
	array_filter( $nodes, static fn( array $node ): bool => $node['parent'] === $parent )
);

$header_source = $read( 'parts/header.html' );
$footer_source = $read( 'parts/footer.html' );
$combined_parts = $header_source . "\n" . $footer_source;
if ( preg_match( '/<script\b|\bonclick\s*=|wp_nav_menu|register_nav_menus|href\s*=\s*["\']#(?:["\']|\s)|"url"\s*:\s*"#"/i', $combined_parts ) ) {
	$fail( 'parts contain executable, legacy-menu or placeholder-link markup' );
}
if ( preg_match( '/Polityka prywatności|Regulamin/u', $footer_source ) ) {
	$fail( 'unapproved legal links must remain deferred to GSWEB-21' );
}
if ( preg_match( '/"tagName"\s*:\s*"(?:header|footer)"/i', $combined_parts ) ) {
	$fail( 'inner groups must not duplicate semantic template-part landmarks' );
}

$header = $parse( $header_source, 'parts/header.html' );
$header_roots = $indexes( $header, null );
if ( 1 !== count( $header_roots ) || 'core/group' !== $header[ $header_roots[0] ]['name'] ) {
	$fail( 'header must have exactly one root Group' );
}
$header_root = $header_roots[0];
if ( array(
	'className' => 'gama-site-header__surface',
	'layout'    => array( 'type' => 'constrained' ),
) !== $header[ $header_root ]['attrs'] ) {
	$fail( 'header surface Group differs from the neutral constrained contract' );
}
$header_root_children = $indexes( $header, $header_root );
if ( 1 !== count( $header_root_children ) ) {
	$fail( 'header surface must contain exactly one inner Group' );
}
$header_inner = $header_root_children[0];
if ( 'core/group' !== $header[ $header_inner ]['name'] || array(
	'align'     => 'wide',
	'className' => 'gama-site-header__inner',
	'layout'    => array(
		'type'           => 'flex',
		'flexWrap'       => 'nowrap',
		'justifyContent' => 'space-between',
	),
) !== $header[ $header_inner ]['attrs'] ) {
	$fail( 'header inner Group differs from the approved alignwide flex contract' );
}
$header_items = $indexes( $header, $header_inner );
if ( 2 !== count( $header_items ) ) {
	$fail( 'header inner Group must contain only Site Logo and Navigation' );
}
list( $header_logo, $primary_navigation ) = $header_items;
if ( 'core/site-logo' !== $header[ $header_logo ]['name'] || array( 'isLink' => true ) !== $header[ $header_logo ]['attrs'] ) {
	$fail( 'header Site Logo must link to the homepage without a bundled media URL' );
}
$primary_attributes = $header[ $primary_navigation ]['attrs'];
$required_primary = array(
	'ariaLabel'         => 'Główna nawigacja',
	'overlayMenu'       => 'mobile',
	'submenuVisibility' => 'click',
	'hasIcon'           => true,
	'icon'              => 'handle',
	'className'         => 'gama-primary-navigation',
);
if ( 'core/navigation' !== $header[ $primary_navigation ]['name'] ) {
	$fail( 'header must use Core Navigation' );
}
foreach ( $required_primary as $key => $value ) {
	if ( $value !== ( $primary_attributes[ $key ] ?? null ) ) {
		$fail( "primary Navigation attribute {$key} differs" );
	}
}
if ( array_key_exists( 'templateLock', $primary_attributes ) ) {
	$fail( 'primary Navigation must not set templateLock' );
}
$primary_items = $children( $header, $primary_navigation );
$expected_primary = array(
	array( 'Start', 'custom', '/#home', 'custom', true ),
	array( 'Usługi', 'custom', '/#services', 'custom', true ),
	array( 'Moduły', 'custom', '/#modules', 'custom', true ),
	array( 'Blog', 'custom', '/blog/', 'custom', true ),
	array( 'Kontakt', 'custom', '/#contact', 'custom', true ),
);
if ( count( $expected_primary ) !== count( $primary_items ) ) {
	$fail( 'primary Navigation must contain exactly five top-level links' );
}
foreach ( $expected_primary as $offset => list( $label, $type, $url, $kind, $is_top_level ) ) {
	$node = $primary_items[ $offset ];
	if ( 'core/navigation-link' !== $node['name'] || array(
		'label'          => $label,
		'type'           => $type,
		'url'            => $url,
		'kind'           => $kind,
		'isTopLevelLink' => $is_top_level,
	) !== $node['attrs'] ) {
		$fail( "primary Navigation item {$offset} differs" );
	}
}

$footer = $parse( $footer_source, 'parts/footer.html' );
$footer_roots = $indexes( $footer, null );
if ( 1 !== count( $footer_roots ) || 'core/group' !== $footer[ $footer_roots[0] ]['name'] ) {
	$fail( 'footer must have exactly one root Group' );
}
$footer_root = $footer_roots[0];
if ( array(
	'className'      => 'gama-site-footer__surface',
	'backgroundColor' => 'surface-inverse',
	'textColor'       => 'text-on-dark-muted',
	'layout'          => array( 'type' => 'constrained' ),
) !== $footer[ $footer_root ]['attrs'] ) {
	$fail( 'footer surface Group differs from the approved neutral contract' );
}
$footer_root_children = $indexes( $footer, $footer_root );
if ( 1 !== count( $footer_root_children ) ) {
	$fail( 'footer surface must contain exactly one inner Group' );
}
$footer_inner = $footer_root_children[0];
if ( 'core/group' !== $footer[ $footer_inner ]['name'] || array(
	'align'     => 'wide',
	'className' => 'gama-site-footer__inner',
	'layout'    => array(
		'type'           => 'flex',
		'flexWrap'       => 'wrap',
		'justifyContent' => 'space-between',
	),
) !== $footer[ $footer_inner ]['attrs'] ) {
	$fail( 'footer inner Group differs from the approved wrapping flex contract' );
}
$footer_items = $indexes( $footer, $footer_inner );
if ( 3 !== count( $footer_items ) ) {
	$fail( 'footer must contain exactly Site Logo, copyright and auxiliary Navigation' );
}
list( $footer_logo, $copyright, $auxiliary_navigation ) = $footer_items;
if ( 'core/site-logo' !== $footer[ $footer_logo ]['name'] || array( 'isLink' => true ) !== $footer[ $footer_logo ]['attrs'] ) {
	$fail( 'footer Site Logo must link to the homepage without a bundled media URL' );
}
if ( 'core/paragraph' !== $footer[ $copyright ]['name'] || ! str_contains( $footer_source, '<p>© 2026 Gama Software. Wszystkie prawa zastrzeżone.</p>' ) ) {
	$fail( 'footer copyright must be the approved editable Paragraph' );
}
if ( 'core/navigation' !== $footer[ $auxiliary_navigation ]['name'] || array(
	'ariaLabel'   => 'Nawigacja pomocnicza',
	'overlayMenu' => 'never',
	'className'   => 'gama-footer-navigation',
) !== $footer[ $auxiliary_navigation ]['attrs'] ) {
	$fail( 'auxiliary Navigation differs from the approved contract' );
}
$auxiliary_items = $children( $footer, $auxiliary_navigation );
if ( array(
	array(
		'name'   => 'core/navigation-link',
		'attrs'  => array(
			'label'          => 'Kontakt',
			'type'           => 'custom',
			'url'            => '/#contact',
			'kind'           => 'custom',
			'isTopLevelLink' => true,
		),
		'parent' => $auxiliary_navigation,
	),
) !== $auxiliary_items ) {
	$fail( 'auxiliary Navigation must contain only the real Contact URL' );
}

foreach ( array( 'index', 'front-page', 'page', 'single', 'home', 'archive', 'search', '404' ) as $slug ) {
	$source = $read( "templates/{$slug}.html" );
	if ( str_contains( $source, 'wp-skip-link' ) || str_contains( $source, '#main-content' ) ) {
		$fail( "template {$slug} must rely on the single Core skip-link" );
	}
	$nodes = $parse( $source, "templates/{$slug}.html" );
	$roots = $indexes( $nodes, null );
	if ( 3 !== count( $roots ) ) {
		$fail( "template {$slug} must have exactly header, main and footer roots" );
	}
	$header_reference = $nodes[ $roots[0] ];
	$main             = $nodes[ $roots[1] ];
	$footer_reference = $nodes[ $roots[2] ];
	if ( 'core/template-part' !== $header_reference['name'] || array(
		'slug'      => 'header',
		'theme'     => 'gama-software',
		'className' => 'gama-site-header',
	) !== $header_reference['attrs'] ) {
		$fail( "template {$slug} has the wrong header reference" );
	}
	if ( 'core/group' !== $main['name'] || 'main' !== ( $main['attrs']['tagName'] ?? null ) ) {
		$fail( "template {$slug} does not have one first semantic main Group" );
	}
	if ( 'core/template-part' !== $footer_reference['name'] || array(
		'slug'      => 'footer',
		'theme'     => 'gama-software',
		'className' => 'gama-site-footer',
	) !== $footer_reference['attrs'] ) {
		$fail( "template {$slug} has the wrong footer reference" );
	}
}

$style_css = $read( 'style.css' );
foreach ( array(
	'.gama-site-header',
	'position: sticky',
	'z-index: 99999',
	'.admin-bar .gama-site-header',
	'top: 32px',
	'top: 46px',
	'scroll-padding-top:',
	'scroll-margin-top:',
	'.gama-site-header__surface .wp-block-site-logo img',
	'.gama-site-footer__surface .wp-block-site-logo img',
	'.gama-site-footer__inner',
	'.gama-footer-navigation',
	'@media (min-width: 600px) and (max-width: 767px)',
	'.gama-primary-navigation.wp-block-navigation .wp-block-navigation__responsive-container:not(.is-menu-open)',
	'.gama-primary-navigation.wp-block-navigation .wp-block-navigation__responsive-container-open:not(.always-shown)',
) as $required_css ) {
	if ( ! str_contains( $style_css, $required_css ) ) {
		$fail( "style.css misses {$required_css}" );
	}
}
if ( preg_match( '/filter\s*:|scroll-behavior\s*:\s*smooth|animation\s*:|\.has-modal-open|\.is-menu-open\s*\{/i', $style_css ) ) {
	$fail( 'theme must not filter logos, force motion or override Core overlay state' );
}

fwrite( STDOUT, "Exact GSWEB-14 header/footer source contract passed.\n" );
