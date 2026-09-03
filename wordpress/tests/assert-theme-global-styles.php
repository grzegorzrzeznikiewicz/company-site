<?php
/** Assert the exact GSWEB-13 Global Styles source contract. */

declare(strict_types=1);

if ( 2 !== $argc ) {
	fwrite( STDERR, "Usage: assert-theme-global-styles.php <theme-directory>\n" );
	exit( 64 );
}

$theme_directory = realpath( $argv[1] );
if ( false === $theme_directory || ! is_dir( $theme_directory ) ) {
	fwrite( STDERR, "Theme directory is unavailable.\n" );
	exit( 1 );
}

$fail = static function ( string $message ): never {
	fwrite( STDERR, "Global Styles contract failed: {$message}\n" );
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

try {
	$theme = json_decode( $read( 'theme.json' ), true, 512, JSON_THROW_ON_ERROR );
} catch ( JsonException $exception ) {
	$fail( 'theme.json is not valid JSON: ' . $exception->getMessage() );
}

$expected_palette = array(
	array( 'slug' => 'base', 'color' => '#ffffff', 'name' => 'Base' ),
	array( 'slug' => 'surface-subtle', 'color' => '#f9fafb', 'name' => 'Subtle surface' ),
	array( 'slug' => 'border-subtle', 'color' => '#e5e7eb', 'name' => 'Subtle border' ),
	array( 'slug' => 'text-strong', 'color' => '#101828', 'name' => 'Strong text' ),
	array( 'slug' => 'text', 'color' => '#364153', 'name' => 'Text' ),
	array( 'slug' => 'text-muted', 'color' => '#4a5565', 'name' => 'Muted text' ),
	array( 'slug' => 'text-card-muted', 'color' => '#717182', 'name' => 'Muted card text' ),
	array( 'slug' => 'text-on-dark-muted', 'color' => '#99a1af', 'name' => 'Muted text on dark' ),
	array( 'slug' => 'surface-inverse', 'color' => '#101828', 'name' => 'Inverse surface' ),
	array( 'slug' => 'accent-soft', 'color' => '#dbeafe', 'name' => 'Soft accent' ),
	array( 'slug' => 'accent', 'color' => '#155dfc', 'name' => 'Accent' ),
);
$expected_font_sizes = array(
	array( 'slug' => 'small', 'size' => '.875rem', 'name' => 'Small' ),
	array( 'slug' => 'body', 'size' => '1rem', 'name' => 'Body' ),
	array( 'slug' => 'button', 'size' => '1.125rem', 'name' => 'Button' ),
	array( 'slug' => 'lead', 'size' => '1.25rem', 'name' => 'Lead' ),
	array( 'slug' => 'heading-3', 'size' => '1.5rem', 'name' => 'Heading 3' ),
	array( 'slug' => 'heading-2', 'size' => '2.25rem', 'name' => 'Heading 2' ),
	array( 'slug' => 'display', 'size' => '3rem', 'name' => 'Display' ),
	array( 'slug' => 'display-large', 'size' => '3.75rem', 'name' => 'Display large' ),
);
$expected_spacing = array(
	array( 'slug' => 'sm', 'size' => '.5rem', 'name' => 'Small' ),
	array( 'slug' => 'md', 'size' => '1rem', 'name' => 'Medium' ),
	array( 'slug' => 'lg', 'size' => '1.5rem', 'name' => 'Large' ),
	array( 'slug' => 'xl', 'size' => '2rem', 'name' => 'Extra large' ),
	array( 'slug' => 'xxl', 'size' => '3rem', 'name' => '2X large' ),
	array( 'slug' => 'section', 'size' => '5rem', 'name' => 'Section' ),
);
$expected_shadows = array(
	array( 'slug' => 'elevation-1', 'shadow' => '0 4px 6px -1px rgb(0 0 0 / .1), 0 2px 4px -2px rgb(0 0 0 / .1)', 'name' => 'Elevation 1' ),
	array( 'slug' => 'elevation-2', 'shadow' => '0 10px 15px -3px rgb(0 0 0 / .1), 0 4px 6px -4px rgb(0 0 0 / .1)', 'name' => 'Elevation 2' ),
	array( 'slug' => 'elevation-3', 'shadow' => '0 20px 25px -5px rgb(0 0 0 / .1), 0 8px 10px -6px rgb(0 0 0 / .1)', 'name' => 'Elevation 3' ),
);

$settings = $theme['settings'] ?? null;
$styles   = $theme['styles'] ?? null;
if ( ! is_array( $settings ) || ! is_array( $styles ) ) {
	$fail( 'settings or styles is missing' );
}
if ( false !== ( $settings['appearanceTools'] ?? null ) ) {
	$fail( 'appearanceTools must be false' );
}
if ( $expected_palette !== ( $settings['color']['palette'] ?? null ) ) {
	$fail( 'editor palette differs from the approved ordered palette' );
}
foreach ( array( 'custom', 'defaultPalette', 'customGradient', 'defaultGradients', 'customDuotone', 'defaultDuotone' ) as $key ) {
	if ( false !== ( $settings['color'][ $key ] ?? null ) ) {
		$fail( "settings.color.{$key} must be false" );
	}
}
if ( array() !== ( $settings['color']['gradients'] ?? null ) || array() !== ( $settings['color']['duotone'] ?? null ) ) {
	$fail( 'gradient and duotone preset lists must be explicitly empty' );
}
if ( '#1447e6' !== ( $settings['custom']['color']['accentHover'] ?? null ) ) {
	$fail( 'accentHover custom token differs' );
}
if ( array( 'button' => '.5rem', 'icon' => '.625rem', 'card' => '.875rem' ) !== ( $settings['custom']['radius'] ?? null ) ) {
	$fail( 'radius custom tokens differ' );
}

$expected_family = array(
	array(
		'slug'       => 'system-sans',
		'fontFamily' => 'ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"',
		'name'       => 'System sans',
	),
);
if ( $expected_family !== ( $settings['typography']['fontFamilies'] ?? null ) ) {
	$fail( 'system-sans must be the only font family' );
}
if ( $expected_font_sizes !== ( $settings['typography']['fontSizes'] ?? null ) ) {
	$fail( 'font-size presets differ' );
}
foreach ( array( 'defaultFontSizes', 'customFontSize', 'fontStyle', 'fontWeight', 'letterSpacing', 'lineHeight' ) as $key ) {
	if ( false !== ( $settings['typography'][ $key ] ?? null ) ) {
		$fail( "settings.typography.{$key} must be false" );
	}
}
if ( str_contains( strtolower( json_encode( $settings['typography'], JSON_THROW_ON_ERROR ) ), 'fontface' ) ) {
	$fail( 'fontFace is forbidden' );
}

if ( $expected_spacing !== ( $settings['spacing']['spacingSizes'] ?? null ) ) {
	$fail( 'spacing presets differ' );
}
if ( true !== ( $settings['spacing']['blockGap'] ?? null )
	|| false !== ( $settings['spacing']['defaultSpacingSizes'] ?? null )
	|| false !== ( $settings['spacing']['customSpacingSize'] ?? null )
	|| true !== ( $settings['spacing']['margin'] ?? null )
	|| true !== ( $settings['spacing']['padding'] ?? null )
	|| array( 'px', 'rem', '%' ) !== ( $settings['spacing']['units'] ?? null ) ) {
	$fail( 'spacing controls differ' );
}
if ( false !== ( $settings['layout']['allowCustomContentAndWideSize'] ?? null )
	|| '70rem' !== ( $settings['layout']['contentSize'] ?? null )
	|| '80rem' !== ( $settings['layout']['wideSize'] ?? null )
	|| true !== ( $settings['useRootPaddingAwareAlignments'] ?? null ) ) {
	$fail( 'layout controls differ' );
}
if ( false !== ( $settings['shadow']['defaultPresets'] ?? null ) || $expected_shadows !== ( $settings['shadow']['presets'] ?? null ) ) {
	$fail( 'shadow presets differ' );
}

$expected_root_styles = array(
	'color'      => array(
		'background' => 'var:preset|color|base',
		'text'       => 'var:preset|color|text',
	),
	'spacing'    => array(
		'blockGap' => 'var:preset|spacing|md',
		'padding'  => array(
			'top'    => '0',
			'right'  => 'var:preset|spacing|md',
			'bottom' => '0',
			'left'   => 'var:preset|spacing|md',
		),
	),
	'typography' => array(
		'fontFamily' => 'var:preset|font-family|system-sans',
		'fontSize'   => 'var:preset|font-size|body',
		'fontWeight' => '400',
		'lineHeight' => '1.5rem',
	),
);
foreach ( $expected_root_styles as $key => $expected ) {
	if ( $expected !== ( $styles[ $key ] ?? null ) ) {
		$fail( "root {$key} styles differ" );
	}
}
$elements = $styles['elements'] ?? array();
if ( array( 'color' => array( 'text' => 'var:preset|color|text-strong' ), 'typography' => array( 'fontWeight' => '500' ) ) !== ( $elements['heading'] ?? null ) ) {
	$fail( 'heading defaults differ' );
}
$semantic_headings = array(
	'h1' => array( 'display', '1' ),
	'h2' => array( 'heading-2', '2.5rem' ),
	'h3' => array( 'heading-3', '2rem' ),
);
foreach ( $semantic_headings as $element => list( $size, $line_height ) ) {
	$expected = array( 'typography' => array( 'fontSize' => "var:preset|font-size|{$size}", 'lineHeight' => $line_height ) );
	if ( $expected !== ( $elements[ $element ] ?? null ) ) {
		$fail( "{$element} semantic typography differs" );
	}
}
$expected_link = array(
	'color'  => array( 'text' => 'var:preset|color|accent' ),
	':hover' => array( 'color' => array( 'text' => 'var:custom|color|accent-hover' ) ),
);
if ( $expected_link !== ( $elements['link'] ?? null ) ) {
	$fail( 'link styles differ' );
}
$expected_button = array(
	'border'     => array( 'radius' => 'var:custom|radius|button' ),
	'color'      => array( 'background' => 'var:preset|color|accent', 'text' => 'var:preset|color|base' ),
	'typography' => array( 'fontSize' => 'var:preset|font-size|button', 'fontWeight' => '500', 'lineHeight' => '1.75rem' ),
	':hover'     => array( 'color' => array( 'background' => 'var:custom|color|accent-hover', 'text' => 'var:preset|color|base' ) ),
);
if ( $expected_button !== ( $elements['button'] ?? null ) ) {
	$fail( 'button styles differ' );
}
foreach ( array( 'core/group', 'core/columns' ) as $block ) {
	if ( isset( $styles['blocks'][ $block ]['border']['radius'] ) || isset( $styles['blocks'][ $block ]['shadow'] ) ) {
		$fail( "{$block} received a global card radius or shadow" );
	}
}

$style_css = $read( 'style.css' );
$required_css = array(
	'outline: 3px solid var(--wp--preset--color--accent)',
	'outline-offset: 3px',
	'box-shadow: 0 0 0 2px var(--wp--preset--color--base)',
	'max-width: 100%',
	'height: auto',
	'overflow-wrap: anywhere',
	'.has-small-font-size',
	'.has-body-font-size',
	'.has-button-font-size',
	'.has-lead-font-size',
	'.has-heading-3-font-size',
	'.has-heading-2-font-size',
	'.has-display-font-size',
	'.has-display-large-font-size',
	'@media (min-width: 768px)',
	'--wp--preset--font-size--display: 3.75rem',
	'--wp--preset--font-size--lead: 1.5rem',
	'--wp--style--root--padding-right: 1.5rem',
	'--wp--style--root--padding-left: 1.5rem',
	'@media (min-width: 1024px)',
	'--wp--style--root--padding-right: 2rem',
	'--wp--style--root--padding-left: 2rem',
);
foreach ( $required_css as $fragment ) {
	if ( ! str_contains( $style_css, $fragment ) ) {
		$fail( "style.css misses {$fragment}" );
	}
}
foreach ( array( 'overflow-x: hidden', 'outline: none', '@font-face', 'linear-gradient', 'radial-gradient', 'animation:' ) as $forbidden ) {
	if ( str_contains( strtolower( $style_css ), strtolower( $forbidden ) ) ) {
		$fail( "style.css contains forbidden fragment {$forbidden}" );
	}
}
if ( ! preg_match( '/Version:\s*0\.2\.0\b/', $style_css )
	|| ! str_contains( $read( 'README.md' ), 'Version 0.2.0' )
	|| ! str_contains( $read( 'CHANGELOG.md' ), '## 0.2.0 - 2026-09-03' )
	|| ! str_contains( $read( 'languages/gama-software.pot' ), 'Project-Id-Version: Gama Software 0.2.0' ) ) {
	$fail( 'theme version metadata is not consistently 0.2.0' );
}

$all_source = '';
$iterator   = new RecursiveIteratorIterator( new RecursiveDirectoryIterator( $theme_directory, FilesystemIterator::SKIP_DOTS ) );
foreach ( $iterator as $file ) {
	if ( $file->isFile() && in_array( strtolower( $file->getExtension() ), array( 'css', 'html', 'json', 'php' ), true ) ) {
		$all_source .= "\n" . file_get_contents( $file->getPathname() );
	}
}
if ( preg_match( '/tailwind|material[ -]?ui|lucide|motion\/react|@font-face|fonts\.(googleapis|gstatic)\.com/i', $all_source ) ) {
	$fail( 'theme contains a forbidden framework, motion, icon, or remote-font dependency' );
}

$relative_luminance = static function ( string $hex ): float {
	$channels = sscanf( ltrim( $hex, '#' ), '%02x%02x%02x' );
	$linear   = array_map(
		static function ( int $channel ): float {
			$value = $channel / 255;
			return $value <= 0.04045 ? $value / 12.92 : ( ( $value + 0.055 ) / 1.055 ) ** 2.4;
		},
		$channels
	);
	return 0.2126 * $linear[0] + 0.7152 * $linear[1] + 0.0722 * $linear[2];
};
$contrast = static function ( string $a, string $b ) use ( $relative_luminance ): float {
	$luminances = array( $relative_luminance( $a ), $relative_luminance( $b ) );
	return ( max( $luminances ) + 0.05 ) / ( min( $luminances ) + 0.05 );
};
foreach ( array(
	array( '#101828', '#ffffff', 4.5 ),
	array( '#4a5565', '#ffffff', 4.5 ),
	array( '#717182', '#ffffff', 4.5 ),
	array( '#ffffff', '#155dfc', 4.5 ),
	array( '#99a1af', '#101828', 4.5 ),
	array( '#155dfc', '#ffffff', 3.0 ),
) as list( $foreground, $background, $minimum ) ) {
	$ratio = $contrast( $foreground, $background );
	if ( $ratio < $minimum ) {
		$fail( "contrast {$foreground} on {$background} is {$ratio}, below {$minimum}" );
	}
}

fwrite( STDOUT, "Exact GSWEB-13 Global Styles source contract passed.\n" );
