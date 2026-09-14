import type { components } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type SavedSearch = components['schemas']['SavedSearchResponse'];
export type SavedSearchCreateRequest = components['schemas']['SavedSearchCreateRequest'];
export type EvaluationList = components['schemas']['EvaluationListResponse'];
export type EvaluationRating = components['schemas']['AnswerEvaluationRequest']['rating'];

export async function listSavedSearches(signal?: AbortSignal): Promise<SavedSearch[]> {
  const result = await apiClient.GET('/api/v1/saved-searches', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function createSavedSearch(
  body: SavedSearchCreateRequest,
  signal?: AbortSignal
): Promise<SavedSearch> {
  const result = await apiClient.POST('/api/v1/saved-searches', { body, signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function deleteSavedSearch(id: number, signal?: AbortSignal): Promise<void> {
  const result = await apiClient.DELETE('/api/v1/saved-searches/{search_id}', {
    params: { path: { search_id: id } },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
}

export async function updateSavedSearch(
  id: number,
  body: components['schemas']['SavedSearchUpdateRequest'],
  signal?: AbortSignal
): Promise<SavedSearch> {
  const result = await apiClient.PATCH('/api/v1/saved-searches/{search_id}', {
    params: { path: { search_id: id } },
    body,
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function submitEvaluation(
  messageId: number,
  rating: EvaluationRating,
  notes?: string,
  signal?: AbortSignal
): Promise<components['schemas']['AnswerEvaluationResponse']> {
  const result = await apiClient.POST('/api/v1/chat/messages/{message_id}/evaluation', {
    params: { path: { message_id: messageId } },
    body: { rating, notes },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function getEvaluations(signal?: AbortSignal): Promise<EvaluationList> {
  const result = await apiClient.GET('/api/v1/evaluations', { signal });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
