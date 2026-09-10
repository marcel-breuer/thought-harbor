import { expect, test } from '@playwright/test';

const pageMeta = { page: 1, page_size: 100, total: 1, total_pages: 1 };

test('walks the source, review, knowledge, and grounded chat journey', async ({ page }) => {
  let uploaded = false;

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({ json: { id: 1, email: 'marcel@example.com', username: null, display_name: 'Marcel', role: 'admin' } });
  });

  await page.route('**/api/v1/inbox**', async (route) => {
    if (route.request().method() === 'POST') {
      uploaded = true;
      await route.fulfill({
        status: 201,
        json: {
          id: 10,
          original_name: 'notes.txt',
          media_type: 'text/plain',
          byte_size: 24,
          sha256: 'a'.repeat(64),
          source_type: 'transcript',
          ingestion_status: 'ready',
          status_timeline: [],
          progress: 1,
          error_message: null,
          created_at: '2026-01-01T12:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          document_id: 20,
          meeting_id: null
        }
      });
      return;
    }
    await route.fulfill({
      json: {
        items: uploaded ? [{
          id: 10,
          original_name: 'notes.txt',
          media_type: 'text/plain',
          byte_size: 24,
          sha256: 'a'.repeat(64),
          source_type: 'transcript',
          ingestion_status: 'ready',
          status_timeline: [{ status: 'ready', at: '2026-01-01T12:00:00Z' }],
          progress: 1,
          error_message: null,
          created_at: '2026-01-01T12:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          document_id: 20,
          meeting_id: null
        }] : [],
        page: { page: 1, page_size: 100, total: uploaded ? 1 : 0, total_pages: uploaded ? 1 : 0 }
      }
    });
  });

  await page.goto('/inbox');
  await page.locator('input[type="file"]').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('A decision for Project Aurora.') });
  await expect(page.getByText('notes.txt')).toBeVisible();
  await expect(page.getByText('ready')).toBeVisible();

  await page.route('**/api/v1/clarifications**', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: { id: 30, status: 'resolved' } });
      return;
    }
    await route.fulfill({ json: { items: [{ id: 30, question: 'Where should this decision live?', status: 'open', classification_id: 40, label: 'Project Aurora', confidence: 0.61, source_text: 'A decision for Project Aurora.', source_location: { section: 1 }, options: [{ id: 7, title: 'Project Aurora', kind: 'project' }], selected_knowledge_object_ids: [], created_at: '2026-01-01T12:00:00Z', resolved_at: null }], page: pageMeta } });
  });
  await page.goto('/clarifications');
  await expect(page.getByRole('heading', { name: 'Where should this decision live?' })).toBeVisible();
  await page.getByRole('button', { name: 'Accept selection' }).click();
  await expect(page.getByText('Nothing needs your input.')).toBeVisible();

  await page.route('**/api/v1/knowledge/objects*', async (route) => {
    if (route.request().url().includes('/7')) {
      await route.fulfill({ json: { item: { id: 7, kind: 'project', title: 'Project Aurora', description: 'A focused project.', metadata: {} }, related: [], artifacts: [{ id: 50, kind: 'decision', title: 'Decision', content: 'Keep the source grounded.', sources: [{ chunk_id: 1, text: 'A decision for Project Aurora.', location: { section: 1 }, source_offset_start: 0, source_offset_end: 31, source_start_ms: null, source_end_ms: null }] }] } });
      return;
    }
    await route.fulfill({ json: { items: [{ id: 7, kind: 'project', title: 'Project Aurora', description: 'A focused project.', metadata: {} }], page: pageMeta } });
  });
  await page.goto('/knowledge');
  await page.getByRole('button', { name: /Project Aurora/ }).click();
  await expect(page.getByText('Keep the source grounded.')).toBeVisible();

  await page.route('**/api/v1/chat', async (route) => {
    await route.fulfill({ json: { conversation_id: 1, message_id: 2, answer: 'The decision is tied to Project Aurora.', evidence_sufficient: true, citations: [{ marker: '[S1]', chunk_id: 1, source_file_id: 10, source_type: 'transcript', source_title: 'notes', excerpt: 'A decision for Project Aurora.', location: { section: 1 }, source_offset_start: 0, source_offset_end: 31, source_start_ms: null, source_end_ms: null }] } });
  });
  await page.goto('/chat');
  await page.getByLabel('Question').fill('Where does the decision belong?');
  await page.getByRole('button', { name: 'Ask question' }).click();
  await expect(page.getByText('The decision is tied to Project Aurora.')).toBeVisible();
  await expect(page.getByText('[S1] · notes')).toBeVisible();
});
