export async function performContactJourney(page, adapter) {
  if (adapter === 'react') {
    const direct = page.getByRole('button', { name: 'Kontakt', exact: true }).filter({ visible: true });
    if (await direct.count()) {
      await direct.first().click();
    } else {
      await page.getByRole('button', { name: 'Otwórz menu nawigacyjne' }).click();
      await page.getByRole('button', { name: 'Kontakt', exact: true }).filter({ visible: true }).click();
    }
  } else if (adapter === 'wordpress') {
    const direct = page.getByRole('link', { name: 'Kontakt', exact: true }).filter({ visible: true });
    if (await direct.count()) {
      await direct.first().click();
    } else {
      await page.locator('.wp-block-navigation__responsive-container-open').click();
      await page.getByRole('link', { name: 'Kontakt', exact: true }).filter({ visible: true }).click();
    }
  } else {
    throw new Error(`Unknown contact journey adapter: ${adapter}`);
  }

  const values = {
    name: 'Gama CWV Test',
    email: 'cwv@example.test',
    phone: '+48123456789',
    message: 'Local diagnostic journey only',
  };
  for (const [name, value] of Object.entries(values)) {
    const field = page.locator(`[name="${name}"]`);
    await field.click();
    await field.pressSequentially(value);
  }
  return {
    formSubmitted: await page.evaluate(() => globalThis.__gamaFormSubmitted === true),
  };
}

export async function performReadingJourney(page) {
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  return { formSubmitted: false };
}
