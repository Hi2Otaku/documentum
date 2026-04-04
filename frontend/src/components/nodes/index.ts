import type { NodeTypes } from '@xyflow/react';
import { StartNode } from './StartNode';
import { EndNode } from './EndNode';
import { ManualNode } from './ManualNode';
import { AutoNode } from './AutoNode';

export const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  manual: ManualNode,
  auto: AutoNode,
  startNode: StartNode,
  endNode: EndNode,
  manualNode: ManualNode,
  autoNode: AutoNode,
};
