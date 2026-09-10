import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type Dashboard = components['schemas']['DashboardResponse'];

export async function getDashboard(signal?: AbortSignal): Promise<Dashboard> {
  // openapi-fetch currently resolves this no-parameter operation to `never`;
  // keep the generated client as the transport and narrow its response here.
  const result = (await apiClient.GET('/api/v1/dashboard', { signal })) as {
    data?: Dashboard;
    error?: unknown;
    response: Response;
  };
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data as Dashboard;
}
