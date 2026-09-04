<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Form;

final class FormRenderer
{
    public static function register(): void
    {
        add_shortcode('gama_contact_form', [self::class, 'render']);
    }

    public static function render(): string
    {
        wp_enqueue_style('gama-contact-form', GAMA_CONTACT_URL . 'assets/contact-form.css', [], GAMA_CONTACT_VERSION);
        wp_enqueue_script('gama-contact-form', GAMA_CONTACT_URL . 'assets/contact-form.js', [], GAMA_CONTACT_VERSION, true);
        wp_localize_script(
            'gama-contact-form',
            'gamaContactForm',
            [
                'endpoint' => rest_url('gama-contact/v1/messages'),
                'nonce' => wp_create_nonce('gama_contact_submit'),
                'genericError' => __('Coś poszło nie tak. Spróbuj ponownie później.', 'gama-contact'),
            ]
        );

        ob_start();
        ?>
        <form class="gama-contact-form" novalidate>
            <div class="gama-contact-form__grid">
                <div class="gama-contact-form__field">
                    <label for="gama-contact-name"><?php esc_html_e('Imię i nazwisko', 'gama-contact'); ?></label>
                    <input id="gama-contact-name" name="name" type="text" autocomplete="name" required maxlength="120">
                    <p class="gama-contact-form__error" data-error-for="name"></p>
                </div>
                <div class="gama-contact-form__field">
                    <label for="gama-contact-email"><?php esc_html_e('E-mail', 'gama-contact'); ?></label>
                    <input id="gama-contact-email" name="email" type="email" autocomplete="email" required maxlength="254">
                    <p class="gama-contact-form__error" data-error-for="email"></p>
                </div>
            </div>
            <div class="gama-contact-form__field">
                <label for="gama-contact-phone"><?php esc_html_e('Telefon', 'gama-contact'); ?></label>
                <input id="gama-contact-phone" name="phone" type="tel" autocomplete="tel" required maxlength="40">
                <p class="gama-contact-form__error" data-error-for="phone"></p>
            </div>
            <div class="gama-contact-form__field">
                <label for="gama-contact-message"><?php esc_html_e('Wiadomość', 'gama-contact'); ?></label>
                <textarea id="gama-contact-message" name="message" rows="5" required maxlength="5000"></textarea>
                <p class="gama-contact-form__error" data-error-for="message"></p>
            </div>
            <div class="gama-contact-form__trap" aria-hidden="true">
                <label for="gama-contact-company"><?php esc_html_e('Firma', 'gama-contact'); ?></label>
                <input id="gama-contact-company" name="company" type="text" tabindex="-1" autocomplete="off">
            </div>
            <input name="gama_contact_nonce" type="hidden" value="<?php echo esc_attr(wp_create_nonce('gama_contact_submit')); ?>">
            <button class="wp-element-button" type="submit"><?php esc_html_e('Wyślij wiadomość', 'gama-contact'); ?></button>
            <p class="gama-contact-form__status" aria-live="polite" aria-atomic="true"></p>
            <noscript><p><?php esc_html_e('Włącz JavaScript albo użyj podanego obok adresu e-mail.', 'gama-contact'); ?></p></noscript>
        </form>
        <?php
        return (string) ob_get_clean();
    }
}
