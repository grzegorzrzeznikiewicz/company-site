<?php
/**
 * Plugin Name: Gama Mail Transport
 * Description: Configures the approved production SMTP transport from environment-only secrets.
 * Version: 0.1.0
 * Requires at least: 7.1
 * Requires PHP: 8.4
 * License: GPL-2.0-or-later
 * Text Domain: gama-mail-transport
 *
 * @package GamaSoftware\MailTransport
 */

declare(strict_types=1);

use PHPMailer\PHPMailer\PHPMailer;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Return validated SMTP configuration or null when production must fail closed.
 *
 * @return array{host:string,port:int,username:string,password:string,encryption:string}|null
 */
function gama_mail_transport_config(): ?array {
	$host       = (string) getenv( 'GAMA_SMTP_HOST' );
	$port       = filter_var( getenv( 'GAMA_SMTP_PORT' ), FILTER_VALIDATE_INT );
	$username   = (string) getenv( 'GAMA_SMTP_USERNAME' );
	$password   = (string) getenv( 'GAMA_SMTP_PASSWORD' );
	$encryption = (string) getenv( 'GAMA_SMTP_ENCRYPTION' );
	$host_lower = strtolower( $host );

	if (
		1 !== preg_match( '/\A[a-z0-9.-]+\z/i', $host )
		|| in_array( $host_lower, array( 'localhost', 'mailpit' ), true )
		|| str_starts_with( $host_lower, 'localhost.' )
		|| str_starts_with( $host_lower, 'mailpit.' )
		|| str_starts_with( $host_lower, '127.' )
		|| false === $port
		|| $port < 1
		|| $port > 65535
		|| '' === $username
		|| '' === $password
		|| ! in_array( $encryption, array( 'tls', 'ssl' ), true )
	) {
		return null;
	}

	return array(
		'host'       => $host,
		'port'       => $port,
		'username'   => $username,
		'password'   => $password,
		'encryption' => $encryption,
	);
}

add_filter(
	'pre_wp_mail',
	static function ( null|bool $short_circuit ): null|bool {
		if ( 'production' === wp_get_environment_type() && null === gama_mail_transport_config() ) {
			return false;
		}

		return $short_circuit;
	},
	5
);

add_action(
	'phpmailer_init',
	static function ( PHPMailer $mailer ): void {
		if ( 'production' !== wp_get_environment_type() ) {
			return;
		}

		$config = gama_mail_transport_config();
		if ( null === $config ) {
			return;
		}

		$mailer->isSMTP();
		// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer owns these public API names.
		$mailer->Host       = $config['host'];
		$mailer->Port       = $config['port'];
		$mailer->SMTPAuth   = true;
		$mailer->Username   = $config['username'];
		$mailer->Password   = $config['password'];
		$mailer->SMTPSecure = 'ssl' === $config['encryption']
			? PHPMailer::ENCRYPTION_SMTPS
			: PHPMailer::ENCRYPTION_STARTTLS;
		// phpcs:enable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase
	}
);
