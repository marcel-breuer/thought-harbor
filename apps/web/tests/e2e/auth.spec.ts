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
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ json: { id: 1, email: 'marcel@example.com', username: null, display_name: 'Marcel', role: 'admin' } });
  });
  await page.route('**/api/v1/dashboard', async (route) => {
    await route.fulfill({ json: { recent_sources: [], processing_attention: [], pending_clarifications: [], open_tasks: [], open_questions: [], recent_decisions: [], active_topics: [], insights: [] } });
  });

  await page.goto('/login');
  await page.getByLabel('Email').fill('marcel@example.com');
  await page.getByLabel('Display name').fill('Marcel');
  await page.getByLabel('Password').fill('correct-horse-battery-staple');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL('/');
  await expect(page).toHaveTitle('Dashboard · ThoughtHarbor');
});

test('redirects unauthenticated users to login', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ status: 401, json: { code: 'AUTH_REQUIRED', message: 'Authentication required.' } });
  });
  await page.route('**/api/v1/auth/status', async (route) => {
    await route.fulfill({ json: { setup_required: false } });
  });

  await page.goto('/chat');

  await expect(page).toHaveURL('/login?redirect=%2Fchat');
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
});
