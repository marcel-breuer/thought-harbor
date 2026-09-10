import { expect, test } from '@playwright/test';

test('loads the ThoughtHarbor workspace', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      json: { id: 1, email: 'marcel@example.com', username: null, display_name: 'Marcel', role: 'admin' }
    });
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

  await page.goto('/');
  await expect(page).toHaveTitle('Dashboard · ThoughtHarbor');
  await expect(page.getByRole('heading', { name: 'Good morning, Marcel.' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recent sources' })).toBeVisible();
});
