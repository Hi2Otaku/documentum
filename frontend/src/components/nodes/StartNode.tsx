import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Play } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type StartNodeType = Node<ActivityNodeData, 'startNode'>;

export function StartNode({ data, selected }: NodeProps<StartNodeType>) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`flex items-center justify-center w-[60px] h-[60px] rounded-full bg-green-500 border-2 border-green-600 text-white ${
          selected ? 'ring-2 ring-primary ring-offset-2' : ''
        }`}
      >
        <Play className="w-6 h-6" />
        <Handle type="source" position={Position.Right} />
      </div>
      <div className="text-sm text-center mt-1">{data.name}</div>
    </div>
  );
}
