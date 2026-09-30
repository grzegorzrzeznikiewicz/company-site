<?php
/**
 * Validate theme.json against the vendored WordPress Draft-07 schema.
 */

declare(strict_types=1);

use Opis\JsonSchema\CompliantValidator;

require __DIR__ . '/vendor/autoload.php';

if ( 3 !== $argc ) {
	fwrite( STDERR, "Usage: validate-theme-json.php <theme.json> <schema.json>\n" );
	exit( 64 );
}

$document_json = file_get_contents( $argv[1] );
$schema_json   = file_get_contents( $argv[2] );
if ( false === $document_json || false === $schema_json ) {
	fwrite( STDERR, "Could not read theme document or schema.\n" );
	exit( 1 );
}

try {
	$document = json_decode( $document_json, false, 512, JSON_THROW_ON_ERROR );
	$schema   = json_decode( $schema_json, false, 512, JSON_THROW_ON_ERROR );
} catch ( JsonException $exception ) {
	fwrite( STDERR, $exception->getMessage() . "\n" );
	exit( 1 );
}

if ( 'http://json-schema.org/draft-07/schema#' !== ( $schema->{'$schema'} ?? null ) ) {
	fwrite( STDERR, "Vendored schema does not declare Draft-07.\n" );
	exit( 1 );
}
if ( 'https://schemas.wp.org/wp/7.1/theme.json' !== ( $document->{'$schema'} ?? null ) ) {
	fwrite( STDERR, "theme.json does not target the exact WordPress 7.1 schema URL.\n" );
	exit( 1 );
}

$validator = new CompliantValidator();
$error     = $validator->dataValidation( $document, $schema, null, null, null, 'draft-07' );
if ( null !== $error ) {
	fwrite( STDERR, "theme.json failed WordPress 7.1 schema validation: {$error->message()}\n" );
	exit( 1 );
}

fwrite( STDOUT, "theme.json is valid against the vendored WordPress 7.1 Draft-07 schema.\n" );
