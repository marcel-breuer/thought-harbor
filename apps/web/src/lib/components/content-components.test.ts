import { describe, expect, it } from 'vitest';

import { humanize, provenanceLabel } from './content-components';

describe('content component helpers', () => {
  it('humanizes persisted status and artifact labels', () => {
    expect(humanize('open_question')).toBe('open question');
  });

  it('keeps source location labels consistent', () => {
    expect(provenanceLabel('document', { page: 4 })).toBe('document · page 4');
    expect(provenanceLabel('transcript', { section: 'Opening' })).toBe('transcript · Opening');
    expect(provenanceLabel('email', {})).toBe('email');
  });
});
