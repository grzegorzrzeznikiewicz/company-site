<?php
/**
 * Title: Gama Software Contact
 * Slug: gama-software/contact
 * Categories: featured, contact
 * Inserter: yes
 * Description: Editable contact details and a replaceable form slot.
 *
 * @package GamaSoftware
 */

?>
<!-- wp:group {"tagName":"section","anchor":"contact","align":"full","className":"gama-contact","backgroundColor":"base","layout":{"type":"constrained"}} -->
<section id="contact" class="wp-block-group alignfull gama-contact has-base-background-color has-background">
	<!-- wp:group {"align":"wide","className":"gama-contact__content","layout":{"type":"constrained"}} -->
	<div class="wp-block-group alignwide gama-contact__content">
		<!-- wp:heading {"level":2,"textAlign":"center","fontSize":"heading-2"} --><h2 class="wp-block-heading has-text-align-center has-heading-2-font-size"><?php esc_html_e( 'Kontakt', 'gama-software' ); ?></h2><!-- /wp:heading -->
		<!-- wp:group {"className":"gama-contact__card","backgroundColor":"base","layout":{"type":"constrained"}} -->
		<div class="wp-block-group gama-contact__card has-base-background-color has-background">
			<!-- wp:group {"className":"gama-contact__layout","layout":{"type":"grid","minimumColumnWidth":"18rem"}} -->
			<div class="wp-block-group gama-contact__layout">
				<!-- wp:group {"className":"gama-contact__details","layout":{"type":"constrained"}} -->
				<div class="wp-block-group gama-contact__details">
					<!-- wp:heading {"level":3,"fontSize":"heading-3"} --><h3 class="wp-block-heading has-heading-3-font-size"><?php esc_html_e( 'Porozmawiajmy o Twoim projekcie', 'gama-software' ); ?></h3><!-- /wp:heading -->
					<!-- wp:paragraph {"textColor":"text-muted"} --><p class="has-text-muted-color has-text-color"><?php esc_html_e( 'Opisz krótko swoje potrzeby. Odpowiemy i zaproponujemy najlepszy następny krok.', 'gama-software' ); ?></p><!-- /wp:paragraph -->
					<!-- wp:paragraph --><p><strong><?php esc_html_e( 'E-mail:', 'gama-software' ); ?></strong> <a href="mailto:founders@gama-software.com">founders@gama-software.com</a></p><!-- /wp:paragraph -->
					<!-- wp:buttons --><div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} --><div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="mailto:founders@gama-software.com"><?php esc_html_e( 'Napisz e-mail', 'gama-software' ); ?></a></div><!-- /wp:button --></div><!-- /wp:buttons -->
				</div>
				<!-- /wp:group -->
				<!-- wp:group {"className":"gama-contact__form-slot","layout":{"type":"constrained"}} -->
				<div class="wp-block-group gama-contact__form-slot">
					<!-- wp:paragraph {"className":"gama-contact__form-placeholder","align":"center","textColor":"text-muted"} --><p class="has-text-align-center gama-contact__form-placeholder has-text-muted-color has-text-color"><?php esc_html_e( 'Formularz kontaktowy zostanie wyświetlony po aktywowaniu wtyczki Gama Contact.', 'gama-software' ); ?></p><!-- /wp:paragraph -->
					<!-- wp:shortcode -->[gama_contact_form]<!-- /wp:shortcode -->
				</div>
				<!-- /wp:group -->
			</div>
			<!-- /wp:group -->
		</div>
		<!-- /wp:group -->
	</div>
	<!-- /wp:group -->
</section>
<!-- /wp:group -->
