import { expect, test } from '@playwright/test';

const emptyActionKnowledge = {
  items: [],
  page: { page: 1, page_size: 100, total: 0, total_pages: 0 },
  summary: { open_tasks: 0, recent_decisions: 0, open_questions: 0 }
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ json: { id: 1, email: 'marcel@example.com', username: null, display_name: 'Marcel', role: 'admin' } });
  });
  await page.route('**/api/v1/dashboard', async (route) => {
    await route.fulfill({
      json: {
        recent_sources: [],
        processing_attention: [],
        pending_clarifications: [],
        open_tasks: [],
        open_questions: [],
        recent_decisions: [],
        active_topics: [],
        insights: []
      }
    });
  });
  await page.route('**/api/v1/inbox**', async (route) => {
    await route.fulfill({
      json: {
        items: [],
        page: { page: 1, page_size: 100, total: 0, total_pages: 0 }
      }
    });
  });
  await page.route('**/api/v1/knowledge/action-items**', async (route) => {
    await route.fulfill({ json: emptyActionKnowledge });
  });
  await page.route('**/api/v1/knowledge/objects**', async (route) => {
    await route.fulfill({
      json: { items: [], page: { page: 1, page_size: 100, total: 0, total_pages: 0 } }
    });
  });
});

test('opens the command palette with the keyboard and navigates', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Control+K');

  const dialog = page.getByRole('dialog', { name: 'Command palette' });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Command search').fill('Tasks');
  await dialog.getByRole('button', { name: 'Tasks' }).click();

  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.getByRole('heading', { name: 'Action knowledge' })).toBeVisible();
});

test('opens the mobile navigation and keeps touch targets usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open navigation' }).click();

  const navigation = page.getByRole('navigation', { name: 'Mobile primary navigation' });
  await expect(navigation).toBeVisible();
  await expect(navigation.getByRole('link', { name: 'Tasks' })).toBeVisible();
  await navigation.getByRole('link', { name: 'Tasks' }).click();
  await expect(page).toHaveURL(/\/tasks$/);
});

test('opens the source overviews from the primary navigation', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Documents' }).click();
  await expect(page).toHaveURL(/\/documents$/);
  await expect(page.getByRole('heading', { name: 'No documents yet.' })).toBeVisible();

  await page.getByRole('link', { name: 'Meetings' }).click();
  await expect(page).toHaveURL(/\/meetings$/);
  await expect(page.getByRole('heading', { name: 'No meetings yet.' })).toBeVisible();
});
