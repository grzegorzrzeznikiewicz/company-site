<?php
/**
 * Bounded login-attempt guard.
 *
 * @package GamaSecurity
 */

declare(strict_types=1);

namespace GamaSoftware\Security;

use WP_Error;
use WP_User;

/** Rate-limit repeated authentication failures by remote address and username. */
final class LoginGuard {
	private const MAX_FAILURES           = 10;
	private const WINDOW_SECONDS         = 15 * MINUTE_IN_SECONDS;
	private const LOCK_WAIT_SECONDS      = 2;

	/** Register authentication lifecycle hooks. */
	public function register(): void {
		add_filter( 'authenticate', array( $this, 'reject_blocked_login' ), 5, 3 );
		add_filter( 'authenticate', array( $this, 'reject_blocked_login' ), 100, 3 );
		add_action( 'wp_login_failed', array( $this, 'record_failure' ), 10, 2 );
		add_action( 'wp_login', array( $this, 'clear_failures' ), 10, 2 );
	}

	/**
	 * Reject a blocked login before password hashing work.
	 *
	 * @param WP_User|WP_Error|null $user     Existing authentication result.
	 * @param string                $username Submitted username.
	 * @param string                $password Submitted password.
	 * @return WP_User|WP_Error|null
	 */
	public function reject_blocked_login( WP_User|WP_Error|null $user, string $username, string $password ): WP_User|WP_Error|null {
		unset( $password );
		if ( $user instanceof WP_Error && 'gama_security_login_rate_limited' === $user->get_error_code() ) {
			return $user;
		}
		if ( '' === trim( $username ) ) {
			return $user;
		}
		if ( (int) get_transient( $this->rate_key( $username ) ) < self::MAX_FAILURES ) {
			return $user;
		}

		return new WP_Error(
			'gama_security_login_rate_limited',
			__( 'Zbyt wiele prób logowania. Spróbuj ponownie później.', 'gama-security' ),
			array( 'status' => 429 )
		);
	}

	/**
	 * Record one failed login through an atomic database advisory lock.
	 *
	 * @param string   $username Submitted username.
	 * @param WP_Error $error    Authentication error.
	 */
	public function record_failure( string $username, WP_Error $error ): void {
		global $wpdb;

		unset( $error );
		$key       = $this->rate_key( $username );
		$lock_name = 'gama_security:' . substr( hash( 'sha256', $key ), 0, 48 );
		$acquired  = $wpdb->get_var(
			$wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $lock_name, self::LOCK_WAIT_SECONDS )
		);
		if ( '1' !== (string) $acquired ) {
			return;
		}

		try {
			$count = (int) get_transient( $key );
			set_transient( $key, min( self::MAX_FAILURES, $count + 1 ), self::WINDOW_SECONDS );
		} finally {
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock_name ) );
		}
	}

	/**
	 * Clear failures after a successful login.
	 *
	 * @param string  $username Authenticated username.
	 * @param WP_User $user     Authenticated user.
	 */
	public function clear_failures( string $username, WP_User $user ): void {
		unset( $user );
		delete_transient( $this->rate_key( $username ) );
	}

	/**
	 * Resolve a privacy-preserving rate key.
	 *
	 * @param string $username Submitted username.
	 */
	private function rate_key( string $username ): string {
		$address = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : 'unknown';
		$subject = strtolower( trim( $username ) ) . '|' . $address;
		return 'gama_security_login_rate_' . hash_hmac( 'sha256', $subject, wp_salt( 'auth' ) );
	}
}
