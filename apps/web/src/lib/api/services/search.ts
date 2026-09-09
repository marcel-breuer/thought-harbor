import type { components, paths } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type SearchResult = components['schemas']['SearchResultResponse'];
export type SearchQuery = paths['/api/v1/search']['get']['parameters']['query'];

export async function searchKnowledge(
  query: SearchQuery,
  signal?: AbortSignal
): Promise<components['schemas']['SearchListResponse']> {
  const result = await apiClient.GET('/api/v1/search', {
    params: { query },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
