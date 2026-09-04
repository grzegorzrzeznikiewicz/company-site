<?php
/**
 * Plugin Name: Gama Local Mailpit
 * Description: Routes non-production mail to an isolated SMTP sink.
 * Version: 0.1.0
 * Text Domain: gama-local-mailpit
 */

declare(strict_types=1);

add_filter(
    'wp_mail_from',
    static fn (): string => 'wordpress@gama-software.test'
);

add_action(
    'phpmailer_init',
    static function (PHPMailer\PHPMailer\PHPMailer $mailer): void {
        $mailer->isSMTP();
        $mailer->Host = (string) ( getenv( 'GAMA_MAIL_SINK_HOST' ) ?: 'mailpit' );
        $mailer->Port = (int) ( getenv( 'GAMA_MAIL_SINK_PORT' ) ?: 1025 );
        $mailer->SMTPAuth = false;
        $mailer->SMTPSecure = '';
    }
);
