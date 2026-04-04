import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import type { ActivityNodeData } from '../../types/workflow';

type AutoNodeType = Node<ActivityNodeData, 'auto'>;

export function AutoNode({ data, selected }: NodeProps<AutoNodeType>) {
  return (
    <div
      className={`min-w-[140px] rounded-lg border-2 bg-white shadow-md ${
        selected
          ? 'border-yellow-400 shadow-lg shadow-yellow-400/30'
          : 'border-purple-500'
      }`}
    >
      <div className="bg-purple-500 text-white text-xs font-semibold px-3 py-1 rounded-t-md">
        Auto
      </div>
      <div className="px-3 py-2">
        <div className="text-sm font-medium text-gray-800 truncate">
          {data.label}
        </div>
        {data.methodName && (
          <div className="text-xs text-gray-500 mt-1 font-mono">
            {data.methodName}
          </div>
        )}
      </div>
      <Handle type="target" position={Position.Left} className="!bg-purple-600" />
      <Handle type="source" position={Position.Right} className="!bg-purple-600" />
    </div>
  );
}
