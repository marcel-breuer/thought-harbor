import type { components } from '$lib/generated/api';

type ErrorPayload = Partial<components['schemas']['ErrorResponse']>;

export class ApiClientError extends Error {
  readonly code: string;
  readonly details: components['schemas']['ValidationErrorDetail'][] | null;
  readonly requestId: string | null;
  readonly status: number;

  constructor({
    code,
    details,
    message,
    requestId,
    status,
  }: {
    code: string;
    details?: components['schemas']['ValidationErrorDetail'][] | null;
    message: string;
    requestId?: string | null;
    status: number;
  }) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.details = details ?? null;
    this.requestId = requestId ?? null;
    this.status = status;
  }
}

export function normalizeApiError(error: unknown, response: Response): ApiClientError {
  const payload = isErrorPayload(error) ? error : undefined;
  const body = payload?.error;

  return new ApiClientError({
    code: body?.code ?? `HTTP_${response.status}`,
    details: body?.details,
    message: body?.message ?? (response.statusText || 'Request failed'),
    requestId: payload?.request_id ?? response.headers.get('X-Request-ID'),
    status: response.status,
  });
}

function isErrorPayload(error: unknown): error is ErrorPayload {
  return typeof error === 'object' && error !== null && 'error' in error;
}
