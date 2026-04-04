import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/workflow';

type ManualNodeType = Node<ActivityNodeData, 'manual'>;

export function ManualNode({ data, selected }: NodeProps<ManualNodeType>) {
  return (
    <div
      className={`min-w-[140px] rounded-lg border-2 bg-white shadow-md ${
        selected
          ? 'border-yellow-400 shadow-lg shadow-yellow-400/30'
          : 'border-blue-500'
      }`}
    >
      <div className="bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-t-md">
        Manual
      </div>
      <div className="px-3 py-2">
        <div className="text-sm font-medium text-gray-800 truncate">
          {data.label}
        </div>
        {data.performerType && (
          <div className="text-xs text-gray-500 mt-1">
            {data.performerType}
            {data.performerId ? `: ${data.performerId}` : ''}
          </div>
        )}
      </div>
      <Handle type="target" position={Position.Left} className="!bg-blue-600" />
      <Handle type="source" position={Position.Right} className="!bg-blue-600" />
    </div>
  );
}
