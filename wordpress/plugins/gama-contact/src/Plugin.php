<?php

declare(strict_types=1);

namespace GamaSoftware\Contact;

use GamaSoftware\Contact\Form\FormRenderer;
use GamaSoftware\Contact\Form\SubmissionController;
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
        add_action('init', [FormRenderer::class, 'register']);
        add_action('rest_api_init', [SubmissionController::class, 'register']);
    }
}
