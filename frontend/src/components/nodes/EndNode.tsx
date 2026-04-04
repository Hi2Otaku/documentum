import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/workflow';

type EndNodeType = Node<ActivityNodeData, 'end'>;

export function EndNode({ selected }: NodeProps<EndNodeType>) {
  return (
    <div
      className={`flex items-center justify-center w-16 h-16 rounded-full border-2 text-white text-xs font-bold ${
        selected
          ? 'border-yellow-400 shadow-lg shadow-yellow-400/30'
          : 'border-red-600'
      } bg-red-500`}
    >
      END
      <Handle type="target" position={Position.Left} className="!bg-red-700" />
    </div>
  );
}
