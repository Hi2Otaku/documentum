import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Radio } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type EventNodeType = Node<ActivityNodeData, 'eventNode'>;

export function EventNode({ data, selected }: NodeProps<EventNodeType>) {
  const eventHint = data.eventTypeFilter || 'No event configured';

  return (
    <div
      className={`min-w-[160px] min-h-[64px] rounded-lg bg-amber-500 border-2 border-amber-600 text-white px-4 py-3 ${
        selected ? 'ring-2 ring-primary ring-offset-2' : ''
      }`}
    >
      <div className="flex items-center gap-1.5">
        <Radio className="w-4 h-4 shrink-0" />
        <div className="font-semibold text-sm truncate">{data.name}</div>
      </div>
      <div className="text-sm opacity-70 truncate">{eventHint}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
