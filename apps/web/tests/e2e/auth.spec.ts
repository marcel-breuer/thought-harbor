import { expect, test } from '@playwright/test';

test('shows the local first-user bootstrap form', async ({ page }) => {
  await page.route('**/api/v1/auth/status', async (route) => {
    await route.fulfill({ json: { setup_required: true } });
  });

  await page.goto('/login');

  await expect(page.getByRole('heading', { name: 'Create your local account.' })).toBeVisible();
  await expect(page.getByLabel('Password')).toHaveAttribute('minlength', '12');
  await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
});
