import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Square } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type EndNodeType = Node<ActivityNodeData, 'endNode'>;

export function EndNode({ data, selected }: NodeProps<EndNodeType>) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`flex items-center justify-center w-[60px] h-[60px] rounded-full bg-red-500 border-2 border-red-600 text-white ${
          selected ? 'ring-2 ring-primary ring-offset-2' : ''
        }`}
      >
        <Square className="w-6 h-6" />
        <Handle type="target" position={Position.Left} />
      </div>
      <div className="text-sm text-center mt-1">{data.name}</div>
    </div>
  );
}
