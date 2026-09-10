import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

type HealthResponse = components['schemas']['HealthResponse'];
export type ReadinessResponse = components['schemas']['ReadinessResponse'];
export type RuntimeSettings = components['schemas']['RuntimeSettingsResponse'];

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const result = await apiClient.GET('/api/v1/health', { signal });

  if (result.error) {
    throw normalizeApiError(result.error, result.response);
  }

  return result.data;
}

export async function getDiagnostics(signal?: AbortSignal): Promise<ReadinessResponse> {
  const result = await apiClient.GET('/api/v1/settings/diagnostics', { signal });

  if (result.error) {
    throw normalizeApiError(result.error, result.response);
  }

  return result.data;
}

export async function getRuntimeSettings(signal?: AbortSignal): Promise<RuntimeSettings> {
  const result = await apiClient.GET('/api/v1/settings/configuration', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
