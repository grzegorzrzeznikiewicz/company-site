import { expect, test } from '@playwright/test';
import {
  login,
  openEditorCanvas,
  rest,
  waitForEditorCanvas,
} from './support/wordpress';

test('@release-acceptance-editor edits content and stays inside the Editor boundary', async ({
  page,
}) => {
  await login(
    page,
    process.env.WP_EDITOR_USER ?? 'theme-navigation-editor',
    process.env.WP_EDITOR_PASSWORD ?? 'navigation-editor-test-only',
  );
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['editor']);
  expect(currentUser.capabilities.activate_plugins ?? false).toBe(false);
  expect(currentUser.capabilities.install_plugins ?? false).toBe(false);
  expect(currentUser.capabilities.manage_options ?? false).toBe(false);
  expect(currentUser.capabilities.create_users ?? false).toBe(false);
  expect(currentUser.capabilities.promote_users ?? false).toBe(false);
  expect(currentUser.capabilities.update_core ?? false).toBe(false);

  for (const route of [
    '/wp-admin/plugins.php',
    '/wp-admin/user-new.php',
    '/wp-admin/options-general.php',
  ]) {
    const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(403);
  }

  const frontPageId = encodeURIComponent('gama-software//front-page');
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${frontPageId}&postType=wp_template&canvas=edit`,
  );
  await expect(frame.locator('main.gama-template--front-page')).toBeVisible();

  const frontPageRecordId = 'gama-software//front-page';
  const savedContact = await page.evaluate(async (recordId) => {
    const wordpress = (window as typeof window & { wp: any }).wp;
    const record = await wordpress.data
      .resolveSelect('core')
      .getEntityRecord('postType', 'wp_template', recordId);
    const original = record.content.raw as string;
    const changed = original.replace(
      '>Kontakt</h2>',
      '>Kontakt próby stagingu</h2>',
    );
    if (changed === original) {
      throw new Error('The contact section did not expose its editable heading.');
    }
    wordpress.data
      .dispatch('core')
      .editEntityRecord('postType', 'wp_template', recordId, {
        content: changed,
      });
    const saved = await wordpress.data
      .dispatch('core')
      .saveEditedEntityRecord('postType', 'wp_template', recordId);
    return { original, saved: saved.content.raw as string };
  }, frontPageRecordId);
  expect(savedContact.saved).toContain('Kontakt próby stagingu');
  await page.goto('/#contact', { waitUntil: 'domcontentloaded' });
  await expect(
    page.getByRole('heading', {
      level: 2,
      name: 'Kontakt próby stagingu',
      exact: true,
    }),
  ).toBeVisible();
  const restoredFrontPage = await rest<any>(
    page,
    '/wp/v2/templates/gama-software//front-page',
    'POST',
    { content: savedContact.original },
  );
  expect(restoredFrontPage.content.raw).toContain('>Kontakt</h2>');

  const headerRecordId = 'gama-software//header';
  const headerFrame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(headerRecordId)}&postType=wp_template_part&canvas=edit`,
  );
  await expect(headerFrame.getByText('Start', { exact: true })).toBeVisible();
  const savedHeader = await page.evaluate(async (recordId) => {
    const wordpress = (window as typeof window & { wp: any }).wp;
    const record = await wordpress.data
      .resolveSelect('core')
      .getEntityRecord('postType', 'wp_template_part', recordId);
    const original = record.content.raw as string;
    const changed = original.replace(
      '"label":"Start"',
      '"label":"Start próby stagingu"',
    );
    if (changed === original) {
      throw new Error('The header did not expose the expected editable menu link.');
    }
    wordpress.data.dispatch('core').editEntityRecord(
      'postType',
      'wp_template_part',
      recordId,
      { content: changed },
    );
    const saved = await wordpress.data
      .dispatch('core')
      .saveEditedEntityRecord('postType', 'wp_template_part', recordId);
    return { original, saved: saved.content.raw as string };
  }, headerRecordId);
  expect(savedHeader.saved).toContain('"label":"Start próby stagingu"');
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(
    page.getByRole('link', { name: 'Start próby stagingu', exact: true }),
  ).toHaveAttribute('href', '/#home');
  const restoredHeader = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//header',
    'POST',
    { content: savedHeader.original },
  );
  expect(restoredHeader.content.raw).toContain('"label":"Start"');

  const footerRecordId = 'gama-software//footer';
  const footerFrame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(footerRecordId)}&postType=wp_template_part&canvas=edit`,
  );
  await expect(
    footerFrame.getByText('© 2026 Gama Software. Wszystkie prawa zastrzeżone.', {
      exact: true,
    }),
  ).toBeVisible();
  const savedFooter = await page.evaluate(async (recordId) => {
    const wordpress = (window as typeof window & { wp: any }).wp;
    const record = await wordpress.data
      .resolveSelect('core')
      .getEntityRecord('postType', 'wp_template_part', recordId);
    const original = record.content.raw as string;
    const changed = original.replace(
      '© 2026 Gama Software. Wszystkie prawa zastrzeżone.',
      '© 2026 Gama Software. Stopka próby stagingu.',
    );
    if (changed === original) {
      throw new Error('The footer did not expose its editable copyright copy.');
    }
    wordpress.data
      .dispatch('core')
      .editEntityRecord('postType', 'wp_template_part', recordId, {
        content: changed,
      });
    const saved = await wordpress.data
      .dispatch('core')
      .saveEditedEntityRecord('postType', 'wp_template_part', recordId);
    return { original, saved: saved.content.raw as string };
  }, footerRecordId);
  expect(savedFooter.saved).toContain('Stopka próby stagingu');
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(
    page.getByText('© 2026 Gama Software. Stopka próby stagingu.', {
      exact: true,
    }),
  ).toBeVisible();
  const restoredFooter = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//footer',
    'POST',
    { content: savedFooter.original },
  );
  expect(restoredFooter.content.raw).toContain(
    '© 2026 Gama Software. Wszystkie prawa zastrzeżone.',
  );

  await page.goto('/wp-admin/post-new.php', { waitUntil: 'domcontentloaded' });
  await waitForEditorCanvas(page);
  const post = await page.evaluate(async () => {
    const wordpress = (window as typeof window & { wp: any }).wp;
    const content = wordpress.blocks.serialize([
      wordpress.blocks.createBlock('core/paragraph', {
        content: 'Treść opublikowana w próbie GSWEB-28.',
      }),
    ]);
    wordpress.data.dispatch('core/editor').editPost({
      title: 'GSWEB-28 próba redaktora',
      content,
      status: 'publish',
    });
    await wordpress.data.dispatch('core/editor').savePost();
    const record = wordpress.data.select('core/editor').getCurrentPost();
    return { id: record.id, link: record.link, status: record.status };
  });
  expect(post.id).toBeGreaterThan(0);
  expect(post.status).toBe('publish');
  const published = await rest<any>(
    page,
    `/wp/v2/posts/${post.id}?context=edit`,
  );
  expect(published.title.raw).toBe('GSWEB-28 próba redaktora');
  expect(published.content.raw).toContain(
    'Treść opublikowana w próbie GSWEB-28.',
  );
  const publicPost = await page.request.get(post.link);
  expect(publicPost.status()).toBe(200);

  const withdrawn = await rest<any>(page, `/wp/v2/posts/${post.id}`, 'POST', {
    status: 'draft',
  });
  expect(withdrawn.status).toBe('draft');

  const media = await page.evaluate(async () => {
    const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
      credentials: 'same-origin',
    }).then((response) => response.text());
    const bytes = Uint8Array.from(
      atob(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
      ),
      (character) => character.charCodeAt(0),
    );
    const response = await fetch('/index.php?rest_route=/wp/v2/media', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Disposition': 'attachment; filename="gsweb-28-acceptance.png"',
        'Content-Type': 'image/png',
        'X-WP-Nonce': nonce,
      },
      body: bytes,
    });
    if (!response.ok) {
      throw new Error(`Media upload failed: ${response.status}`);
    }
    return response.json();
  });
  expect(media.id).toBeGreaterThan(0);
  const mediaWithAlt = await rest<any>(
    page,
    `/wp/v2/media/${media.id}`,
    'POST',
    { alt_text: 'Piksel testowy próby migracji GSWEB-28' },
  );
  expect(mediaWithAlt.alt_text).toBe('Piksel testowy próby migracji GSWEB-28');

  await rest(page, `/wp/v2/media/${media.id}?force=true`, 'DELETE');
  await rest(page, `/wp/v2/posts/${post.id}?force=true`, 'DELETE');
});

test('@release-acceptance-admin manages users and verifies the deployed extensions', async ({
  page,
}) => {
  await login(page);
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['administrator']);
  expect(currentUser.capabilities.manage_options).toBe(true);
  expect(currentUser.capabilities.create_users).toBe(true);
  expect(currentUser.capabilities.promote_users).toBe(true);

  for (const [route, bodyClass] of [
    ['/wp-admin/users.php', 'users-php'],
    ['/wp-admin/plugins.php', 'plugins-php'],
    ['/wp-admin/site-health.php', 'site-health'],
  ] as const) {
    const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);
    await expect(page.locator('body')).toHaveClass(new RegExp(bodyClass));
  }
  const installResponse = await page.goto('/wp-admin/plugin-install.php', {
    waitUntil: 'domcontentloaded',
  });
  expect(installResponse?.status()).toBe(403);

  const plugins = await rest<any[]>(page, '/wp/v2/plugins?context=edit');
  const statuses = Object.fromEntries(
    plugins.map(({ plugin, status }) => [plugin, status]),
  );
  expect(statuses).toMatchObject({
    'gama-contact/gama-contact': 'active',
    'gama-local-mailpit/gama-local-mailpit': 'active',
    'gama-security/gama-security': 'active',
    'gama-seo/gama-seo': 'active',
  });

  const marker = Date.now();
  const createdUser = await rest<any>(page, '/wp/v2/users', 'POST', {
    username: `gsweb28-editor-${marker}`,
    email: `gsweb28-editor-${marker}@example.test`,
    password: `GSWEB28-test-only-${marker}`,
    roles: ['editor'],
  });
  expect(createdUser.roles).toEqual(['editor']);
  const deletedUser = await rest<any>(
    page,
    `/wp/v2/users/${createdUser.id}?force=true&reassign=${currentUser.id}`,
    'DELETE',
  );
  expect(deletedUser.deleted).toBe(true);
});
