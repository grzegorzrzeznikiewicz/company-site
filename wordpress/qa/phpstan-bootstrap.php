<?php

declare(strict_types=1);

// plugin_dir_url() depends on runtime WordPress state; provide its known type.
if (! defined('GAMA_CONTACT_URL')) {
    define('GAMA_CONTACT_URL', 'https://example.test/wp-content/plugins/gama-contact/');
}
