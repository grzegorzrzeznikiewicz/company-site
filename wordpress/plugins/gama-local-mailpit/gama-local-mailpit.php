<?php
/**
 * Plugin Name: Gama Local Mailpit
 * Description: Routes local development mail to the project Mailpit SMTP sink.
 * Version: 0.1.0
 * Text Domain: gama-local-mailpit
 */

declare(strict_types=1);

add_action(
    'phpmailer_init',
    static function (PHPMailer\PHPMailer\PHPMailer $mailer): void {
        $mailer->isSMTP();
        $mailer->Host = 'mailpit';
        $mailer->Port = 1025;
        $mailer->SMTPAuth = false;
        $mailer->SMTPSecure = '';
    }
);
