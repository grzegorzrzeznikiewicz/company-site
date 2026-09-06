<?php
/**
 * Title: Gama Software Services
 * Slug: gama-software/services
 * Categories: featured, text
 * Inserter: yes
 * Description: The editable services grid for the Gama Software homepage.
 *
 * @package GamaSoftware
 */

?>
<!-- wp:group {"tagName":"section","anchor":"services","align":"full","className":"gama-services","backgroundColor":"surface-subtle","layout":{"type":"constrained"}} -->
<section id="services" class="wp-block-group alignfull gama-services has-surface-subtle-background-color has-background">
	<!-- wp:group {"align":"wide","className":"gama-services__content","layout":{"type":"constrained"}} -->
	<div class="wp-block-group alignwide gama-services__content">
		<!-- wp:heading {"level":2,"textAlign":"center","fontSize":"heading-2"} -->
		<h2 class="wp-block-heading has-text-align-center has-heading-2-font-size"><?php esc_html_e( 'Nasze Usługi', 'gama-software' ); ?></h2>
		<!-- /wp:heading -->

		<!-- wp:group {"className":"gama-services__grid","layout":{"type":"grid","minimumColumnWidth":"20rem"}} -->
		<div class="wp-block-group gama-services__grid">
			<!-- wp:group {"className":"gama-service-card","backgroundColor":"base","layout":{"type":"constrained"}} -->
			<div class="wp-block-group gama-service-card has-base-background-color has-background">
				<!-- wp:image {"sizeSlug":"full","linkDestination":"none","className":"gama-service-card__icon"} -->
				<figure class="wp-block-image size-full gama-service-card__icon"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/icons/service-ecommerce.svg' ) ); ?>" alt="" /></figure>
				<!-- /wp:image -->

				<!-- wp:heading {"level":3,"fontSize":"heading-3"} -->
				<h3 class="wp-block-heading has-heading-3-font-size"><?php esc_html_e( 'Wdrożenia E-commerce', 'gama-software' ); ?></h3>
				<!-- /wp:heading -->

				<!-- wp:paragraph {"textColor":"text-card-muted"} -->
				<p class="has-text-card-muted-color has-text-color"><?php esc_html_e( 'Kompleksowe wdrożenia platform e-commerce, w tym Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po uruchomienie sklepu.', 'gama-software' ); ?></p>
				<!-- /wp:paragraph -->
			</div>
			<!-- /wp:group -->

			<!-- wp:group {"className":"gama-service-card","backgroundColor":"base","layout":{"type":"constrained"}} -->
			<div class="wp-block-group gama-service-card has-base-background-color has-background">
				<!-- wp:image {"sizeSlug":"full","linkDestination":"none","className":"gama-service-card__icon"} -->
				<figure class="wp-block-image size-full gama-service-card__icon"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/icons/service-consulting.svg' ) ); ?>" alt="" /></figure>
				<!-- /wp:image -->

				<!-- wp:heading {"level":3,"fontSize":"heading-3"} -->
				<h3 class="wp-block-heading has-heading-3-font-size"><?php esc_html_e( 'Konsultacje E-commerce', 'gama-software' ); ?></h3>
				<!-- /wp:heading -->

				<!-- wp:paragraph {"textColor":"text-card-muted"} -->
				<p class="has-text-card-muted-color has-text-color"><?php esc_html_e( 'Profesjonalne doradztwo w zakresie strategii e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych rozwiązań technologicznych.', 'gama-software' ); ?></p>
				<!-- /wp:paragraph -->
			</div>
			<!-- /wp:group -->

			<!-- wp:group {"className":"gama-service-card","backgroundColor":"base","layout":{"type":"constrained"}} -->
			<div class="wp-block-group gama-service-card has-base-background-color has-background">
				<!-- wp:image {"sizeSlug":"full","linkDestination":"none","className":"gama-service-card__icon"} -->
				<figure class="wp-block-image size-full gama-service-card__icon"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/icons/service-ai.svg' ) ); ?>" alt="" /></figure>
				<!-- /wp:image -->

				<!-- wp:heading {"level":3,"fontSize":"heading-3"} -->
				<h3 class="wp-block-heading has-heading-3-font-size"><?php esc_html_e( 'Agenci AI', 'gama-software' ); ?></h3>
				<!-- /wp:heading -->

				<!-- wp:paragraph {"textColor":"text-card-muted"} -->
				<p class="has-text-card-muted-color has-text-color"><?php esc_html_e( 'Budujemy inteligentnych asystentów AI, którzy automatyzują obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu online.', 'gama-software' ); ?></p>
				<!-- /wp:paragraph -->
			</div>
			<!-- /wp:group -->
		</div>
		<!-- /wp:group -->
	</div>
	<!-- /wp:group -->
</section>
<!-- /wp:group -->
