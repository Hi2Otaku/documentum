// Re-export workflow types that are used by pages and API
export type {
  ProcessTemplate as ProcessTemplateResponse,
  ActivityTemplate,
  FlowTemplate,
  ProcessVariable,
  ProcessTemplateDetail,
  ValidationResult,
  ValidationErrorDetail,
} from "./workflow";

export interface ProcessTemplateCreate {
  name: string;
  description?: string | null;
}
