import {
  expect,
  test,
  type FrameLocator,
  type Page,
} from '@playwright/test';
import { login, openEditorCanvas, rest } from './support/wordpress';

const services = [
  [
    'Wdrożenia E-commerce',
    'Kompleksowe wdrożenia platform e-commerce, w tym Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po uruchomienie sklepu.',
  ],
  [
    'Konsultacje E-commerce',
    'Profesjonalne doradztwo w zakresie strategii e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych rozwiązań technologicznych.',
  ],
  [
    'Agenci AI',
    'Budujemy inteligentnych asystentów AI, którzy automatyzują obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu online.',
  ],
] as const;

const longServiceTitle =
  'Wdrożenia E-commerce: kompleksowa strategia, architektura i uruchomienie sprzedaży wielokanałowej';
const updatedServiceDescription =
  'Redaktor może zmienić opis usługi bez wdrożenia kodu i bez utraty responsywnego układu kart.';
const movedServiceTitle = 'Karta przeniesiona na początek przez redaktora';
const serviceButton = 'Poznaj szczegóły usługi';

function servicesSection(page: Page) {
  return page.locator('main section#services.gama-services');
}

async function openFrontPageTemplate(page: Page): Promise<FrameLocator> {
  const templateId = 'gama-software//front-page';
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(templateId)}&postType=wp_template&canvas=edit`,
  );
  await expect(frame.locator('section.gama-services')).toBeVisible();
  return frame;
}

async function saveFrontPageTemplate(page: Page): Promise<void> {
  const save = page.getByRole('button', { name: 'Save', exact: true });
  await expect(save).toBeEnabled();
  await expect(
    page.getByRole('dialog', { name: 'Are you ready to save?' }),
  ).toHaveCount(0);
  await save.click();
  const confirmation = page
    .locator('.components-snackbar__content')
    .getByText('Template updated.', { exact: true });
  await expect(confirmation).toBeVisible({ timeout: 30_000 });
  await expect(save).toBeDisabled({ timeout: 30_000 });
}

async function keyboardFocusesServiceButton(page: Page): Promise<void> {
  await page.locator('body').click({ position: { x: 1, y: 1 } });
  await page.evaluate(() =>
    (document.activeElement as HTMLElement | null)?.blur(),
  );
  let focused = false;
  for (let step = 0; step < 100; step += 1) {
    await page.keyboard.press('Tab');
    focused = await page.evaluate(
      () =>
        document.activeElement?.matches(
          '.gama-service-card .wp-block-button__link',
        ) ?? false,
    );
    if (focused) break;
  }
  expect(focused, 'Keyboard could not reach the editable service link.').toBe(
    true,
  );
  const focus = await page.evaluate(() => {
    const element = document.activeElement as HTMLElement;
    const style = getComputedStyle(element);

    return {
      outlineColor: style.outlineColor,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      outlineOffset: style.outlineOffset,
    };
  });
  expect(focus.outlineStyle).toBe('solid');
  expect(Number.parseFloat(focus.outlineWidth)).toBeGreaterThanOrEqual(3);
  expect(Number.parseFloat(focus.outlineOffset)).toBeGreaterThanOrEqual(3);
  expect(focus.outlineColor).toBe('rgb(21, 93, 252)');
}

test('renders the baseline services section as responsive accessible cards @services', async ({
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

    const section = page.locator('main section#services.gama-services');
    await expect(section).toHaveCount(1);
    await expect(
      section.getByRole('heading', { level: 2, name: 'Nasze Usługi' }),
    ).toHaveCount(1);

    const cards = section.locator('.gama-service-card');
    await expect(cards).toHaveCount(services.length);
    for (const [title, description] of services) {
      await expect(
        cards.getByRole('heading', { level: 3, name: title }),
      ).toHaveCount(1);
      await expect(cards.getByText(description, { exact: true })).toHaveCount(1);
    }

    const cardRows = await cards.evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return { left: Math.round(rect.left), top: Math.round(rect.top) };
      }),
    );
    const firstRowTop = Math.min(...cardRows.map(({ top }) => top));
    expect(
      cardRows.filter(({ top }) => Math.abs(top - firstRowTop) <= 1),
    ).toHaveLength(expectedColumns);

    const sectionBounds = await section.evaluate((element) => {
      const { left, right } = element.getBoundingClientRect();

      return { left: Math.round(left), right: Math.round(right) };
    });
    expect(sectionBounds.left).toBe(0);
    expect(sectionBounds.right).toBe(width);

    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(hasOverflow).toBe(false);
  }
});

test('lets a scoped Editor add, remove, reorder and edit service cards without code @services', async ({
  page,
}) => {
  await login(page, 'theme-navigation-editor', 'navigation-editor-test-only');
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['editor']);
  expect(currentUser.capabilities.edit_theme_options).toBe(true);
  expect(currentUser.capabilities.activate_plugins ?? false).toBe(false);

  const frame = await openFrontPageTemplate(page);
  await expect(
    frame.locator('[data-type="core/group"].gama-service-card'),
  ).toHaveCount(3);

  const serviceTitleBlock = frame
    .locator('[data-type="core/heading"]')
    .filter({ hasText: services[0][0] });
  await expect(serviceTitleBlock).toHaveCount(1);
  await serviceTitleBlock.scrollIntoViewIfNeeded();
  await serviceTitleBlock.click();
  const editableTitle = frame
    .locator('[data-type="core/heading"][contenteditable="true"]')
    .filter({ hasText: services[0][0] });
  await expect(editableTitle).toHaveCount(1);
  await editableTitle.fill(longServiceTitle);

  const serviceDescriptionBlock = frame
    .locator('[data-type="core/paragraph"]')
    .filter({ hasText: services[0][1] });
  await expect(serviceDescriptionBlock).toHaveCount(1);
  await serviceDescriptionBlock.click();
  const editableDescription = frame
    .locator('[data-type="core/paragraph"][contenteditable="true"]')
    .filter({ hasText: services[0][1] });
  await expect(editableDescription).toHaveCount(1);
  await editableDescription.fill(updatedServiceDescription);

  const mutation = await page.evaluate(
    ({ movedTitle }) => {
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
      const grid = () => {
        const block = findByClassName(
          select.getBlocks(),
          'gama-services__grid',
        );
        if (block === undefined) {
          throw new Error('The editable Services Grid block was not found.');
        }

        return block;
      };
      const cards = () =>
        grid().innerBlocks.filter(
          (block: any) => block.attributes?.className === 'gama-service-card',
        );
      const counts: number[] = [];
      const initialCards = cards();
      if (initialCards.length !== 3) {
        throw new Error(`Expected three baseline cards, received ${initialCards.length}.`);
      }

      dispatch.removeBlocks(
        initialCards.slice(1).map((block: any) => block.clientId),
        false,
      );
      counts.push(cards().length);

      for (const targetCount of [3, 6]) {
        while (cards().length < targetCount) {
          const countBeforeDuplicate = cards().length;
          dispatch.duplicateBlocks(
            [cards()[0].clientId],
            false,
          );
          if (cards().length !== countBeforeDuplicate + 1) {
            throw new Error('Core Block Editor did not duplicate the service card.');
          }
        }
        counts.push(cards().length);
      }

      const lastCard = cards().at(-1);
      const lastTitle = lastCard?.innerBlocks.find(
        (block: any) => block.name === 'core/heading',
      );
      if (lastCard === undefined || lastTitle === undefined) {
        throw new Error('The duplicated service card is missing its editable title.');
      }
      dispatch.updateBlockAttributes(lastTitle.clientId, { content: movedTitle });
      dispatch.moveBlockToPosition(
        lastCard.clientId,
        grid().clientId,
        grid().clientId,
        0,
      );

      return {
        counts,
        firstCardClientId: cards()[0].clientId,
        firstTitle: cards()[0].innerBlocks.find(
          (block: any) => block.name === 'core/heading',
        )?.attributes?.content,
        finalCount: cards().length,
      };
    },
    { movedTitle: movedServiceTitle },
  );
  expect(mutation.counts).toEqual([1, 3, 6]);
  expect(mutation.finalCount).toBe(6);
  expect(mutation.firstTitle).toBe(movedServiceTitle);
  await expect(
    frame.locator('[data-type="core/group"].gama-service-card'),
  ).toHaveCount(6);
  await expect(
    frame
      .locator('[data-type="core/heading"]')
      .filter({ hasText: movedServiceTitle }),
  ).toBeVisible();

  await page.waitForFunction((cardClientId) => {
    const wordpress = (window as typeof window & { wp: any }).wp;

    return wordpress.data
      .select('core/block-editor')
      .canInsertBlockType('core/buttons', cardClientId);
  }, mutation.firstCardClientId);

  const optionalLink = await page.evaluate(
    ({ cardClientId, buttonLabel }) => {
      const wordpress = (window as typeof window & { wp: any }).wp;
      const select = wordpress.data.select('core/block-editor');
      const dispatch = wordpress.data.dispatch('core/block-editor');
      if (!select.canInsertBlockType('core/buttons', cardClientId)) {
        throw new Error('The rendered service card does not accept an optional Core Button.');
      }

      const button = wordpress.blocks.createBlock('core/button', {
        text: buttonLabel,
        url: '/#services',
      });
      const buttons = wordpress.blocks.createBlock('core/buttons', {}, [button]);
      dispatch.insertBlock(buttons, undefined, cardClientId, false);

      return select
        .getBlocks(cardClientId)
        .filter((block: any) => block.name === 'core/buttons').length;
    },
    { cardClientId: mutation.firstCardClientId, buttonLabel: serviceButton },
  );
  expect(optionalLink).toBe(1);
  const movedServiceCard = frame
    .locator('[data-type="core/group"].gama-service-card')
    .filter({ hasText: movedServiceTitle });
  await expect(movedServiceCard.locator('[data-type="core/buttons"]')).toHaveCount(
    1,
  );

  await saveFrontPageTemplate(page);
  const frontPage = await rest<any>(
    page,
    '/wp/v2/templates/gama-software//front-page?context=edit',
  );
  expect(frontPage.source).toBe('custom');
  expect(frontPage.has_theme_file).toBe(true);
  expect(frontPage.content.raw).toContain(longServiceTitle);
  expect(frontPage.content.raw).toContain(updatedServiceDescription);
  expect(frontPage.content.raw).toContain(movedServiceTitle);
  expect(frontPage.content.raw).toContain(serviceButton);
  const savedServiceCardCount = await page.evaluate((templateContent) => {
    const wordpress = (window as typeof window & { wp: any }).wp;
    const countCards = (blocks: any[]): number =>
      blocks.reduce(
        (count, block) =>
          count +
          (block.attributes?.className === 'gama-service-card' ? 1 : 0) +
          countCards(block.innerBlocks ?? []),
        0,
      );

    return countCards(wordpress.blocks.parse(templateContent));
  }, frontPage.content.raw);
  expect(savedServiceCardCount).toBe(6);

  for (const [width, expectedColumns] of [
    [320, 1],
    [768, 2],
    [1440, 3],
  ] as const) {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);

    const section = servicesSection(page);
    const cards = section.locator('.gama-service-card');
    await expect(cards).toHaveCount(6);
    await expect(
      section.getByRole('heading', { level: 3, name: movedServiceTitle }),
    ).toBeVisible();
    await expect(
      section.getByRole('link', { name: serviceButton }),
    ).toHaveAttribute('href', '/#services');
    await expect(section.locator('.gama-service-card img[alt=""]')).toHaveCount(6);

    const cardRows = await cards.evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          height: Math.round(rect.height),
          left: Math.round(rect.left),
          top: Math.round(rect.top),
        };
      }),
    );
    const firstRowTop = Math.min(...cardRows.map(({ top }) => top));
    expect(
      cardRows.filter(({ top }) => Math.abs(top - firstRowTop) <= 1),
    ).toHaveLength(expectedColumns);
    for (const rowTop of [...new Set(cardRows.map(({ top }) => top))]) {
      const rowHeights = cardRows
        .filter(({ top }) => Math.abs(top - rowTop) <= 1)
        .map(({ height }) => height);
      expect(Math.max(...rowHeights) - Math.min(...rowHeights)).toBeLessThanOrEqual(
        1,
      );
    }

    const titleOverflow = await section.locator('h3').evaluateAll((elements) =>
      elements.map((element) => {
        const htmlElement = element as HTMLElement;

        return htmlElement.scrollWidth > htmlElement.clientWidth + 1;
      }),
    );
    expect(titleOverflow).toEqual(Array(6).fill(false));
    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(hasOverflow).toBe(false);
  }

  await keyboardFocusesServiceButton(page);
});
