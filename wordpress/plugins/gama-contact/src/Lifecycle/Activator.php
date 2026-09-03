<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Lifecycle;

final class Activator
{
    public const SCHEMA_VERSION = 1;

    public static function activate(): void
    {
        update_option('gama_contact_schema_version', self::SCHEMA_VERSION, false);
    }
}
