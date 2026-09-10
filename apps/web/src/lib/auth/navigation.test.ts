import { describe, expect, it } from 'vitest';

import { safeRedirectPath } from './navigation';

describe('safeRedirectPath', () => {
  it('keeps internal paths', () => {
    expect(safeRedirectPath('/knowledge/documents/7?tab=source')).toBe(
      '/knowledge/documents/7?tab=source'
    );
  });

  it('rejects external and protocol-relative destinations', () => {
    expect(safeRedirectPath('https://example.com')).toBe('/');
    expect(safeRedirectPath('//example.com')).toBe('/');
    expect(safeRedirectPath(null)).toBe('/');
  });
});
