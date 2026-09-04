<?php
/**
 * Plugin Name: Gama Security
 * Description: Role, response-header and login protections for Gama Software.
 * Version: 0.1.1
 * Requires at least: 7.1
 * Requires PHP: 8.4
 * Author: Gama Software
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: gama-security
 *
 * @package GamaSecurity
 */

declare(strict_types=1);

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once __DIR__ . '/src/class-loginguard.php';
require_once __DIR__ . '/src/class-plugin.php';

add_action(
	'plugins_loaded',
	static function (): void {
		( new GamaSoftware\Security\Plugin() )->register();
	}
);
