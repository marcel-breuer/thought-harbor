import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type AuthUser = components['schemas']['UserResponse'];
export type AuthSessionResponse = components['schemas']['AuthSessionResponse'];
export type BootstrapRequest = components['schemas']['BootstrapRequest'];
export type RegisterRequest = components['schemas']['RegisterRequest'];
export type LoginRequest = components['schemas']['LoginRequest'];

export async function getAuthStatus(signal?: AbortSignal) {
  const result = await apiClient.GET('/api/v1/auth/status', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function bootstrap(request: BootstrapRequest): Promise<AuthSessionResponse> {
  const result = await apiClient.POST('/api/v1/auth/bootstrap', { body: request });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function register(request: RegisterRequest): Promise<AuthSessionResponse> {
  const result = await apiClient.POST('/api/v1/auth/register', { body: request });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function login(request: LoginRequest): Promise<AuthSessionResponse> {
  const result = await apiClient.POST('/api/v1/auth/login', { body: request });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function logout(): Promise<{ message: string }> {
  const result = await apiClient.POST('/api/v1/auth/logout', {});
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function getCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  const result = await apiClient.GET('/api/v1/auth/me', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
