<?php

declare(strict_types=1);

defined( 'WP_UNINSTALL_PLUGIN' ) || exit;

require_once __DIR__ . '/src/Lifecycle/Uninstaller.php';

GamaSoftware\Contact\Lifecycle\Uninstaller::uninstall();
