<?php
/**
 * Site Health adjustments for immutable releases.
 *
 * @package GamaSecurity
 */

declare(strict_types=1);

namespace GamaSoftware\Security;

/**
 * Replace the background-update check when core updates ship through the release pipeline.
 *
 * Core, theme and plugin files come from an immutable, digest-pinned image, so automatic
 * background updates are disabled on purpose. The core "WordPress version" test stays
 * active and still reports every pending core release.
 */
final class SiteHealth {
	public const TEST_ID = 'gama_release_managed_updates';

	/** Register the Site Health filter. */
	public function register(): void {
		add_filter( 'site_status_tests', array( $this, 'filter_tests' ) );
	}

	/** Whether this installation deliberately delegates core updates to releases. */
	public static function updates_are_release_managed(): bool {
		return defined( 'AUTOMATIC_UPDATER_DISABLED' ) && true === AUTOMATIC_UPDATER_DISABLED
			&& defined( 'WP_AUTO_UPDATE_CORE' ) && false === WP_AUTO_UPDATE_CORE;
	}

	/**
	 * Swap the background-update test for an explicit release-managed status.
	 *
	 * @param array<string, array<string, mixed>> $tests Site Health tests by type.
	 * @return array<string, array<string, mixed>>
	 */
	public function filter_tests( array $tests ): array {
		if ( ! self::updates_are_release_managed() ) {
			return $tests;
		}

		unset( $tests['async']['background_updates'], $tests['direct']['background_updates'] );
		$tests['direct'][ self::TEST_ID ] = array(
			'label' => __( 'WordPress updates are delivered by the release pipeline', 'gama-security' ),
			'test'  => array( $this, 'release_managed_updates_test' ),
		);

		return $tests;
	}

	/**
	 * Report the deliberate update policy as a passed test.
	 *
	 * @return array<string, mixed>
	 */
	public function release_managed_updates_test(): array {
		return array(
			'label'       => __( 'WordPress updates are delivered by the release pipeline', 'gama-security' ),
			'status'      => 'good',
			'badge'       => array(
				'label' => __( 'Security', 'gama-security' ),
				'color' => 'blue',
			),
			'description' => '<p>' . esc_html__( 'Automatic background updates are disabled on purpose: WordPress core, themes and plugins are shipped as an immutable, digest-pinned image through the release pipeline. The WordPress version test above still reports any pending core release, which must be applied by bumping the image in the repository.', 'gama-security' ) . '</p>',
			'actions'     => '',
			'test'        => self::TEST_ID,
		);
	}
}
