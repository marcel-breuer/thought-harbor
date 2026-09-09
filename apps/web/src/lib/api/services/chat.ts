import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type ChatResponse = components['schemas']['ChatResponse'];
export type ChatRequestBody = components['schemas']['ChatRequestBody'];

export async function askKnowledge(
  body: ChatRequestBody,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const result = await apiClient.POST('/api/v1/chat', { body, signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
