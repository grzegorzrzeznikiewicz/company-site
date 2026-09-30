<?php

declare(strict_types=1);

/**
 * Validate only the JSON Schema keywords used by extensions.schema.json.
 *
 * This is intentionally not a general-purpose JSON Schema implementation.
 * Supported keywords: type, const, enum, properties, required,
 * additionalProperties=false, items, minLength, pattern, and format=uri.
 */

function gama_validate_extensions_fail(string $message): never
{
    fwrite(STDERR, "Extension lock validation failed: {$message}\n");
    exit(1);
}

function gama_validate_extensions_load(string $path): mixed
{
    $contents = @file_get_contents($path);
    if ($contents === false) {
        gama_validate_extensions_fail("cannot read {$path}");
    }

    try {
        return json_decode($contents, true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException $exception) {
        gama_validate_extensions_fail("{$path}: {$exception->getMessage()}");
    }
}

/** @param array<string, mixed> $schema */
function gama_validate_extensions_value(mixed $value, array $schema, string $location = '$'): void
{
    $type = $schema['type'] ?? null;
    $matches = match ($type) {
        'object' => is_array($value) && !array_is_list($value),
        'array' => is_array($value) && array_is_list($value),
        'string' => is_string($value),
        'integer' => is_int($value),
        default => gama_validate_extensions_fail("{$location}: unsupported schema type"),
    };
    if (!$matches) {
        gama_validate_extensions_fail("{$location}: expected {$type}");
    }

    if (array_key_exists('const', $schema) && $value !== $schema['const']) {
        gama_validate_extensions_fail("{$location}: value does not match const");
    }
    if (isset($schema['enum']) && !in_array($value, $schema['enum'], true)) {
        gama_validate_extensions_fail("{$location}: value is not in the allowed enum");
    }

    if ($type === 'object') {
        $properties = $schema['properties'] ?? null;
        $required = $schema['required'] ?? null;
        if (!is_array($properties) || !is_array($required)) {
            gama_validate_extensions_fail("{$location}: object schema is incomplete");
        }
        foreach ($required as $name) {
            if (!is_string($name) || !array_key_exists($name, $value)) {
                gama_validate_extensions_fail("{$location}: missing required field {$name}");
            }
        }
        if (($schema['additionalProperties'] ?? null) === false) {
            $unknown = array_diff(array_keys($value), array_keys($properties));
            if ($unknown !== []) {
                gama_validate_extensions_fail("{$location}: unknown fields: " . implode(', ', $unknown));
            }
        }
        foreach ($value as $name => $child) {
            if (isset($properties[$name]) && is_array($properties[$name])) {
                gama_validate_extensions_value($child, $properties[$name], "{$location}.{$name}");
            }
        }
    }

    if ($type === 'array') {
        $itemSchema = $schema['items'] ?? null;
        if (!is_array($itemSchema)) {
            gama_validate_extensions_fail("{$location}: array schema has no supported items definition");
        }
        foreach ($value as $index => $item) {
            gama_validate_extensions_value($item, $itemSchema, "{$location}[{$index}]");
        }
    }

    if ($type === 'string') {
        if (isset($schema['minLength']) && strlen($value) < $schema['minLength']) {
            gama_validate_extensions_fail("{$location}: string is too short");
        }
        if (isset($schema['pattern']) && preg_match('/' . str_replace('/', '\\/', $schema['pattern']) . '/D', $value) !== 1) {
            gama_validate_extensions_fail("{$location}: value does not match the declared pattern");
        }
        if (($schema['format'] ?? null) === 'uri') {
            $scheme = parse_url($value, PHP_URL_SCHEME);
            $host = parse_url($value, PHP_URL_HOST);
            if (!in_array($scheme, ['http', 'https'], true) || !is_string($host) || $host === '') {
                gama_validate_extensions_fail("{$location}: expected an absolute HTTP(S) URI");
            }
        }
    }
}

if ($argc !== 3) {
    fwrite(STDERR, "Usage: validate-extensions-lock.php <schema> <lock>\n");
    exit(64);
}

$schema = gama_validate_extensions_load($argv[1]);
$lock = gama_validate_extensions_load($argv[2]);
if (!is_array($schema) || ($schema['$schema'] ?? null) !== 'https://json-schema.org/draft/2020-12/schema') {
    gama_validate_extensions_fail('schema must declare JSON Schema Draft 2020-12');
}

gama_validate_extensions_value($lock, $schema);
fwrite(STDOUT, "Validated {$argv[2]} against the closed Draft 2020-12 schema (supported subset).\n");
