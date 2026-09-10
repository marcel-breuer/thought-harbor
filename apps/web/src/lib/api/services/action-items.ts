import type { components, paths } from '$lib/generated/api';

import { apiClient } from '$lib/api/client';
import { normalizeApiError } from '$lib/api/errors';

export type ActionItem = components['schemas']['ActionItemResponse'];
export type ActionItemList = components['schemas']['ActionItemListResponse'];
export type ActionItemType = NonNullable<
  NonNullable<paths['/api/v1/knowledge/action-items']['get']['parameters']['query']>['type']
>;
export type ActionSourceType = NonNullable<
  NonNullable<paths['/api/v1/knowledge/action-items']['get']['parameters']['query']>['source_type']
>;

export async function listActionItems(
  options: {
    type?: ActionItemType;
    status?: string;
    topic_id?: number;
    project_id?: number;
    source_type?: ActionSourceType;
    assignee_user_id?: number;
    date_from?: string;
    date_to?: string;
    signal?: AbortSignal;
  } = {}
): Promise<ActionItemList> {
  const result = await apiClient.GET('/api/v1/knowledge/action-items', {
    params: {
      query: {
        type: options.type,
        status: options.status,
        topic_id: options.topic_id,
        project_id: options.project_id,
        source_type: options.source_type,
        assignee_user_id: options.assignee_user_id,
        date_from: options.date_from,
        date_to: options.date_to,
        page: 1,
        page_size: 100
      }
    },
    signal: options.signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}

export async function updateActionItemStatus(
  id: number,
  status: string,
  signal?: AbortSignal
): Promise<ActionItem> {
  const result = await apiClient.PATCH('/api/v1/knowledge/action-items/{artifact_id}', {
    params: { path: { artifact_id: id } },
    body: { status },
    signal
  });
  if (result.error) throw normalizeApiError(result.error, result.response);
  return result.data;
}
