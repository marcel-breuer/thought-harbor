import { describe, expect, it } from 'vitest';

import { ApiClientError, normalizeApiError } from '$lib/api/errors';

describe('normalizeApiError', () => {
  it('preserves the public error envelope and correlation ID', () => {
    const response = new Response(null, {
      headers: { 'X-Request-ID': 'request-42' },
      status: 422,
      statusText: 'Unprocessable Entity',
    });

    const error = normalizeApiError(
      {
        error: {
          code: 'VALIDATION_ERROR',
          details: [{ location: ['query', 'page'], message: 'Invalid', type: 'greater_than' }],
          message: 'The request could not be validated.',
        },
        request_id: 'request-42',
      },
      response,
    );

    expect(error).toBeInstanceOf(ApiClientError);
    expect(error.code).toBe('VALIDATION_ERROR');
    expect(error.requestId).toBe('request-42');
    expect(error.status).toBe(422);
  });
});
