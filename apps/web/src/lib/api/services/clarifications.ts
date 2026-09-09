import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type Clarification = components['schemas']['ClarificationResponse'];
export type ClarificationResolutionRequest = components['schemas']['ClarificationResolutionRequest'];

export async function listClarifications(signal?: AbortSignal): Promise<components['schemas']['ClarificationListResponse']> {
  const result = await apiClient.GET('/api/v1/clarifications', {
    params: { query: { page: 1, page_size: 100 } },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function resolveClarification(
  id: number,
  body: ClarificationResolutionRequest
): Promise<Clarification> {
  const result = await apiClient.POST('/api/v1/clarifications/{clarification_id}/resolve', {
    params: { path: { clarification_id: id } },
    body
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
