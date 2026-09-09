import { describe, expect, it } from 'vitest';

import { createFakeSystemApi } from '$lib/api/fakes';

describe('createFakeSystemApi', () => {
  it('supports frontend tests without a live backend', async () => {
    await expect(createFakeSystemApi().getHealth()).resolves.toEqual({ status: 'ok' });
  });

  it('honors cancellation', async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(createFakeSystemApi().getHealth(controller.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
  });
});
