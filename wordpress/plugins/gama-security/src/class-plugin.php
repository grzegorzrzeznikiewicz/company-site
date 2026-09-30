<?php
/**
 * Project security policy.
 *
 * @package GamaSecurity
 */

declare(strict_types=1);

namespace GamaSoftware\Security;

use WP_User;

/** Apply the least-privilege editor boundary and public response protections. */
final class Plugin {
	private const EDITOR_FORBIDDEN_CAPABILITIES = array(
		'activate_plugins',
		'delete_plugins',
		'edit_files',
		'edit_plugins',
		'edit_users',
		'install_plugins',
		'install_themes',
		'manage_options',
		'promote_users',
		'switch_themes',
		'update_core',
		'update_plugins',
		'update_themes',
	);

	/** Register the policy without persisting role mutations. */
	public function register(): void {
		add_filter( 'user_has_cap', array( $this, 'filter_user_capabilities' ), 100, 4 );
		add_action( 'send_headers', array( $this, 'send_security_headers' ) );
		add_filter( 'login_errors', array( $this, 'generic_login_error' ) );
		add_filter( 'the_generator', '__return_empty_string' );
		remove_action( 'wp_head', 'wp_generator' );
		( new LoginGuard() )->register();
	}

	/**
	 * Let Editors use the Site Editor while preserving all administrative boundaries.
	 *
	 * @param array<string, bool> $allcaps All resolved capabilities.
	 * @param string[]            $caps    Primitive capabilities under evaluation.
	 * @param mixed[]             $args    Original current_user_can arguments.
	 * @param WP_User             $user    Current user.
	 * @return array<string, bool>
	 */
	public function filter_user_capabilities( array $allcaps, array $caps, array $args, WP_User $user ): array {
		if ( ! in_array( 'editor', $user->roles, true ) ) {
			return $allcaps;
		}

		if ( 'edit_theme_options' === ( $args[0] ?? '' ) || in_array( 'edit_theme_options', $caps, true ) ) {
			$allcaps['edit_theme_options'] = true;
		}
		foreach ( self::EDITOR_FORBIDDEN_CAPABILITIES as $capability ) {
			$allcaps[ $capability ] = false;
		}

		return $allcaps;
	}

	/** Send browser protections; TLS-only HSTS is never emitted on local HTTP. */
	public function send_security_headers(): void {
		if ( headers_sent() ) {
			return;
		}
		header( 'X-Content-Type-Options: nosniff', true );
		header( 'X-Frame-Options: SAMEORIGIN', true );
		header( 'Referrer-Policy: strict-origin-when-cross-origin', true );
		header( 'Permissions-Policy: camera=(), geolocation=(), microphone=()', true );
		if ( 'production' === wp_get_environment_type() && is_ssl() ) {
			header( 'Strict-Transport-Security: max-age=31536000; includeSubDomains', true );
		}
	}

	/** Return one generic login error to avoid account enumeration. */
	public function generic_login_error(): string {
		return __( 'Logowanie nie powiodło się. Sprawdź dane lub spróbuj ponownie później.', 'gama-security' );
	}
}
