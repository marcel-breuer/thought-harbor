import createClient from 'openapi-fetch';
import type { Middleware } from 'openapi-fetch';

import type { paths } from '$lib/generated/api';

const configuredApiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

// Generated OpenAPI paths already include /api/v1, so the fetch client must
// receive the API origin rather than the versioned path as its base URL.
export function normalizeApiBaseUrl(value: string): string {
  return value
    .replace(/\/+$/, '')
    .replace(/\/api\/v1$/, '');
}

export const apiBaseUrl = normalizeApiBaseUrl(configuredApiBaseUrl);

const authExpiryMiddleware: Middleware = {
  onResponse: async ({ response }) => {
    if (response.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('thought-harbor:auth-expired'));
    }
    return response;
  },
};

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  credentials: 'include',
});

apiClient.use(authExpiryMiddleware);
