<?php
/**
 * Title: Gama Software Modules
 * Slug: gama-software/modules
 * Categories: featured, text
 * Inserter: yes
 * Description: The editable Magento modules offer for the Gama Software homepage.
 *
 * @package GamaSoftware
 */

$gama_software_module_icon = get_theme_file_uri( 'assets/icons/module-package.svg' );
?>
<!-- wp:group {"tagName":"section","anchor":"modules","align":"full","className":"gama-modules","backgroundColor":"base","layout":{"type":"constrained"}} -->
<section id="modules" class="wp-block-group alignfull gama-modules has-base-background-color has-background">
	<!-- wp:group {"align":"wide","className":"gama-modules__content","layout":{"type":"constrained"}} -->
	<div class="wp-block-group alignwide gama-modules__content">
		<!-- wp:group {"className":"gama-modules__intro","layout":{"type":"constrained"}} -->
		<div class="wp-block-group gama-modules__intro">
			<!-- wp:heading {"level":2,"textAlign":"center","fontSize":"heading-2"} -->
			<h2 class="wp-block-heading has-text-align-center has-heading-2-font-size"><?php esc_html_e( 'Moduły Magento 2', 'gama-software' ); ?></h2>
			<!-- /wp:heading -->
			<!-- wp:paragraph {"align":"center","textColor":"text-muted","fontSize":"lead"} -->
			<p class="has-text-align-center has-text-muted-color has-text-color has-lead-font-size"><?php esc_html_e( 'Profesjonalne rozszerzenia dostępne w modelu subskrypcji', 'gama-software' ); ?></p>
			<!-- /wp:paragraph -->
		</div>
		<!-- /wp:group -->

		<!-- wp:group {"className":"gama-modules__grid","layout":{"type":"grid","minimumColumnWidth":"20rem"}} -->
		<div class="wp-block-group gama-modules__grid">
			<?php
			$gama_software_modules = array(
				array( 'Advanced SEO Suite', 'Kompleksowe narzędzie do optymalizacji SEO', array( 'Automatyczne generowanie meta tagów', 'Optymalizacja URL', 'Rich snippets', 'Sitemap XML', 'Analiza SEO on-page' ) ),
				array( 'Smart Product Recommendations', 'AI-powered rekomendacje produktów', array( 'Algorytmy uczenia maszynowego', 'Personalizacja dla użytkownika', 'Cross-selling i up-selling', 'Analityka skuteczności', 'A/B testing' ) ),
				array( 'Enhanced Checkout', 'Zoptymalizowany proces zakupowy', array( 'One-step checkout', 'Autouzupełnianie adresów', 'Integracje z kurierami', 'Płatności Express', 'Optymalizacja konwersji' ) ),
				array( 'Inventory Management Pro', 'Zaawansowane zarządzanie magazynem', array( 'Multi-warehouse support', 'Automatyczne powiadomienia', 'Prognozowanie zapasów', 'Integracja z ERP', 'Raporty i analityka' ) ),
				array( 'Customer Loyalty Program', 'Program lojalnościowy dla klientów', array( 'System punktów i nagród', 'Poziomy lojalnościowe', 'Spersonalizowane promocje', 'Gamifikacja', 'Integracja z newsletter' ) ),
				array( 'Performance Optimizer', 'Optymalizacja wydajności sklepu', array( 'Lazy loading obrazów', 'Optymalizacja bazy danych', 'Cache management', 'CDN integration', 'Monitoring wydajności' ) ),
			);
			foreach ( $gama_software_modules as $gama_software_module ) :
				?>
				<!-- wp:group {"className":"gama-module-card","backgroundColor":"base","layout":{"type":"constrained"}} -->
				<div class="wp-block-group gama-module-card has-base-background-color has-background">
					<!-- wp:group {"className":"gama-module-card__header","layout":{"type":"flex","flexWrap":"nowrap","justifyContent":"space-between","verticalAlignment":"top"}} -->
					<div class="wp-block-group gama-module-card__header">
						<!-- wp:group {"layout":{"type":"constrained"}} -->
						<div class="wp-block-group">
							<!-- wp:heading {"level":3,"fontSize":"heading-3"} -->
							<h3 class="wp-block-heading has-heading-3-font-size"><?php echo esc_html( $gama_software_module[0] ); ?></h3>
							<!-- /wp:heading -->
							<!-- wp:paragraph {"textColor":"text-card-muted"} -->
							<p class="has-text-card-muted-color has-text-color"><?php echo esc_html( $gama_software_module[1] ); ?></p>
							<!-- /wp:paragraph -->
						</div>
						<!-- /wp:group -->
						<!-- wp:image {"sizeSlug":"full","linkDestination":"none","url":"<?php echo esc_url( $gama_software_module_icon ); ?>","alt":"","className":"gama-module-card__icon"} -->
						<figure class="wp-block-image size-full gama-module-card__icon"><img src="<?php echo esc_url( $gama_software_module_icon ); ?>" alt="" /></figure>
						<!-- /wp:image -->
					</div>
					<!-- /wp:group -->
					<!-- wp:list {"className":"gama-module-card__features","textColor":"text-card-muted","fontSize":"small"} -->
					<ul class="wp-block-list gama-module-card__features has-text-card-muted-color has-text-color has-small-font-size">
						<?php foreach ( $gama_software_module[2] as $gama_software_feature ) : ?>
							<!-- wp:list-item --><li><?php echo esc_html( $gama_software_feature ); ?></li><!-- /wp:list-item -->
						<?php endforeach; ?>
					</ul>
					<!-- /wp:list -->
				</div>
				<!-- /wp:group -->
			<?php endforeach; ?>
		</div>
		<!-- /wp:group -->

		<!-- wp:group {"className":"gama-modules__action","layout":{"type":"constrained"}} -->
		<div class="wp-block-group gama-modules__action">
			<!-- wp:paragraph {"align":"center","textColor":"text-muted"} -->
			<p class="has-text-align-center has-text-muted-color has-text-color"><?php esc_html_e( 'Wkrótce dostępne w formie subskrypcji', 'gama-software' ); ?></p>
			<!-- /wp:paragraph -->
			<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
			<div class="wp-block-buttons"><!-- wp:button -->
				<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="/#contact"><?php esc_html_e( 'Zapisz się na listę oczekujących', 'gama-software' ); ?></a></div>
			<!-- /wp:button --></div>
			<!-- /wp:buttons -->
		</div>
		<!-- /wp:group -->
	</div>
	<!-- /wp:group -->
</section>
<!-- /wp:group -->
