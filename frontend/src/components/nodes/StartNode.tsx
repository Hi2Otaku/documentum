import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/workflow';

type StartNodeType = Node<ActivityNodeData, 'start'>;

export function StartNode({ selected }: NodeProps<StartNodeType>) {
  return (
    <div
      className={`flex items-center justify-center w-16 h-16 rounded-full border-2 text-white text-xs font-bold ${
        selected
          ? 'border-yellow-400 shadow-lg shadow-yellow-400/30'
          : 'border-green-600'
      } bg-green-500`}
    >
      START
      <Handle type="source" position={Position.Right} className="!bg-green-700" />
    </div>
  );
}
