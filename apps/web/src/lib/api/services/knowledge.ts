import type { components, paths } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type KnowledgeObject = components['schemas']['KnowledgeObjectResponse'];
export type KnowledgeObjectDetail = components['schemas']['KnowledgeObjectDetailResponse'];
export type KnowledgeKind = NonNullable<
  NonNullable<paths['/api/v1/knowledge/objects']['get']['parameters']['query']>['kind']
>;

export async function listKnowledge(kind?: KnowledgeKind): Promise<components['schemas']['KnowledgeObjectListResponse']> {
  const result = await apiClient.GET('/api/v1/knowledge/objects', { params: { query: { kind, page: 1, page_size: 100 } } });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function getKnowledgeObject(id: number): Promise<KnowledgeObjectDetail> {
  const result = await apiClient.GET('/api/v1/knowledge/objects/{object_id}', { params: { path: { object_id: id } } });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export type DocumentDetail = components['schemas']['DocumentDetailResponse'];
export type MeetingDetail = components['schemas']['MeetingDetailResponse'];

export async function getDocument(id: number): Promise<DocumentDetail> {
  const result = await apiClient.GET('/api/v1/knowledge/documents/{document_id}', {
    params: { path: { document_id: id } }
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function getMeeting(id: number): Promise<MeetingDetail> {
  const result = await apiClient.GET('/api/v1/knowledge/meetings/{meeting_id}', {
    params: { path: { meeting_id: id } }
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
