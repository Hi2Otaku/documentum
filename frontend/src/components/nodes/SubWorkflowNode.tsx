import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type SubWorkflowNodeType = Node<ActivityNodeData, 'subWorkflowNode'>;

export function SubWorkflowNode({ data, selected }: NodeProps<SubWorkflowNodeType>) {
  const templateHint = data.subTemplateId
    ? 'Template linked'
    : 'No template selected';

  return (
    <div
      className={`min-w-[160px] min-h-[64px] ${
        selected ? 'ring-2 ring-primary ring-offset-2' : ''
      }`}
    >
      <div className="bg-purple-500 border-double border-4 border-purple-600 text-white px-4 py-3 rounded">
        <div className="flex items-center gap-1.5">
          <GitBranch className="w-4 h-4 shrink-0" />
          <div className="font-semibold text-sm truncate">{data.name}</div>
        </div>
        <div className="text-sm opacity-70 truncate">{templateHint}</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
