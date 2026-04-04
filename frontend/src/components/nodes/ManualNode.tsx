import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/designer';

type ManualNodeType = Node<ActivityNodeData, 'manualNode'>;

export function ManualNode({ data, selected }: NodeProps<ManualNodeType>) {
  const performerHint = data.performerType
    ? `${data.performerType}: ${data.performerId || '...'}`
    : 'No performer';

  return (
    <div
      className={`min-w-[160px] min-h-[64px] rounded-lg bg-blue-500 border-2 border-blue-600 text-white px-3 py-2 ${
        selected ? 'ring-2 ring-primary ring-offset-2' : ''
      }`}
    >
      <div className="font-semibold text-sm truncate">{data.name}</div>
      <div className="text-sm opacity-70 truncate">{performerHint}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
