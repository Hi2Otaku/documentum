import type { EdgeTypes } from '@xyflow/react';
import { NormalEdge } from './NormalEdge';
import { RejectEdge } from './RejectEdge';

export const edgeTypes: EdgeTypes = {
  normal: NormalEdge,
  reject: RejectEdge,
};
