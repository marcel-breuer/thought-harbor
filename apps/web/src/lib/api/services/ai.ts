import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type OpenRouterModelList = components['schemas']['OpenRouterModelListResponse'];

export async function getOpenRouterModels(signal?: AbortSignal): Promise<OpenRouterModelList> {
  const result = await apiClient.GET('/api/v1/ai/models', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
