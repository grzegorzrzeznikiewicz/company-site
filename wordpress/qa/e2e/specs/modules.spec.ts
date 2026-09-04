import { expect, test, type FrameLocator, type Page } from '@playwright/test';
import { login, openEditorCanvas, rest } from './support/wordpress';

const modules = [
  [
    'Advanced SEO Suite',
    'Kompleksowe narzędzie do optymalizacji SEO',
    [
      'Automatyczne generowanie meta tagów',
      'Optymalizacja URL',
      'Rich snippets',
      'Sitemap XML',
      'Analiza SEO on-page',
    ],
  ],
  [
    'Smart Product Recommendations',
    'AI-powered rekomendacje produktów',
    [
      'Algorytmy uczenia maszynowego',
      'Personalizacja dla użytkownika',
      'Cross-selling i up-selling',
      'Analityka skuteczności',
      'A/B testing',
    ],
  ],
  [
    'Enhanced Checkout',
    'Zoptymalizowany proces zakupowy',
    [
      'One-step checkout',
      'Autouzupełnianie adresów',
      'Integracje z kurierami',
      'Płatności Express',
      'Optymalizacja konwersji',
    ],
  ],
  [
    'Inventory Management Pro',
    'Zaawansowane zarządzanie magazynem',
    [
      'Multi-warehouse support',
      'Automatyczne powiadomienia',
      'Prognozowanie zapasów',
      'Integracja z ERP',
      'Raporty i analityka',
    ],
  ],
  [
    'Customer Loyalty Program',
    'Program lojalnościowy dla klientów',
    [
      'System punktów i nagród',
      'Poziomy lojalnościowe',
      'Spersonalizowane promocje',
      'Gamifikacja',
      'Integracja z newsletter',
    ],
  ],
  [
    'Performance Optimizer',
    'Optymalizacja wydajności sklepu',
    [
      'Lazy loading obrazów',
      'Optymalizacja bazy danych',
      'Cache management',
      'CDN integration',
      'Monitoring wydajności',
    ],
  ],
] as const;

function modulesSection(page: Page) {
  return page.locator('main section#modules.gama-modules');
}

async function openFrontPageTemplate(page: Page): Promise<FrameLocator> {
  const templateId = 'gama-software//front-page';
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(templateId)}&postType=wp_template&canvas=edit`,
  );
  await expect(frame.locator('section.gama-modules')).toBeVisible();
  return frame;
}

async function saveFrontPageTemplate(page: Page): Promise<void> {
  const save = page.getByRole('button', { name: 'Save', exact: true });
  await expect(save).toBeEnabled();
  await save.click();
  await expect(
    page
      .locator('.components-snackbar__content')
      .getByText('Template updated.', { exact: true }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(save).toBeDisabled({ timeout: 30_000 });
}

test('renders the complete modules offer with a working contact action @modules', async ({
  page,
}) => {
  for (const [width, expectedColumns] of [
    [320, 1],
    [768, 2],
    [1440, 3],
  ] as const) {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);

    const section = modulesSection(page);
    await expect(section).toHaveCount(1);
    await expect(
      section.getByRole('heading', { level: 2, name: 'Moduły Magento 2' }),
    ).toHaveCount(1);
    await expect(
      section.getByText(
        'Profesjonalne rozszerzenia dostępne w modelu subskrypcji',
        { exact: true },
      ),
    ).toHaveCount(1);

    const cards = section.locator('.gama-module-card');
    await expect(cards).toHaveCount(modules.length);
    for (const [title, description, features] of modules) {
      const card = cards.filter({ hasText: title });
      await expect(card).toHaveCount(1);
      await expect(
        card.getByRole('heading', { level: 3, name: title }),
      ).toHaveCount(1);
      await expect(card.getByText(description, { exact: true })).toHaveCount(1);
      const list = card.getByRole('list');
      await expect(list).toHaveCount(1);
      await expect(list.getByRole('listitem')).toHaveCount(features.length);
      for (const feature of features) {
        await expect(list.getByText(feature, { exact: true })).toHaveCount(1);
      }
    }

    await expect(
      section.getByText('Wkrótce dostępne w formie subskrypcji', {
        exact: true,
      }),
    ).toHaveCount(1);
    const action = section.getByRole('link', {
      name: 'Zapisz się na listę oczekujących',
    });
    await expect(action).toHaveAttribute('href', '/#contact');

    const positions = await cards.evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return { left: Math.round(rect.left), top: Math.round(rect.top) };
      }),
    );
    const firstRowTop = Math.min(...positions.map(({ top }) => top));
    expect(
      positions.filter(({ top }) => Math.abs(top - firstRowTop) <= 1),
    ).toHaveLength(expectedColumns);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      ),
    ).toBe(false);
  }
});

test('lets an Editor vary, reorder and edit module cards and remove the final action @modules', async ({
  page,
}) => {
  const movedTitle = 'Moduł przeniesiony na początek przez redaktora';
  const editorChangedTitle = 'Tytuł zmieniony bezpośrednio w edytorze';
  const updatedDescription =
    'Opis zmieniony bez wdrożenia kodu i bez utraty elastycznego układu.';
  const longFeature =
    'Bardzo długa pozycja listy funkcji zachowująca pełną treść bez przycinania na telefonie i przy powiększeniu interfejsu';
  const optionalLinkLabel = 'Zapytaj o wybrany moduł';

  await login(page, 'theme-navigation-editor', 'navigation-editor-test-only');
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['editor']);
  expect(currentUser.capabilities.activate_plugins ?? false).toBe(false);

  const frame = await openFrontPageTemplate(page);
  await expect(
    frame.locator('[data-type="core/group"].gama-module-card'),
  ).toHaveCount(6);

  const titleBlock = frame
    .locator('[data-type="core/heading"]')
    .filter({ hasText: modules[0][0] });
  await titleBlock.click();
  const editableTitle = frame
    .locator('[data-type="core/heading"][contenteditable="true"]')
    .filter({ hasText: modules[0][0] });
  await expect(editableTitle).toHaveCount(1);
  await editableTitle.fill(editorChangedTitle);

  const descriptionBlock = frame
    .locator('[data-type="core/paragraph"]')
    .filter({ hasText: modules[0][1] });
  await descriptionBlock.click();
  const editableDescription = frame
    .locator('[data-type="core/paragraph"][contenteditable="true"]')
    .filter({ hasText: modules[0][1] });
  await expect(editableDescription).toHaveCount(1);
  await editableDescription.fill(updatedDescription);

  const mutation = await page.evaluate(
    ({ description, feature, linkLabel, title }) => {
      const wordpress = (window as typeof window & { wp: any }).wp;
      const select = wordpress.data.select('core/block-editor');
      const dispatch = wordpress.data.dispatch('core/block-editor');
      const findByClassName = (
        blocks: any[],
        className: string,
      ): any | undefined => {
        for (const block of blocks) {
          if (block.attributes?.className === className) return block;
          const nested = findByClassName(block.innerBlocks ?? [], className);
          if (nested !== undefined) return nested;
        }

        return undefined;
      };
      const findDescendant = (block: any, name: string): any | undefined => {
        for (const child of block.innerBlocks ?? []) {
          if (child.name === name) return child;
          const nested = findDescendant(child, name);
          if (nested !== undefined) return nested;
        }

        return undefined;
      };
      const grid = () => {
        const block = findByClassName(select.getBlocks(), 'gama-modules__grid');
        if (block === undefined) {
          throw new Error('The editable Modules Grid block was not found.');
        }

        return block;
      };
      const cards = () =>
        grid().innerBlocks.filter(
          (block: any) => block.attributes?.className === 'gama-module-card',
        );

      dispatch.removeBlocks(
        cards()
          .slice(2)
          .map((block: any) => block.clientId),
        false,
      );
      const counts = [cards().length];
      for (const targetCount of [4, 7]) {
        while (cards().length < targetCount) {
          dispatch.duplicateBlocks([cards()[0].clientId], false);
        }
        counts.push(cards().length);
      }

      const lastCard = cards().at(-1);
      const heading = lastCard && findDescendant(lastCard, 'core/heading');
      const paragraph = lastCard && findDescendant(lastCard, 'core/paragraph');
      const list = lastCard && findDescendant(lastCard, 'core/list');
      if (
        lastCard === undefined ||
        heading === undefined ||
        paragraph === undefined ||
        list === undefined
      ) {
        throw new Error('The duplicated module card is incomplete.');
      }
      dispatch.updateBlockAttributes(heading.clientId, { content: title });
      dispatch.updateBlockAttributes(paragraph.clientId, {
        content: description,
      });
      dispatch.insertBlock(
        wordpress.blocks.createBlock('core/list-item', { content: feature }),
        undefined,
        list.clientId,
        false,
      );
      dispatch.insertBlock(
        wordpress.blocks.createBlock('core/buttons', {}, [
          wordpress.blocks.createBlock('core/button', {
            text: linkLabel,
            url: '/#contact',
          }),
        ]),
        undefined,
        lastCard.clientId,
        false,
      );
      dispatch.moveBlockToPosition(
        lastCard.clientId,
        grid().clientId,
        grid().clientId,
        0,
      );

      const action = findByClassName(
        select.getBlocks(),
        'gama-modules__action',
      );
      if (action === undefined) {
        throw new Error('The optional Modules action block was not found.');
      }
      dispatch.removeBlocks([action.clientId], false);

      return {
        counts,
        firstTitle: findDescendant(cards()[0], 'core/heading')?.attributes
          ?.content,
      };
    },
    {
      description: updatedDescription,
      feature: longFeature,
      linkLabel: optionalLinkLabel,
      title: movedTitle,
    },
  );
  expect(mutation.counts).toEqual([2, 4, 7]);
  expect(mutation.firstTitle).toBe(movedTitle);
  await expect(
    frame.locator('[data-type="core/group"].gama-module-card'),
  ).toHaveCount(7);
  await expect(
    frame.locator('[data-type="core/heading"]').filter({ hasText: movedTitle }),
  ).toBeVisible();

  await saveFrontPageTemplate(page);
  const frontPage = await rest<any>(
    page,
    '/wp/v2/templates/gama-software//front-page?context=edit',
  );
  expect(frontPage.source).toBe('custom');
  expect(frontPage.has_theme_file).toBe(true);
  expect(frontPage.content.raw).toContain(movedTitle);
  expect(frontPage.content.raw).toContain(editorChangedTitle);
  expect(frontPage.content.raw).toContain(updatedDescription);
  expect(frontPage.content.raw).toContain(longFeature);
  expect(frontPage.content.raw).toContain(optionalLinkLabel);
  expect(frontPage.content.raw).not.toContain(
    'Zapisz się na listę oczekujących',
  );

  for (const [width, expectedColumns] of [
    [320, 1],
    [768, 2],
    [1440, 3],
  ] as const) {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);
    const section = modulesSection(page);
    const cards = section.locator('.gama-module-card');
    await expect(cards).toHaveCount(7);
    await expect(
      cards.first().getByRole('heading', { level: 3, name: movedTitle }),
    ).toBeVisible();
    await expect(
      cards.first().getByText(longFeature, { exact: true }),
    ).toBeVisible();
    await expect(
      cards.first().getByRole('link', { name: optionalLinkLabel }),
    ).toHaveAttribute('href', '/#contact');
    await expect(
      section.getByRole('link', {
        name: 'Zapisz się na listę oczekujących',
      }),
    ).toHaveCount(0);

    const positions = await cards.evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return { left: Math.round(rect.left), top: Math.round(rect.top) };
      }),
    );
    const firstRowTop = Math.min(...positions.map(({ top }) => top));
    expect(
      positions.filter(({ top }) => Math.abs(top - firstRowTop) <= 1),
    ).toHaveLength(expectedColumns);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      ),
    ).toBe(false);
  }
});
