/** Designer-specific types for React Flow canvas */

export interface ActivityNodeData extends Record<string, unknown> {
  name: string;
  description?: string;
  activityType: 'start' | 'end' | 'manual' | 'auto' | 'sub_workflow';
  performerType?: string | null;
  performerId?: string | null;
  triggerType?: 'and_join' | 'or_join';
  methodName?: string | null;
  routingType?: string | null;
  performerList?: string[] | null;
  expectedDurationHours?: number | null;
  escalationAction?: 'priority_bump' | 'reassign' | 'notify' | null;
  warningThresholdHours?: number | null;
  apiId?: string;
  /** Sub-workflow: referenced template ID */
  subTemplateId?: string | null;
  /** Sub-workflow: parent->child variable mapping */
  variableMapping?: Record<string, string> | null;
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
