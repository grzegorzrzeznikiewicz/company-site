<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Form;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

final class SubmissionController
{
    public static function register(): void
    {
        register_rest_route(
            'gama-contact/v1',
            '/messages',
            [
                'methods' => 'POST',
                'callback' => [self::class, 'submit'],
                'permission_callback' => '__return_true',
            ]
        );
    }

    public static function submit(WP_REST_Request $request): WP_REST_Response|WP_Error
    {
        if (!self::is_same_origin($request) || !wp_verify_nonce((string) $request->get_header('X-Gama-Contact-Nonce'), 'gama_contact_submit')) {
            return new WP_Error('gama_contact_forbidden', __('Nie udało się zweryfikować formularza. Odśwież stronę i spróbuj ponownie.', 'gama-contact'), ['status' => 403]);
        }

        $input = (array) $request->get_json_params();
        if (sanitize_text_field((string) ($input['company'] ?? '')) !== '') {
            return new WP_REST_Response(['message' => __('Dziękujemy. Wiadomość została przyjęta.', 'gama-contact')], 200);
        }
        if (!RateLimiter::consume()) {
            return new WP_Error('gama_contact_rate_limited', __('Wysłano zbyt wiele wiadomości. Spróbuj ponownie później.', 'gama-contact'), ['status' => 429]);
        }

        $result = Validator::validate($input);
        if ($result['errors'] !== []) {
            return new WP_REST_Response(
                [
                    'message' => __('Popraw zaznaczone pola.', 'gama-contact'),
                    'field_errors' => $result['errors'],
                ],
                422
            );
        }

        $values = $result['values'];
        $configured_recipient = defined('GAMA_CONTACT_RECIPIENT') ? (string) GAMA_CONTACT_RECIPIENT : (string) getenv('GAMA_CONTACT_RECIPIENT');
        $configured_sender = defined('GAMA_CONTACT_SENDER') ? (string) GAMA_CONTACT_SENDER : (string) getenv('GAMA_CONTACT_SENDER');
        $recipient = sanitize_email($configured_recipient !== '' ? $configured_recipient : (string) get_option('admin_email'));
        $sender = sanitize_email($configured_sender);
        if (!is_email($recipient)) {
            return new WP_Error('gama_contact_configuration', __('Formularz jest chwilowo niedostępny.', 'gama-contact'), ['status' => 503]);
        }

        $headers = ['Content-Type: text/plain; charset=UTF-8', 'Reply-To: ' . $values['name'] . ' <' . $values['email'] . '>'];
        if (is_email($sender)) {
            $headers[] = 'From: Gama Software <' . $sender . '>';
        }
        $body = sprintf(
            "Imię i nazwisko: %s\nE-mail: %s\nTelefon: %s\n\nWiadomość:\n%s",
            $values['name'],
            $values['email'],
            $values['phone'],
            $values['message']
        );
        if (!wp_mail($recipient, __('Nowa wiadomość ze strony Gama Software', 'gama-contact'), $body, $headers)) {
            return new WP_Error('gama_contact_delivery', __('Nie udało się wysłać wiadomości. Spróbuj ponownie później.', 'gama-contact'), ['status' => 503]);
        }

        return new WP_REST_Response(['message' => __('Dziękujemy. Wiadomość została wysłana.', 'gama-contact')], 200);
    }

    private static function is_same_origin(WP_REST_Request $request): bool
    {
        $source = (string) ($request->get_header('Origin') ?: wp_get_raw_referer());
        $expected = wp_parse_url(home_url('/'));
        $actual = wp_parse_url($source);

        return is_array($expected)
            && is_array($actual)
            && strtolower((string) ($actual['scheme'] ?? '')) === strtolower((string) ($expected['scheme'] ?? ''))
            && strtolower((string) ($actual['host'] ?? '')) === strtolower((string) ($expected['host'] ?? ''))
            && (int) ($actual['port'] ?? self::default_port((string) ($actual['scheme'] ?? ''))) === (int) ($expected['port'] ?? self::default_port((string) ($expected['scheme'] ?? '')));
    }

    private static function default_port(string $scheme): int
    {
        return strtolower($scheme) === 'https' ? 443 : 80;
    }

}
