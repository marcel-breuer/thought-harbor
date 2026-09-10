import { describe, expect, it } from 'vitest';

import { normalizeApiBaseUrl } from './client';

describe('normalizeApiBaseUrl', () => {
  it('uses the API origin for generated versioned paths', () => {
    expect(normalizeApiBaseUrl('http://localhost:8000/api/v1')).toBe('http://localhost:8000');
  });

  it('keeps an origin-only URL unchanged', () => {
    expect(normalizeApiBaseUrl('http://localhost:8000/')).toBe('http://localhost:8000');
  });
});
