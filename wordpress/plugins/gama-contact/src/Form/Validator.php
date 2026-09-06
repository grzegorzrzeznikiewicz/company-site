<?php

declare(strict_types=1);

namespace GamaSoftware\Contact\Form;

final class Validator {

	/** @return array{values: array{name: string, email: string, phone: string, message: string}, errors: array<string, string>} */
	public static function validate( array $input ): array {
		$values = array(
			'name' => sanitize_text_field( (string) ( $input['name'] ?? '' ) ),
			'email' => sanitize_email( (string) ( $input['email'] ?? '' ) ),
			'phone' => sanitize_text_field( (string) ( $input['phone'] ?? '' ) ),
			'message' => sanitize_textarea_field( (string) ( $input['message'] ?? '' ) ),
		);
		$errors = array();

		if ( $values['name'] === '' ) {
			$errors['name'] = __( 'Podaj swoje imię i nazwisko.', 'gama-contact' );
		} elseif ( mb_strlen( $values['name'] ) > 120 ) {
			$errors['name'] = __( 'Imię i nazwisko jest zbyt długie.', 'gama-contact' );
		}
		if ( $values['email'] === '' || ! is_email( $values['email'] ) ) {
			$errors['email'] = __( 'Podaj poprawny adres e-mail.', 'gama-contact' );
		}
		if ( $values['phone'] === '' ) {
			$errors['phone'] = __( 'Podaj numer telefonu.', 'gama-contact' );
		} elseif ( mb_strlen( $values['phone'] ) > 40 || ! preg_match( '/^[0-9+() .-]+$/', $values['phone'] ) ) {
			$errors['phone'] = __( 'Podaj poprawny numer telefonu.', 'gama-contact' );
		}
		if ( $values['message'] === '' ) {
			$errors['message'] = __( 'Wiadomość nie może być pusta.', 'gama-contact' );
		} elseif ( mb_strlen( $values['message'] ) > 5000 ) {
			$errors['message'] = __( 'Wiadomość jest zbyt długa.', 'gama-contact' );
		}

		return array(
			'values' => $values,
			'errors' => $errors,
		);
	}
}
