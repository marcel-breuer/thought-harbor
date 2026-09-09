import type { components } from '$lib/generated/api';

type HealthResponse = components['schemas']['HealthResponse'];

export interface SystemApi {
  getHealth(signal?: AbortSignal): Promise<HealthResponse>;
}

export function createFakeSystemApi(response: HealthResponse = { status: 'ok' }): SystemApi {
  return {
    async getHealth(signal?: AbortSignal) {
      if (signal?.aborted) {
        throw new DOMException('The request was aborted.', 'AbortError');
      }
      return response;
    },
  };
}
