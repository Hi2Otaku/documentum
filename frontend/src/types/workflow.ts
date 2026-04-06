/** Backend enum mirrors */
export type ActivityType = 'start' | 'end' | 'manual' | 'auto' | 'sub_workflow';
export type FlowType = 'normal' | 'reject';
export type TriggerType = 'and_join' | 'or_join';
export type ProcessState = 'draft' | 'validated' | 'active' | 'deprecated';
export type PerformerType =
  | 'user'
  | 'group'
  | 'supervisor'
  | 'alias'
  | 'sequential'
  | 'runtime_selection';

/** Backend response types */
export interface ProcessTemplate {
  id: string;
  name: string;
  description: string | null;
  version: number;
  state: ProcessState;
  is_installed: boolean;
  installed_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  is_deleted: boolean;
}

export interface ActivityTemplate {
  id: string;
  process_template_id: string;
  name: string;
  activity_type: ActivityType;
  description: string | null;
  performer_type: PerformerType | null;
  performer_id: string | null;
  trigger_type: TriggerType;
  method_name: string | null;
  position_x: number | null;
  position_y: number | null;
  routing_type: string | null;
  performer_list: string[] | null;
  expected_duration_hours: number | null;
  escalation_action: string | null;
  warning_threshold_hours: number | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface FlowTemplate {
  id: string;
  process_template_id: string;
  source_activity_id: string;
  target_activity_id: string;
  flow_type: FlowType;
  condition_expression: string | null;
  display_label: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface ProcessVariable {
  id: string;
  process_template_id: string | null;
  workflow_instance_id: string | null;
  name: string;
  variable_type: string;
  string_value: string | null;
  int_value: number | null;
  bool_value: boolean | null;
  date_value: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface ProcessTemplateDetail extends ProcessTemplate {
  activities: ActivityTemplate[];
  flows: FlowTemplate[];
  variables: ProcessVariable[];
}

export interface ValidationErrorDetail {
  code: string;
  message: string;
  entity_type: string;
  entity_id: string | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationErrorDetail[];
}

/** API envelope */
export interface ApiResponse<T> {
  data: T;
  meta?: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
}

/** React Flow node data */
export interface ActivityNodeData extends Record<string, unknown> {
  label: string;
  activityType: ActivityType;
  description?: string;
  performerType?: PerformerType | null;
  performerId?: string | null;
  triggerType?: TriggerType;
  methodName?: string | null;
  routingType?: string | null;
  performerList?: string[] | null;
  /** Backend ID -- undefined for newly created nodes not yet saved */
  backendId?: string;
}

/** React Flow edge data */
export interface FlowEdgeData extends Record<string, unknown> {
  flowType: FlowType;
  conditionExpression?: string | null;
  displayLabel?: string | null;
  /** Backend ID -- undefined for newly created edges not yet saved */
  backendId?: string;
}
