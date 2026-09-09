import { expect, test } from '@playwright/test';

test('loads the ThoughtHarbor workspace', async ({ page }) => {
  await page.route('**/api/v1/inbox**', async (route) => {
    await route.fulfill({
      json: {
        items: [],
        page: { page: 1, page_size: 100, total: 0, total_pages: 0 }
      }
    });
  });

  await page.goto('/');
  await expect(page).toHaveTitle('Inbox · ThoughtHarbor');
  await expect(page.getByRole('heading', { name: 'Your private inbox.' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Add knowledge' })).toBeVisible();
});
