import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type ApiToken = components['schemas']['ApiTokenResponse'];
export type ApiTokenCreateRequest = components['schemas']['ApiTokenCreateRequest'];

export async function listApiTokens(signal?: AbortSignal): Promise<ApiToken[]> {
  const result = await apiClient.GET('/api/v1/auth/tokens', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data.items;
}

export async function createApiToken(body: ApiTokenCreateRequest): Promise<ApiToken> {
  const result = await apiClient.POST('/api/v1/auth/tokens', { body });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function revokeApiToken(id: number): Promise<void> {
  const result = await apiClient.DELETE('/api/v1/auth/tokens/{token_id}', {
    params: { path: { token_id: id } }
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
}
