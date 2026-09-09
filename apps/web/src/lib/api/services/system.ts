import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

type HealthResponse = components['schemas']['HealthResponse'];

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const result = await apiClient.GET('/api/v1/health', { signal });

  if (result.error) {
    throw normalizeApiError(result.error, result.response);
  }

  return result.data;
}
