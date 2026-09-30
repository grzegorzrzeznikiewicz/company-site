<?php
/**
 * Plugin Name: Gama SEO
 * Description: Jedno źródło metadanych SEO, robots, sitemap i przekierowań dla strony Gama Software.
 * Version: 0.1.0
 * Requires at least: 7.1
 * Requires PHP: 8.4
 * Author: Gama Software
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: gama-seo
 * Domain Path: /languages
 *
 * @package GamaSeo
 */

declare(strict_types=1);

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once __DIR__ . '/src/class-plugin.php';

add_action(
	'plugins_loaded',
	static function (): void {
		( new GamaSoftware\Seo\Plugin() )->register();
	}
);
