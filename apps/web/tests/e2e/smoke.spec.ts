import { expect, test } from '@playwright/test';

test('loads the ThoughtHarbor workspace', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('ThoughtHarbor');
  await expect(page.getByRole('heading', { name: 'Your knowledge, privately yours.' })).toBeVisible();
});
