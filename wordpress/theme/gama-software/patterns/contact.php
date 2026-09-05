<?php
/**
 * Title: Gama Software Contact
 * Slug: gama-software/contact
 * Categories: featured, contact
 * Inserter: yes
 * Description: Centered contact form with an editable heading and e-mail fallback.
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
			<!-- wp:group {"className":"gama-contact__form-slot","layout":{"type":"constrained"}} -->
			<div class="wp-block-group gama-contact__form-slot">
				<!-- wp:paragraph {"className":"gama-contact__form-placeholder","align":"center","textColor":"text-muted"} --><p class="has-text-align-center gama-contact__form-placeholder has-text-muted-color has-text-color"><?php esc_html_e( 'Formularz jest chwilowo niedostępny. Napisz do nas:', 'gama-software' ); ?> <a href="mailto:founders@gama-software.com">founders@gama-software.com</a></p><!-- /wp:paragraph -->
				<!-- wp:shortcode -->[gama_contact_form]<!-- /wp:shortcode -->
			</div>
			<!-- /wp:group -->
		</div>
		<!-- /wp:group -->
	</div>
	<!-- /wp:group -->
</section>
<!-- /wp:group -->
