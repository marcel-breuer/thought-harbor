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

test('submits the bootstrap form and shows the local account', async ({ page }) => {
  await page.route('**/api/v1/auth/status', async (route) => {
    await route.fulfill({ json: { setup_required: true } });
  });
  await page.route('**/api/v1/auth/bootstrap', async (route) => {
    await route.fulfill({ status: 201, json: { user: { id: 1, email: 'marcel@example.com', username: null, display_name: 'Marcel', role: 'admin' } } });
  });

  await page.goto('/login');
  await page.getByLabel('Email').fill('marcel@example.com');
  await page.getByLabel('Display name').fill('Marcel');
  await page.getByLabel('Password').fill('correct-horse-battery-staple');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await expect(page.getByText('Signed in as marcel@example.com')).toBeVisible();
});
