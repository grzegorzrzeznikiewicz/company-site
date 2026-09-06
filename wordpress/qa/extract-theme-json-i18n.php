<?php
/** Create a deterministic POT seed from the official WordPress i18n map. */

declare(strict_types=1);

if ( 4 !== $argc ) {
	fwrite( STDERR, "Usage: extract-theme-json-i18n.php <theme.json> <theme-i18n.json> <output.pot>\n" );
	exit( 64 );
}
$theme   = json_decode( (string) file_get_contents( $argv[1] ), true, 512, JSON_THROW_ON_ERROR );
$mapping = json_decode( (string) file_get_contents( $argv[2] ), true, 512, JSON_THROW_ON_ERROR );
$paths = array(
	array( array( 'templateParts' ), 'title', 'Template part name' ),
	array( array( 'settings', 'color', 'palette' ), 'name', 'Color name' ),
	array( array( 'settings', 'typography', 'fontFamilies' ), 'name', 'Font family name' ),
	array( array( 'settings', 'typography', 'fontSizes' ), 'name', 'Font size name' ),
	array( array( 'settings', 'spacing', 'spacingSizes' ), 'name', 'Space size name' ),
	array( array( 'settings', 'shadow', 'presets' ), 'name', 'Shadow name' ),
);
$messages = array();
foreach ( $paths as list( $segments, $value_key, $expected_context ) ) {
	$mapping_cursor = $mapping;
	$theme_cursor   = $theme;
	foreach ( $segments as $segment ) {
		$mapping_cursor = $mapping_cursor[ $segment ] ?? null;
		$theme_cursor   = $theme_cursor[ $segment ] ?? null;
	}
	$mapping_context = is_array( $mapping_cursor ) ? ( $mapping_cursor[0][ $value_key ] ?? null ) : null;
	if ( $expected_context !== $mapping_context || ! is_array( $theme_cursor ) ) {
		fwrite( STDERR, "Official WordPress i18n map or theme data lacks {$expected_context}.\n" );
		exit( 1 );
	}
	foreach ( $theme_cursor as $item ) {
		$message = $item[ $value_key ] ?? null;
		if ( is_string( $message ) && '' !== $message ) {
			$messages[ $expected_context . "\0" . $message ] = array( $expected_context, $message );
		}
	}
}
$template_messages = array_values(
	array_map(
		static fn( array $message ): string => $message[1],
		array_filter( $messages, static fn( array $message ): bool => 'Template part name' === $message[0] )
	)
);
sort( $template_messages, SORT_STRING );
if ( array( 'Footer', 'Header' ) !== $template_messages ) {
	fwrite( STDERR, "Expected the exact Header/Footer template-part titles.\n" );
	exit( 1 );
}
ksort( $messages, SORT_STRING );
$escape = static fn( string $value ): string => addcslashes( $value, "\\\"\n\r\t" );
$pot    = "msgid \"\"\nmsgstr \"\"\n\"Content-Type: text/plain; charset=UTF-8\\n\"\n\n";
foreach ( $messages as list( $context, $message ) ) {
	$pot .= "#: theme.json\nmsgctxt \"{$escape( $context )}\"\nmsgid \"{$escape( $message )}\"\nmsgstr \"\"\n\n";
}
if ( false === file_put_contents( $argv[3], $pot ) ) {
	fwrite( STDERR, "Could not write the deterministic theme.json POT seed.\n" );
	exit( 1 );
}
fwrite( STDOUT, "Extracted Global Styles and template-part labels using the vendored WordPress 7.1 i18n map.\n" );
