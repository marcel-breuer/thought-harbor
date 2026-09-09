import createClient from 'openapi-fetch';

import type { paths } from '$lib/generated/api';

const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const apiClient = createClient<paths>({ baseUrl: apiBaseUrl });
