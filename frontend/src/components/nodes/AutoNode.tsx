import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/designer';

type AutoNodeType = Node<ActivityNodeData, 'autoNode'>;

export function AutoNode({ data, selected }: NodeProps<AutoNodeType>) {
  const methodHint = data.methodName
    ? `Method: ${data.methodName}`
    : 'No method';

  return (
    <div
      className={`min-w-[160px] min-h-[64px] ${
        selected ? 'ring-2 ring-primary ring-offset-2' : ''
      }`}
    >
      <div
        className="bg-orange-500 border-2 border-orange-600 text-white px-4 py-3"
        style={{
          clipPath:
            'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)',
        }}
      >
        <div className="font-semibold text-sm truncate">{data.name}</div>
        <div className="text-sm opacity-70 truncate">{methodHint}</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
