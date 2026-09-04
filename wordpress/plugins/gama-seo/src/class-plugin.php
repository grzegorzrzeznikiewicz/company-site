<?php
/**
 * SEO integration owned by the Gama Software site.
 *
 * @package GamaSeo
 */

declare(strict_types=1);

namespace GamaSoftware\Seo;

/** Provide a single, deterministic source of public SEO metadata. */
final class Plugin {
	private const HOME_TITLE = 'Gama Software — E-commerce, Magento 2 i agenci AI';

	private const HOME_DESCRIPTION = 'Gama Software specjalizuje się we wdrożeniach i konsultacjach e-commerce oraz budowaniu agentów AI dla biznesu.';

	/** Register WordPress hooks. */
	public function register(): void {
		add_filter( 'pre_get_document_title', array( $this, 'filter_document_title' ) );
		add_filter( 'document_title_parts', array( $this, 'filter_document_title_parts' ) );
		add_filter( 'language_attributes', array( $this, 'filter_language_attributes' ) );
		add_filter( 'wp_robots', array( $this, 'filter_robots' ), 100 );
		add_filter( 'robots_txt', array( $this, 'filter_robots_text' ), 100, 2 );
		add_filter( 'pre_handle_404', array( $this, 'preserve_sitemap_status' ), 10, 2 );
		remove_action( 'wp_head', 'rel_canonical' );
		add_action( 'wp_head', array( $this, 'render_head' ), 1 );
		add_action( 'template_redirect', array( $this, 'redirect_legacy_sitemap' ), 1 );
	}

	/**
	 * Publish the approved content language independently of installed admin translations.
	 *
	 * @param string $output Existing language attributes.
	 */
	public function filter_language_attributes( string $output ): string {
		if ( preg_match( '/\blang=("|\')[^"\']*\1/', $output ) ) {
			return (string) preg_replace( '/\blang=("|\')[^"\']*\1/', 'lang="pl-PL"', $output, 1 );
		}
		return 'lang="pl-PL" ' . $output;
	}

	/**
	 * Keep a valid Core sitemap response at HTTP 200 on the pinned Core version.
	 *
	 * @param bool|null $preempt Existing pre-emption decision.
	 * @param \WP_Query $query   Main query.
	 * @return bool|null
	 */
	public function preserve_sitemap_status( ?bool $preempt, \WP_Query $query ): ?bool {
		unset( $query );
		if ( get_query_var( 'sitemap' ) || get_query_var( 'sitemap-stylesheet' ) ) {
			return true;
		}
		return $preempt;
	}

	/**
	 * Return the approved homepage title without a duplicate site-name suffix.
	 *
	 * @param string $title Existing document title.
	 */
	public function filter_document_title( string $title ): string {
		return is_front_page() ? self::HOME_TITLE : $title;
	}

	/**
	 * Keep other document titles descriptive and consistently branded.
	 *
	 * @param array<string, string> $parts WordPress title parts.
	 * @return array<string, string>
	 */
	public function filter_document_title_parts( array $parts ): array {
		if ( is_front_page() ) {
			$parts['title'] = self::HOME_TITLE;
			unset( $parts['site'], $parts['tagline'] );
		}
		return $parts;
	}

	/**
	 * Prevent indexing everywhere except the explicitly configured production environment.
	 *
	 * @param array<string, bool|string> $robots Existing robots directives.
	 * @return array<string, bool|string>
	 */
	public function filter_robots( array $robots ): array {
		unset( $robots );
		if ( $this->is_production() ) {
			return array(
				'index'                   => true,
				'follow'                  => true,
				'max-image-preview:large' => true,
			);
		}

		return array(
			'noindex'   => true,
			'nofollow'  => true,
			'noarchive' => true,
		);
	}

	/**
	 * Render an unambiguous virtual robots.txt for the active environment.
	 *
	 * @param string $output Existing output.
	 * @param bool   $is_public Whether WordPress is configured as public.
	 */
	public function filter_robots_text( string $output, bool $is_public ): string {
		unset( $output, $is_public );
		if ( ! $this->is_production() ) {
			return "User-agent: *\nDisallow: /\n";
		}

		return "User-agent: *\nAllow: /\nSitemap: " . home_url( '/wp-sitemap.xml' ) . "\n";
	}

	/** Render canonical, description, Open Graph and Schema.org data. */
	public function render_head(): void {
		if ( is_admin() || is_feed() || is_robots() ) {
			return;
		}

		$title       = wp_get_document_title();
		$description = $this->description();
		$canonical   = $this->canonical_url();
		$type        = is_singular( 'post' ) ? 'article' : 'website';

		printf( "<meta name=\"description\" content=\"%s\" />\n", esc_attr( $description ) );
		printf( "<link rel=\"canonical\" href=\"%s\" />\n", esc_url( $canonical ) );
		printf( "<meta property=\"og:title\" content=\"%s\" />\n", esc_attr( $title ) );
		printf( "<meta property=\"og:description\" content=\"%s\" />\n", esc_attr( $description ) );
		printf( "<meta property=\"og:url\" content=\"%s\" />\n", esc_url( $canonical ) );
		printf( "<meta property=\"og:type\" content=\"%s\" />\n", esc_attr( $type ) );

		$schema = array(
			'@context' => 'https://schema.org',
			'@graph'   => array(
				array(
					'@type' => 'Organization',
					'@id'   => home_url( '/#organization' ),
					'name'  => 'Gama Software',
					'url'   => home_url( '/' ),
					'logo'  => $this->logo_url(),
				),
				array(
					'@type'       => 'WebSite',
					'@id'         => home_url( '/#website' ),
					'url'         => home_url( '/' ),
					'name'        => 'Gama Software',
					'description' => self::HOME_DESCRIPTION,
					'publisher'   => array( '@id' => home_url( '/#organization' ) ),
					'inLanguage'  => 'pl-PL',
				),
			),
		);

		printf(
			"<script type=\"application/ld+json\">%s</script>\n",
			wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE )
		);
	}

	/** Redirect the legacy sitemap URL once to the WordPress Core sitemap. */
	public function redirect_legacy_sitemap(): void {
		$request_uri = isset( $_SERVER['REQUEST_URI'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ) ) : '';
		$path        = wp_parse_url( $request_uri, PHP_URL_PATH );
		if ( '/sitemap.xml' !== $path ) {
			return;
		}

		wp_safe_redirect( home_url( '/wp-sitemap.xml' ), 301, 'Gama SEO' );
		exit;
	}

	/** Resolve the current page's canonical URL. */
	private function canonical_url(): string {
		if ( is_front_page() ) {
			return home_url( '/' );
		}
		if ( is_home() ) {
			return home_url( '/blog/' );
		}
		if ( is_singular() ) {
			$permalink = get_permalink();
			return is_string( $permalink ) ? $permalink : home_url( '/' );
		}

		return (string) get_pagenum_link( max( 1, get_query_var( 'paged' ) ) );
	}

	/** Resolve a concise description without adding an editable duplicate field. */
	private function description(): string {
		if ( is_front_page() || is_home() ) {
			return self::HOME_DESCRIPTION;
		}

		if ( is_singular() ) {
			$excerpt = get_the_excerpt();
			if ( '' !== trim( $excerpt ) ) {
				return wp_trim_words( wp_strip_all_tags( $excerpt ), 30, '…' );
			}
		}

		return self::HOME_DESCRIPTION;
	}

	/** Resolve the media-library logo URL when configured. */
	private function logo_url(): string {
		$logo_id = (int) get_theme_mod( 'custom_logo', 0 );
		$logo    = $logo_id > 0 ? wp_get_attachment_image_url( $logo_id, 'full' ) : false;
		return is_string( $logo ) ? $logo : '';
	}

	/** Only a deliberate production environment may be indexed. */
	private function is_production(): bool {
		return 'production' === wp_get_environment_type();
	}
}
