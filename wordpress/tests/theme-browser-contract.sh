#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$ROOT_DIR/qa/e2e/package.json"
lock="$ROOT_DIR/qa/e2e/package-lock.json"
dockerfile="$ROOT_DIR/qa/browser.Dockerfile"
global_styles_spec="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts"
navigation_spec="$ROOT_DIR/qa/e2e/specs/header-footer-navigation.spec.ts"
hero_spec="$ROOT_DIR/qa/e2e/specs/hero.spec.ts"
services_spec="$ROOT_DIR/qa/e2e/specs/services.spec.ts"
modules_spec="$ROOT_DIR/qa/e2e/specs/modules.spec.ts"
blog_spec="$ROOT_DIR/qa/e2e/specs/blog.spec.ts"
contact_section_spec="$ROOT_DIR/qa/e2e/specs/contact-section.spec.ts"
content_spec="$ROOT_DIR/qa/e2e/specs/content.spec.ts"
shared_helpers="$ROOT_DIR/qa/e2e/specs/support/wordpress.ts"
snapshot_dir="$ROOT_DIR/qa/e2e/specs/global-styles.spec.ts-snapshots"
config="$ROOT_DIR/qa/e2e/playwright.config.ts"
timeout_policy="$ROOT_DIR/qa/e2e/specs/support/timeout-policy-reporter.cjs"
timeout_policy_contract="$ROOT_DIR/qa/e2e/specs/support/timeout-policy-contract.cjs"
timeout_policy_tsconfig="$ROOT_DIR/qa/e2e/timeout-policy.tsconfig.json"
playwright_launcher="$ROOT_DIR/qa/e2e/specs/support/run-playwright.cjs"
test_package="$ROOT_DIR/bin/test-package"

grep -Fq '"node": "24.*"' "$manifest"
grep -Fq '"@axe-core/playwright": "4.13.0"' "$manifest"
grep -Fq '"@playwright/test": "1.62.1"' "$manifest"
grep -Fq '"node_modules/@playwright/test"' "$lock"
grep -Fq '"version": "1.62.1"' "$lock"
grep -Fq 'mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e' "$dockerfile"
grep -Fq 'npm ci --ignore-scripts' "$dockerfile"
[[ -f "$global_styles_spec" ]]
[[ -f "$navigation_spec" ]]
[[ -f "$hero_spec" ]]
[[ -f "$services_spec" ]]
[[ -f "$modules_spec" ]]
[[ -f "$blog_spec" ]]
[[ -f "$contact_section_spec" ]]
[[ -f "$content_spec" ]]
[[ -f "$shared_helpers" ]]
[[ -f "$timeout_policy" ]]
[[ -f "$timeout_policy_contract" ]]
[[ -f "$timeout_policy_tsconfig" ]]
[[ -f "$playwright_launcher" ]]
if [[ "$(<"$timeout_policy_tsconfig")" != $'{\n  "compilerOptions": {}\n}' ]]; then
  echo 'Timeout policy TypeScript configuration is not the reviewed empty compilerOptions object.' >&2
  exit 1
fi
grep -Fq "reducedMotion: 'reduce'" "$config"
grep -Fq 'threshold: 0.2' "$config"
grep -Fq 'maxDiffPixelRatio: 0.003' "$config"
grep -Fq 'globalTimeout: 0' "$config"
grep -Fq 'retries: 0' "$config"
grep -Fq "tsconfig: './timeout-policy.tsconfig.json'" "$config"
grep -Fq "['./specs/support/timeout-policy-reporter.cjs']" "$config"
grep -Fq '@global-styles' "$global_styles_spec"
for tag in \
  '@global-styles-editor-choices' \
  '@global-styles-front-snapshots' \
  '@global-styles-editor-snapshots' \
  '@global-styles-focus' \
  '@global-styles-admin-persistence' \
  '@global-styles-dpr2'; do
  grep -Fq "$tag" "$global_styles_spec"
  grep -Fq "GAMA_PLAYWRIGHT_RUN=${tag#@}" "$test_package"
  grep -Fq -- "--grep $tag" "$test_package"
done
for tag in '@navigation-initial' '@navigation-save' '@navigation-persisted'; do
  grep -Fq "$tag" "$navigation_spec"
done
grep -Fq '@hero' "$hero_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=hero' "$test_package"
grep -Fq -- '--grep @hero' "$test_package"
grep -Fq '@services' "$services_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=services' "$test_package"
grep -Fq -- '--grep @services' "$test_package"
grep -Fq '@modules' "$modules_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=modules' "$test_package"
grep -Fq -- '--grep @modules' "$test_package"
grep -Fq '@blog' "$blog_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=blog' "$test_package"
grep -Fq -- '--grep @blog' "$test_package"
grep -Fq '@contact-section' "$contact_section_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=contact-section' "$test_package"
grep -Fq -- '--grep @contact-section' "$test_package"
grep -Fq '@content' "$content_spec"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=content' "$test_package"
grep -Fq -- '--grep @content' "$test_package"
for required_services_assertion in \
  'main section#services.gama-services' \
  'gama-service-card' \
  'expectedColumns' \
  'sectionBounds' \
  'hasOverflow'; do
  grep -Fq "$required_services_assertion" "$services_spec"
done
if [[ "$(grep -Fc 'assertDocumentScrollUnlocked(page)' "$navigation_spec")" -ne 5 ]]; then
  echo 'Navigation acceptance must prove computed scroll unlock before open and after both close paths.' >&2
  exit 1
fi
for persisted_token in \
  'const persistedMobileWidths = [320, 390] as const;' \
  'assertPersistedMobileNavigation' \
  'storedNavigationAttributes.overlayMenu ??' \
  'navigationBlockType.attributes.overlayMenu.default' \
  "storedNavigationAttributes.ariaLabel).toBe('Główna nawigacja')" \
  'storedNavigationAttributes.className).toBe('; do
  if ! grep -Fq "$persisted_token" "$navigation_spec"; then
    echo "Persisted navigation acceptance is missing: $persisted_token" >&2
    exit 1
  fi
done
grep -Fq 'waitForEditorCanvas' "$shared_helpers"
grep -Fq "waitUntil: 'domcontentloaded'" "$shared_helpers"
grep -Fq 'timeout: 45_000' "$shared_helpers"
grep -Fq "waitForLoadState('domcontentloaded'" "$shared_helpers"
visible_canvas_line="$(grep -nFx "  const visibleCanvas = page.locator('iframe[name=\"editor-canvas\"]:visible');" "$shared_helpers" | cut -d: -f1 || true)"
welcome_selector_line="$(grep -nFx "  const welcome = page.getByRole('dialog', {" "$shared_helpers" | cut -d: -f1 || true)"
welcome_name_line="$(grep -nFx '    name: /Welcome to the (?:site )?editor/i,' "$shared_helpers" | cut -d: -f1 || true)"
welcome_cache_line="$(grep -nFx 'const knownWelcomeGuideUsers = new Set<string>();' "$shared_helpers" | cut -d: -f1 || true)"
welcome_user_registration_line="$(grep -nFx '  loggedInUserByPage.set(page, user);' "$shared_helpers" | cut -d: -f1 || true)"
editor_ready_union_line="$(grep -nFx '  await expect(visibleCanvas.or(welcome).first()).toBeVisible({' "$shared_helpers" | cut -d: -f1 || true)"
welcome_probe_line="$(grep -nFx '  if (shouldCheckWelcome && (await welcome.isVisible())) {' "$shared_helpers" | cut -d: -f1 || true)"
canvas_ready_line="$(grep -nFx '  await expect(canvas).toBeVisible({ timeout: 60_000 });' "$shared_helpers" | cut -d: -f1 || true)"
if [[ ! "$visible_canvas_line" =~ ^[0-9]+$ \
  || ! "$welcome_selector_line" =~ ^[0-9]+$ \
  || ! "$welcome_name_line" =~ ^[0-9]+$ \
  || ! "$welcome_cache_line" =~ ^[0-9]+$ \
  || ! "$welcome_user_registration_line" =~ ^[0-9]+$ \
  || ! "$editor_ready_union_line" =~ ^[0-9]+$ \
  || ! "$welcome_probe_line" =~ ^[0-9]+$ \
  || ! "$canvas_ready_line" =~ ^[0-9]+$ \
  || "$visible_canvas_line" -ge "$editor_ready_union_line" \
  || "$welcome_selector_line" -ge "$editor_ready_union_line" \
  || "$welcome_selector_line" -ge "$welcome_name_line" \
  || "$welcome_name_line" -ge "$editor_ready_union_line" \
  || "$editor_ready_union_line" -ge "$welcome_probe_line" \
  || "$welcome_probe_line" -ge "$canvas_ready_line" ]]; then
  echo 'Editor readiness must resolve a visible canvas-or-welcome gate before requiring the canvas.' >&2
  exit 1
fi
password_fill_line="$(grep -nFx '  await passwordField.fill(password);' "$shared_helpers" | cut -d: -f1)"
username_fill_line="$(grep -nFx '  await usernameField.fill(user);' "$shared_helpers" | cut -d: -f1)"
login_load_line="$(grep -nFx "  await page.waitForLoadState('load');" "$shared_helpers" | cut -d: -f1)"
username_focus_line="$(grep -nFx '  await expect(usernameField).toBeFocused();' "$shared_helpers" | cut -d: -f1)"
username_assertion_line="$(grep -nFx '  expect(usernameMatchesExpectedValue).toBe(true);' "$shared_helpers" | cut -d: -f1)"
password_assertion_line="$(grep -nFx '  expect(passwordMatchesExpectedValue).toBe(true);' "$shared_helpers" | cut -d: -f1)"
submit_line="$(grep -nF "page.locator('#wp-submit').click()" "$shared_helpers" | cut -d: -f1)"
if [[ ! "$password_fill_line" =~ ^[0-9]+$ \
  || ! "$username_fill_line" =~ ^[0-9]+$ \
  || ! "$login_load_line" =~ ^[0-9]+$ \
  || ! "$username_focus_line" =~ ^[0-9]+$ \
  || ! "$username_assertion_line" =~ ^[0-9]+$ \
  || ! "$password_assertion_line" =~ ^[0-9]+$ \
  || ! "$submit_line" =~ ^[0-9]+$ \
  || "$login_load_line" -ge "$username_focus_line" \
  || "$username_focus_line" -ge "$password_fill_line" \
  || "$password_fill_line" -ge "$username_fill_line" \
  || "$username_fill_line" -ge "$username_assertion_line" \
  || "$username_assertion_line" -ge "$password_assertion_line" \
  || "$password_assertion_line" -ge "$submit_line" ]]; then
  echo 'Login must fill password before username and verify both exact values before submit.' >&2
  exit 1
fi
grep -Fq 'waitForExactEditorParagraph' "$global_styles_spec"
grep -Fq 'extractNavigationBlockAttributes' "$navigation_spec"
grep -Fq 'self-closing Navigation fixture' "$navigation_spec"
grep -Fq 'inline-inner-block Navigation fixture' "$navigation_spec"
grep -Fq 'COPY wordpress/qa/e2e/specs ./specs' "$dockerfile"
grep -Fq 'COPY wordpress/qa/e2e/timeout-policy.tsconfig.json ./' "$dockerfile"
grep -Fq '01511e45db7646e2a12890de8d7866caa0754c8799db6407a6345236f4bed0c4' "$timeout_policy"
grep -Fq 'node ./specs/support/timeout-policy-contract.cjs' "$test_package"
grep -Fq 'PLAYWRIGHT_TEST=(' "$test_package"
grep -Fq 'node ./specs/support/run-playwright.cjs' "$test_package"
grep -Fq 'node ./specs/support/run-playwright.cjs' "$manifest"
grep -Fq -- '--tsconfig' "$playwright_launcher"
grep -Fq './timeout-policy.tsconfig.json' "$playwright_launcher"
grep -Fq "'--update-snapshots'" "$playwright_launcher"
grep -Fq "'--update-snapshots'" "$timeout_policy_contract"
grep -Fq 'GAMA_PLAYWRIGHT_RUN=timeout-policy browser "${PLAYWRIGHT_TEST[@]}" --list' "$test_package"
for variable in \
  PW_TEST_SOURCE_TRANSFORM \
  PW_TEST_SOURCE_TRANSFORM_SCOPE \
  PW_TEST_REPORTER \
  PWDEBUG; do
  grep -Fq -- "-u $variable" "$test_package"
  grep -Fq -- "-u $variable" "$manifest"
  grep -Fq "$variable" "$playwright_launcher"
done
if [[ "$(grep -Fc 'browser "${PLAYWRIGHT_TEST[@]}"' "$test_package")" -ne 20 ]]; then
  echo 'Every one of the twenty browser runs must use the reviewed Playwright launcher.' >&2
  exit 1
fi
if grep -Fq 'browser npx playwright test' "$test_package"; then
  echo 'Browser runs must not bypass the reviewed Playwright launcher.' >&2
  exit 1
fi
grep -Fq 'Semantic timeout policy passed:' "$test_package"
if grep -Fq -- '--reporter=./specs/support/timeout-policy-reporter.cjs' "$test_package"; then
  echo 'Timeout policy must be configured for every browser run, not injected only into a listing command.' >&2
  exit 1
fi
if grep -Fq '"@babel/' "$manifest" "$lock"; then
  echo 'GSWEB-14 timeout policy must not add a parser dependency.' >&2
  exit 1
fi
grep -Fq 'watchWordPressDiagnostics' "$shared_helpers"
if ! grep -Fq '(options.expectedMissingPaths ?? []).includes(locationPath)' "$shared_helpers"; then
  echo 'Expected 404 diagnostics are not scoped to the console message location.' >&2
  exit 1
fi
if grep -Fq 'new URL(page.url()).pathname' "$shared_helpers"; then
  echo 'Expected 404 diagnostics must be scoped to the console message location.' >&2
  exit 1
fi
grep -Fq 'deviceScaleFactor' "$global_styles_spec"
grep -Fq 'does not satisfy the native 200% zoom checkpoint' "$global_styles_spec"
expected_snapshots="$(
  printf '%s\n' \
    global-styles-editor-1440-linux.png \
    global-styles-editor-390-linux.png \
    global-styles-editor-768-linux.png \
    global-styles-front-1440-linux.png \
    global-styles-front-390-linux.png \
    global-styles-front-768-linux.png
)"
actual_snapshots="$(find "$snapshot_dir" -mindepth 1 -maxdepth 1 -type f -name '*.png' -exec basename {} \; | sort)"
[[ "$actual_snapshots" == "$expected_snapshots" ]]
while IFS= read -r snapshot; do
  [[ -s "$snapshot_dir/$snapshot" ]]
done <<<"$expected_snapshots"
if grep -Eq 'COPY[[:space:]]+(\. |wordpress/ |src/|backend/)' "$dockerfile"; then
  echo 'Browser image copies outside its dedicated E2E package.' >&2
  exit 1
fi

echo 'Pinned browser image contract passed.'
