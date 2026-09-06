<?php

declare(strict_types=1);

function fail_contract(string $message): never
{
    fwrite(STDERR, "Package Compose contract failed: {$message}\n");
    exit(1);
}

$expectedPackageZip = getenv('EXPECTED_PACKAGE_ZIP');
if (!is_string($expectedPackageZip) || $expectedPackageZip === '') {
    fail_contract('EXPECTED_PACKAGE_ZIP is required');
}

try {
    $resolved = json_decode((string) stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
} catch (JsonException $exception) {
    fail_contract('resolved Compose output is not valid JSON: ' . $exception->getMessage());
}

if (!is_array($resolved) || !isset($resolved['services']) || !is_array($resolved['services'])) {
    fail_contract('resolved Compose output has no services object');
}

$expectedImages = [
    'db' => 'mariadb:10.11.18-jammy',
    'uploads-init' => 'wordpress:7.1.0-php8.4-apache',
    'wordpress' => 'wordpress:7.1.0-php8.4-apache',
    'wp' => 'wordpress:cli-2.12.0-php8.4',
];
$expectedMounts = [
    'db' => [
        ['type' => 'volume', 'source' => 'db-data', 'target' => '/var/lib/mysql', 'read_only' => false],
    ],
    'uploads-init' => [
        ['type' => 'volume', 'source' => 'uploads', 'target' => '/uploads', 'read_only' => false],
    ],
    'wordpress' => [
        ['type' => 'volume', 'source' => 'core', 'target' => '/var/www/html', 'read_only' => false],
        ['type' => 'volume', 'source' => 'uploads', 'target' => '/var/www/html/wp-content/uploads', 'read_only' => false],
    ],
    'wp' => [
        ['type' => 'volume', 'source' => 'core', 'target' => '/var/www/html', 'read_only' => false],
        ['type' => 'volume', 'source' => 'uploads', 'target' => '/var/www/html/wp-content/uploads', 'read_only' => false],
        ['type' => 'bind', 'source' => $expectedPackageZip, 'target' => '/package/gama-contact.zip', 'read_only' => true],
    ],
];

$actualServiceNames = array_keys($resolved['services']);
$expectedServiceNames = array_keys($expectedImages);
sort($actualServiceNames, SORT_STRING);
sort($expectedServiceNames, SORT_STRING);
if ($actualServiceNames !== $expectedServiceNames) {
    fail_contract('service set changed');
}

$actualBindMounts = [];
foreach ($expectedImages as $serviceName => $expectedImage) {
    $service = $resolved['services'][$serviceName];
    if (!is_array($service) || ($service['image'] ?? null) !== $expectedImage) {
        fail_contract("{$serviceName} image changed");
    }
    if (array_key_exists('ports', $service)) {
        fail_contract("{$serviceName} publishes ports");
    }

    $mounts = $service['volumes'] ?? [];
    if (!is_array($mounts)) {
        fail_contract("{$serviceName} volumes are not an array");
    }
    $normalized = [];
    foreach ($mounts as $mount) {
        if (!is_array($mount)) {
            fail_contract("{$serviceName} contains a malformed mount");
        }
        $normalizedMount = [
            'type' => $mount['type'] ?? null,
            'source' => $mount['source'] ?? null,
            'target' => $mount['target'] ?? null,
            'read_only' => (bool) ($mount['read_only'] ?? false),
        ];
        $normalized[] = $normalizedMount;
        if (($mount['type'] ?? null) === 'bind') {
            $actualBindMounts[] = [$serviceName, $normalizedMount];
        }
    }
    $expectedServiceMounts = $expectedMounts[$serviceName];
    usort($normalized, static fn (array $left, array $right): int => json_encode($left) <=> json_encode($right));
    usort($expectedServiceMounts, static fn (array $left, array $right): int => json_encode($left) <=> json_encode($right));
    if ($normalized !== $expectedServiceMounts) {
        fail_contract("{$serviceName} mount set changed: " . json_encode($normalized, JSON_UNESCAPED_SLASHES));
    }
}

if (count($actualBindMounts) !== 1
    || $actualBindMounts[0][0] !== 'wp'
    || $actualBindMounts[0][1]['source'] !== $expectedPackageZip
    || $actualBindMounts[0][1]['target'] !== '/package/gama-contact.zip'
    || $actualBindMounts[0][1]['read_only'] !== true
) {
    fail_contract('ZIP must be the only bind mount and must be read-only');
}

$volumes = $resolved['volumes'] ?? null;
$actualVolumeNames = is_array($volumes) ? array_keys($volumes) : [];
sort($actualVolumeNames, SORT_STRING);
if (!is_array($volumes) || $actualVolumeNames !== ['core', 'db-data', 'uploads']) {
    fail_contract('project-scoped volume set changed');
}
foreach ($volumes as $name => $volume) {
    if (!is_array($volume) || array_key_exists('external', $volume)) {
        fail_contract("{$name} must be a project-scoped volume");
    }
    if (($volume['name'] ?? null) !== "gama-package-contract_{$name}") {
        fail_contract("{$name} resolved name is not project-scoped");
    }
}

fwrite(STDOUT, "Resolved package Compose mount contract is exact.\n");
