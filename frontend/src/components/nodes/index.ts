import type { NodeTypes } from '@xyflow/react';
import { StartNode } from './StartNode';
import { EndNode } from './EndNode';
import { ManualNode } from './ManualNode';
import { AutoNode } from './AutoNode';
import { SubWorkflowNode } from './SubWorkflowNode';
import { EventNode } from './EventNode';

export const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  manual: ManualNode,
  auto: AutoNode,
  sub_workflow: SubWorkflowNode,
  event: EventNode,
  startNode: StartNode,
  endNode: EndNode,
  manualNode: ManualNode,
  autoNode: AutoNode,
  sub_workflowNode: SubWorkflowNode,
  eventNode: EventNode,
};
