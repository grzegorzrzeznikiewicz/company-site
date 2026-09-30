export default {
  extends: ['stylelint-config-standard'],
  rules: {
    // WordPress preset variables use a deliberate double-hyphen hierarchy.
    'custom-property-pattern': null,
    // First-party and WordPress block classes use BEM-style underscores.
    'selector-class-pattern': null,
    // Theme rules are grouped by component instead of global specificity.
    'no-descending-specificity': null,
    // Keep the broadly supported min/max syntax used by the WordPress theme.
    'media-feature-range-notation': null,
  },
};
