<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Support;

final class I18n {

	public static function load(): void {
		load_plugin_textdomain(
			'gama-contact',
			false,
			dirname( plugin_basename( GAMA_CONTACT_FILE ) ) . '/languages'
		);
	}
}
