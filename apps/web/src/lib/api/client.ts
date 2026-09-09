import createClient from 'openapi-fetch';
import type { Middleware } from 'openapi-fetch';

import type { paths } from '$lib/generated/api';

export const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

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
