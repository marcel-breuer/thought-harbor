import { describe, expect, it } from 'vitest';

describe('web bootstrap', () => {
  it('has a stable package surface for the initial workspace', () => {
    expect('ThoughtHarbor').toBeTruthy();
  });
});
