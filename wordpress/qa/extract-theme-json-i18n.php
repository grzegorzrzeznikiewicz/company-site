<?php
/** Create a deterministic POT seed from the official WordPress i18n map. */

declare(strict_types=1);

if ( 4 !== $argc ) {
	fwrite( STDERR, "Usage: extract-theme-json-i18n.php <theme.json> <theme-i18n.json> <output.pot>\n" );
	exit( 64 );
}
$theme   = json_decode( (string) file_get_contents( $argv[1] ), true, 512, JSON_THROW_ON_ERROR );
$mapping = json_decode( (string) file_get_contents( $argv[2] ), true, 512, JSON_THROW_ON_ERROR );
if ( 'Template part name' !== ( $mapping['templateParts'][0]['title'] ?? null ) ) {
	fwrite( STDERR, "Official WordPress i18n map lacks the template-parts title contract.\n" );
	exit( 1 );
}
$messages = array();
foreach ( $theme['templateParts'] ?? array() as $part ) {
	if ( isset( $part['title'] ) && is_string( $part['title'] ) && '' !== $part['title'] ) {
		$messages[] = $part['title'];
	}
}
$messages = array_values( array_unique( $messages ) );
sort( $messages, SORT_STRING );
if ( array( 'Footer', 'Header' ) !== $messages ) {
	fwrite( STDERR, "Expected the exact Header/Footer template-part titles.\n" );
	exit( 1 );
}
$escape = static fn( string $value ): string => addcslashes( $value, "\\\"\n\r\t" );
$pot    = "msgid \"\"\nmsgstr \"\"\n\"Content-Type: text/plain; charset=UTF-8\\n\"\n\n";
foreach ( $messages as $message ) {
	$pot .= "#: theme.json\nmsgctxt \"Template part name\"\nmsgid \"{$escape( $message )}\"\nmsgstr \"\"\n\n";
}
if ( false === file_put_contents( $argv[3], $pot ) ) {
	fwrite( STDERR, "Could not write the deterministic theme.json POT seed.\n" );
	exit( 1 );
}
fwrite( STDOUT, "Extracted template-part titles using the vendored WordPress 7.1 i18n map.\n" );
