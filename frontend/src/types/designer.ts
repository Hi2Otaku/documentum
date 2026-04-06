/** Designer-specific types for React Flow canvas */

export interface ActivityNodeData extends Record<string, unknown> {
  name: string;
  description?: string;
  activityType: 'start' | 'end' | 'manual' | 'auto' | 'sub_workflow' | 'event';
  /** EVENT: which domain event type to listen for */
  eventTypeFilter?: string | null;
  /** EVENT: optional key-value filter on event payload */
  eventFilterConfig?: Record<string, string> | null;
  performerType?: string | null;
  performerId?: string | null;
  triggerType?: 'and_join' | 'or_join';
  methodName?: string | null;
  routingType?: string | null;
  performerList?: string[] | null;
  apiId?: string;
  /** Backend ID -- undefined for newly created nodes not yet saved */
  backendId?: string;
}

export interface FlowEdgeData extends Record<string, unknown> {
  flowType: 'normal' | 'reject';
  conditionExpression?: string | null;
  displayLabel?: string | null;
  apiId?: string;
  /** Backend ID -- undefined for newly created edges not yet saved */
  backendId?: string;
}
