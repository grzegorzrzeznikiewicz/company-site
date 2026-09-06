<?php
/**
 * Plugin Name: Gama Contact
 * Description: Theme-independent, secure contact form for Gama Software.
 * Version: 0.3.2
 * Requires at least: 7.1
 * Requires PHP: 8.4
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: gama-contact
 * Domain Path: /languages
 */

declare(strict_types=1);

namespace GamaSoftware\Contact;

use GamaSoftware\Contact\Lifecycle\Activator;
use GamaSoftware\Contact\Lifecycle\Deactivator;

defined( 'ABSPATH' ) || exit;

define( 'GAMA_CONTACT_VERSION', '0.3.2' );
define( 'GAMA_CONTACT_FILE', __FILE__ );
define( 'GAMA_CONTACT_PATH', plugin_dir_path( __FILE__ ) );
define( 'GAMA_CONTACT_URL', plugin_dir_url( __FILE__ ) );

require_once GAMA_CONTACT_PATH . 'src/Lifecycle/Activator.php';
require_once GAMA_CONTACT_PATH . 'src/Lifecycle/Deactivator.php';
require_once GAMA_CONTACT_PATH . 'src/Support/I18n.php';
require_once GAMA_CONTACT_PATH . 'src/Form/Validator.php';
require_once GAMA_CONTACT_PATH . 'src/Form/FormRenderer.php';
require_once GAMA_CONTACT_PATH . 'src/Form/RateLimiter.php';
require_once GAMA_CONTACT_PATH . 'src/Form/SubmissionController.php';
require_once GAMA_CONTACT_PATH . 'src/Plugin.php';

register_activation_hook( GAMA_CONTACT_FILE, array( Activator::class, 'activate' ) );
register_deactivation_hook( GAMA_CONTACT_FILE, array( Deactivator::class, 'deactivate' ) );

( new Plugin() )->boot();
