<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Lifecycle;

final class Uninstaller {

	public static function uninstall(): void {
		// Durable data is preserved by default. Opt-in deletion is future scope.
	}
}
