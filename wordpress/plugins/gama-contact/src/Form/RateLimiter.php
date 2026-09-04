<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Form;

final class RateLimiter
{
    private const MAX_REQUESTS = 5;
    private const WINDOW_SECONDS = HOUR_IN_SECONDS;
    private const LOCK_WAIT_SECONDS = 2;

    public static function consume(): bool
    {
        global $wpdb;

        $address = sanitize_text_field(wp_unslash((string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown')));
        $address_hash = hash_hmac('sha256', $address, wp_salt('nonce'));
        $rate_key = 'gama_contact_rate_' . $address_hash;
        $lock_name = 'gama_contact:' . substr(hash('sha256', $rate_key), 0, 48);
        $acquired = $wpdb->get_var(
            $wpdb->prepare('SELECT GET_LOCK(%s, %d)', $lock_name, self::LOCK_WAIT_SECONDS)
        );

        if ((string) $acquired !== '1') {
            return false;
        }

        try {
            $count = (int) get_transient($rate_key);
            if ($count >= self::MAX_REQUESTS) {
                return false;
            }

            set_transient($rate_key, $count + 1, self::WINDOW_SECONDS);

            return true;
        } finally {
            $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock_name));
        }
    }
}
