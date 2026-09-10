import type { components } from '$lib/generated/api';

import { apiBaseUrl, apiClient } from '$lib/api/client';
import { ApiClientError, normalizeApiError } from '$lib/api/errors';

export type InboxItem = components['schemas']['InboxItemResponse'];
export type InboxList = components['schemas']['InboxListResponse'];
export type IngestionStatus = InboxItem['ingestion_status'];
export type SourceType = InboxItem['source_type'];

export async function listInbox(
  options: {
    page?: number;
    page_size?: number;
    status?: IngestionStatus;
    source_type?: SourceType;
    signal?: AbortSignal;
  } = {}
): Promise<InboxList> {
  const result = await apiClient.GET('/api/v1/inbox', {
    params: {
      query: {
        page: options.page ?? 1,
        page_size: options.page_size ?? 100,
        status: options.status,
        source_type: options.source_type
      }
    },
    signal: options.signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function getInboxItem(id: number, signal?: AbortSignal): Promise<InboxItem> {
  const result = await apiClient.GET('/api/v1/inbox/{source_file_id}', {
    params: { path: { source_file_id: id } },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function retryInboxItem(id: number): Promise<InboxItem> {
  const result = await apiClient.POST('/api/v1/inbox/{source_file_id}/retry', {
    params: { path: { source_file_id: id } }
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export function uploadInboxFile(
  file: File,
  onProgress: (percent: number) => void,
  signal?: AbortSignal
): Promise<InboxItem> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const form = new FormData();
    form.append('file', file, file.name);
    request.open('POST', `${apiBaseUrl}/api/v1/inbox/upload`);
    request.withCredentials = true;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onload = () => {
      let body: unknown;
      try {
        body = request.responseText ? JSON.parse(request.responseText) : undefined;
      } catch {
        reject(new ApiClientError({
          code: 'INVALID_RESPONSE',
          message: 'The upload service returned invalid JSON.',
          status: request.status
        }));
        return;
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(body as InboxItem);
      } else {
        reject(normalizeApiError(body, new Response(null, { status: request.status })));
      }
    };
    request.onerror = () => reject(new ApiClientError({
      code: 'NETWORK_ERROR',
      message: 'The upload service is unavailable.',
      status: 0
    }));
    request.onabort = () => reject(new DOMException('The upload was aborted.', 'AbortError'));
    signal?.addEventListener('abort', () => request.abort(), { once: true });
    request.send(form);
  });
}
