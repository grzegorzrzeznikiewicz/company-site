<?php
/**
 * Title: Gama Software Hero
 * Slug: gama-software/hero
 * Categories: featured, text
 * Inserter: yes
 * Description: The editable introductory section for the Gama Software homepage.
 *
 * @package GamaSoftware
 */

?>
<!-- wp:group {"tagName":"section","anchor":"home","className":"gama-hero","layout":{"type":"constrained"}} -->
<section id="home" class="wp-block-group gama-hero">
	<!-- wp:group {"className":"gama-hero__content","layout":{"type":"constrained"}} -->
	<div class="wp-block-group gama-hero__content">
		<!-- wp:heading {"level":1,"textAlign":"center","fontSize":"display"} -->
		<h1 class="wp-block-heading has-text-align-center has-display-font-size"><?php esc_html_e( 'Gama Software', 'gama-software' ); ?></h1>
		<!-- /wp:heading -->

		<!-- wp:paragraph {"align":"center","className":"gama-hero__lead","fontSize":"lead"} -->
		<p class="has-text-align-center gama-hero__lead has-lead-font-size"><?php esc_html_e( 'Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu', 'gama-software' ); ?></p>
		<!-- /wp:paragraph -->

		<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
		<div class="wp-block-buttons">
			<!-- wp:button {"url":"/#services","backgroundColor":"accent","textColor":"base"} -->
			<div class="wp-block-button"><a class="wp-block-button__link has-base-color has-accent-background-color has-text-color has-background wp-element-button" href="/#services"><?php esc_html_e( 'Poznaj nasze usługi', 'gama-software' ); ?></a></div>
			<!-- /wp:button -->
		</div>
		<!-- /wp:buttons -->
	</div>
	<!-- /wp:group -->
</section>
<!-- /wp:group -->
