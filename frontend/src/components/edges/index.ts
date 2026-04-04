import type { EdgeTypes } from '@xyflow/react';
import { NormalEdge } from './NormalEdge';
import { RejectEdge } from './RejectEdge';
import { ConditionalEdge } from './ConditionalEdge';

export const edgeTypes: EdgeTypes = {
  normal: NormalEdge,
  reject: RejectEdge,
  normalEdge: NormalEdge,
  rejectEdge: RejectEdge,
  conditionalEdge: ConditionalEdge,
};
