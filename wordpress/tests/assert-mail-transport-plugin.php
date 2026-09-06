<?php

declare(strict_types=1);

namespace PHPMailer\PHPMailer {
    final class PHPMailer
    {
        public const ENCRYPTION_SMTPS = 'ssl';
        public const ENCRYPTION_STARTTLS = 'tls';

        public string $Host = '';
        public int $Port = 0;
        public bool $SMTPAuth = false;
        public string $Username = '';
        public string $Password = '';
        public string $SMTPSecure = '';
        public bool $smtpEnabled = false;

        public function isSMTP(): void
        {
            $this->smtpEnabled = true;
        }
    }
}

namespace {
    use PHPMailer\PHPMailer\PHPMailer;

    define('ABSPATH', '/var/www/html/');

    $environment = 'local';
    $hooks       = array();

    function wp_get_environment_type(): string
    {
        global $environment;

        return $environment;
    }

    function add_action(string $hook, callable $callback): void
    {
        global $hooks;
        $hooks[$hook] = $callback;
    }

    function add_filter(string $hook, callable $callback): void
    {
        global $hooks;
        $hooks[$hook] = $callback;
    }

    require '/plugin/gama-mail-transport.php';

    if (!isset($hooks['phpmailer_init'], $hooks['pre_wp_mail'])) {
        throw new RuntimeException('Mail transport did not register both required hooks.');
    }

    putenv('GAMA_SMTP_HOST=smtp.example.test');
    putenv('GAMA_SMTP_PORT=587');
    putenv('GAMA_SMTP_USERNAME=release-user');
    putenv('GAMA_SMTP_PASSWORD=release-password');
    putenv('GAMA_SMTP_ENCRYPTION=tls');

    $localMailer = new PHPMailer();
    $hooks['phpmailer_init']($localMailer);
    if ($localMailer->smtpEnabled) {
        throw new RuntimeException('Production SMTP transport was enabled in a local environment.');
    }

    $environment = 'production';
    $mailer      = new PHPMailer();
    $hooks['phpmailer_init']($mailer);
    if (
        !$mailer->smtpEnabled
        || 'smtp.example.test' !== $mailer->Host
        || 587 !== $mailer->Port
        || !$mailer->SMTPAuth
        || 'release-user' !== $mailer->Username
        || 'release-password' !== $mailer->Password
        || PHPMailer::ENCRYPTION_STARTTLS !== $mailer->SMTPSecure
    ) {
        throw new RuntimeException('Production SMTP settings were not applied exactly.');
    }

    foreach (array('bad host', 'localhost', 'localhost.example.test', 'mailpit', 'mailpit.example.test', '127.0.0.2') as $invalidHost) {
        putenv('GAMA_SMTP_HOST=' . $invalidHost);
        $invalidMailer = new PHPMailer();
        $hooks['phpmailer_init']($invalidMailer);
        if ($invalidMailer->smtpEnabled) {
            throw new RuntimeException('Invalid production SMTP configuration was accepted.');
        }
        if (false !== $hooks['pre_wp_mail'](null)) {
            throw new RuntimeException('Invalid production SMTP did not fail closed.');
        }
    }
}
