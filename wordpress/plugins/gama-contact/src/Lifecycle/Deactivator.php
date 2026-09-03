<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Lifecycle;

final class Deactivator
{
    public static function deactivate(): void
    {
        // GSWEB-11 owns no scheduled work and deactivation preserves all data.
    }
}
