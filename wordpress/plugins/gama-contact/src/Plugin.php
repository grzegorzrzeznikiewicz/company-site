<?php

declare(strict_types=1);

namespace GamaSoftware\Contact;

use GamaSoftware\Contact\Support\I18n;

final class Plugin
{
    private static bool $booted = false;

    public function boot(): void
    {
        if (self::$booted) {
            return;
        }

        self::$booted = true;
        add_action('init', [I18n::class, 'load']);
    }
}
